"""Inviting somebody who does not have an account, and letting them in.

Two audiences, two very different security postures, one file so the pair can
be read together.

**The admin half** is ordinary tenant-admin work behind the usual session.

**The candidate half is unauthenticated**, which is the part worth being
careful about. Three rules hold it together, and each exists because the
obvious implementation gets it wrong:

* *Looking is free, claiming is once.* ``GET`` tells a candidate what they
  have been invited to without consuming anything, so a preview, a reload or a
  link-scanner in a mail client cannot burn the invitation. ``POST`` is what
  redeems it, once, atomically.
* *A redeemed session is a key to one assessment.* Role ``candidate``, and
  every endpoint they can reach checks it. Not a student account with the
  practice screens, the drill history and every past result attached.
* *Refusals say which of the three things went wrong.* "Invalid link" is
  useless to somebody holding a link; expired, already-used and withdrawn each
  have a different next step.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app import audit, invitations, ratelimit
from app.db import platform_sessionmaker, tenant_sessionmaker
from app.deps import PlatformSession, Principal, TenantSession, require_roles
from app.models.platform import InvitationDirectory, Tenant
from app.models.tenant import (Attempt, Invitation, SimulationProfile, User)
from app.schemas import (AttemptResult, CandidateSession, InvitationOut,
                         InvitationRequest, InvitePreview, RedeemRequest)
from app.security import TokenPrincipal, create_token

router = APIRouter(prefix="/tenant/invitations", tags=["invitations"],
                   dependencies=[Depends(require_roles("tenant_admin"))])

# Unauthenticated on purpose. Nothing here reads a session, and everything it
# returns is about the invitation the caller already holds a token for.
public = APIRouter(prefix="/invite", tags=["invitations"])

# The one place in this application without a session in front of it, so the
# one place that needs a brake. See ``app.ratelimit`` for what it does and does
# not protect against.
_by_token = ratelimit.Limiter(limit=ratelimit.PER_TOKEN_LIMIT)
_by_caller = ratelimit.Limiter(limit=ratelimit.PER_CALLER_LIMIT)


def _not_flooding(request: Request, token: str) -> None:
    """Both limits, and the token one first.

    Order matters for what the caller learns: an address that has tripped the
    looser limit is doing something no candidate does, whereas a token being
    hammered may be one confused person with a broken connection. Neither
    refusal reveals whether the token is real -- the check runs before the
    lookup, so a 429 says the same thing for a token that exists and one that
    does not.
    """
    if not _by_token.allows(token) or not _by_caller.allows(
            ratelimit.caller_of(request)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            ratelimit.TOO_MANY_MESSAGE)


def _out(row: Invitation, profile_name: str = "") -> InvitationOut:
    return InvitationOut(
        id=row.id, token=row.token, profile_id=row.profile_id,
        profile_name=profile_name, invited_name=row.invited_name,
        invited_email=row.invited_email, reference=row.reference,
        status=row.status, expires_at=row.expires_at,
        redeemed_at=row.redeemed_at, attempt_id=row.attempt_id,
        created_at=row.created_at)


@router.get("/{invitation_id}/result", response_model=AttemptResult)
async def invitation_result(invitation_id: str, principal: Principal,
                            session: TenantSession) -> AttemptResult:
    """The report for the sitting this invitation produced.

    Without this the external-hiring flow stopped one step short of the point
    of it. An employer could build an assessment, invite somebody, watch the
    invitation turn "redeemed" -- and never see the result. The candidate's
    own report lives behind `/student/attempts/{id}/result`, which is scoped
    to the person who sat it, and every trainer route is cohort-scoped, which
    a candidate is not in. There was no route at all.

    Authorised by the invitation rather than by the attempt: this admin's
    institution issued the link, and the schema the query runs in is the one
    their token names, so an invitation from another institution is not
    merely forbidden -- it is not present to be asked for.
    """
    from app.routers.attempts import _result, finalise_attempt, pending_responses

    row = await session.get(Invitation, invitation_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such invitation")

    attempt = None
    if row.attempt_id:
        attempt = await session.get(Attempt, row.attempt_id)
    if attempt is None and row.candidate_id:
        # Invitations redeemed before the attempt link was recorded. Falls
        # back to the candidate's own attempt rather than reporting nothing.
        attempt = (await session.execute(
            select(Attempt)
            .where(Attempt.user_id == row.candidate_id,
                   Attempt.profile_id == row.profile_id)
            .order_by(Attempt.attempt_number)
        )).scalars().first()

    if attempt is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Nobody has sat this assessment yet, so there is no result.")

    if attempt.status == "scoring" and not await pending_responses(session, attempt.id):
        await finalise_attempt(session, attempt.id)
        await session.refresh(attempt)

    return await _result(session, attempt)


@router.get("", response_model=list[InvitationOut])
async def list_invitations(principal: Principal,
                           session: TenantSession) -> list[InvitationOut]:
    rows = list((await session.execute(
        select(Invitation).order_by(Invitation.created_at.desc()).limit(200)
    )).scalars().all())
    names = {p.id: p.name for p in (await session.execute(
        select(SimulationProfile))).scalars().all()}
    return [_out(row, names.get(row.profile_id, "")) for row in rows]


@router.post("", response_model=InvitationOut,
             status_code=status.HTTP_201_CREATED)
async def create_invitation(body: InvitationRequest, principal: Principal,
                            session: TenantSession,
                            platform: PlatformSession) -> InvitationOut:
    """Issue a link for one person to sit one assessment."""
    profile = await session.get(SimulationProfile, body.profile_id)
    if profile is None or profile.status != "published":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "That assessment is not published, so nobody can be invited to it "
            "yet.")

    token = invitations.new_token()
    row = Invitation(
        token=token, profile_id=profile.id,
        invited_name=body.invited_name.strip(),
        invited_email=body.invited_email.strip().lower(),
        reference=body.reference.strip(),
        expires_at=invitations.expiry_for(body.valid_days),
        created_by=principal.user_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # The control-plane pointer, so redemption can find the schema without a
    # session and without the slug appearing in the link.
    platform.add(InvitationDirectory(
        token=token, tenant_id=principal.tenant_id or "",
        tenant_slug=principal.tenant_slug or ""))
    await platform.commit()

    await audit.record(principal, "invitation.created", entity="Invitation",
                       entity_id=row.id,
                       after={"profile": profile.name,
                              "invited": row.invited_email})
    return _out(row, profile.name)


@router.post("/{invitation_id}/withdraw", response_model=InvitationOut)
async def withdraw(invitation_id: str, principal: Principal,
                   session: TenantSession,
                   platform: PlatformSession) -> InvitationOut:
    """Cancel a link that has not been used.

    A redeemed invitation is left alone: the attempt behind it is somebody's
    work, and withdrawing the invitation afterwards would suggest the result
    can be withdrawn too. It cannot.
    """
    row = await session.get(Invitation, invitation_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    if row.redeemed_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "That invitation has already been used. The assessment behind it "
            "stands; withdrawing the link now would change nothing.")

    row.status = "withdrawn"
    await session.commit()

    # Remove the pointer as well, so a withdrawn token stops resolving to an
    # institution at all rather than resolving and then being refused.
    pointer = (await platform.execute(
        select(InvitationDirectory).where(
            InvitationDirectory.token == row.token))).scalars().first()
    if pointer is not None:
        await platform.delete(pointer)
        await platform.commit()

    await audit.record(principal, "invitation.withdrawn", entity="Invitation",
                       entity_id=row.id)
    return _out(row)


# --------------------------------------------------------------------------
# The candidate's side. No session, no account, one token.
# --------------------------------------------------------------------------

async def _resolve(token: str):
    """Token -> (tenant, invitation row) or a refusal.

    Two lookups: the control plane says which schema, the schema says whether
    the invitation is usable. Neither reveals anything to somebody without a
    valid token -- an unknown one stops at the first.
    """
    async with platform_sessionmaker()() as platform:
        pointer = (await platform.execute(
            select(InvitationDirectory).where(
                InvitationDirectory.token == token))).scalars().first()
        if pointer is None:
            return None, None, invitations.UNKNOWN
        tenant = await platform.get(Tenant, pointer.tenant_id)
        if tenant is None or tenant.status in {"suspended", "closed"}:
            return None, None, invitations.UNKNOWN
        slug = pointer.tenant_slug
        name = tenant.name
        tenant_id = tenant.id

    async with tenant_sessionmaker(slug)() as session:
        row = (await session.execute(
            select(Invitation).where(Invitation.token == token)
        )).scalars().first()
        refusal = invitations.check(row)
        if refusal is not None:
            return None, None, refusal
        profile = await session.get(SimulationProfile, row.profile_id)

    return ({"slug": slug, "id": tenant_id, "name": name},
            {"row": row, "profile": profile}, None)


@public.get("/{token}", response_model=InvitePreview)
async def preview(token: str, request: Request) -> InvitePreview:
    """What am I being asked to do, and by whom?

    A GET, and it consumes nothing. A preview that redeemed would mean a link
    scanner in a mail client -- or the candidate opening it on the train to
    check what it is -- burning the invitation before they ever sat down.
    """
    _not_flooding(request, token)
    tenant, found, refusal = await _resolve(token)
    if refusal is not None:
        return InvitePreview(ok=False, reason=refusal.reason,
                             message=refusal.message)

    profile = found["profile"]
    return InvitePreview(
        ok=True,
        tenant_name=tenant["name"],
        profile_name=profile.name if profile else "",
        description=profile.description if profile else "",
        estimated_minutes=profile.estimated_minutes if profile else 0,
        camera_check=bool(profile.camera_check) if profile else False,
        practice_item=bool(profile.practice_item) if profile else False,
        invited_name=found["row"].invited_name,
    )


@public.post("/{token}/claim", response_model=CandidateSession)
async def claim(token: str, body: RedeemRequest,
                request: Request) -> CandidateSession:
    """Take the invitation, and become somebody who can sit this one test.

    The write that burns the token and the write that creates the account
    happen in one transaction. Two people opening the same link at the same
    moment is the case this protects: the unique index on ``token`` plus the
    re-check inside the transaction means the second one gets a refusal rather
    than a second account against a single invitation.
    """
    _not_flooding(request, token)
    tenant, found, refusal = await _resolve(token)
    if refusal is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, refusal.message)

    name = body.full_name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Please give the name your result should be in.")

    async with tenant_sessionmaker(tenant["slug"])() as session:
        row = (await session.execute(
            select(Invitation).where(Invitation.token == token).with_for_update()
        )).scalars().first()
        # Re-checked inside the transaction, not just before it. Between the
        # preview above and this line somebody else may have claimed it.
        again = invitations.check(row)
        if again is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, again.message)

        email = invitations.candidate_email(token, body.email)
        existing = (await session.execute(
            select(User).where(User.email == email))).scalars().first()
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Somebody with that email address already has an account here. "
                "Sign in instead, or use a different address.")

        candidate = User(
            email=email, full_name=name,
            # No password. There is nothing to sign in to: the token was the
            # credential and it is now spent.
            password_hash="",
            role=invitations.CANDIDATE_ROLE, active=True)
        session.add(candidate)
        await session.flush()

        row.status = "redeemed"
        row.redeemed_at = datetime.now(timezone.utc)
        row.candidate_id = candidate.id
        await session.commit()

        profile_id = row.profile_id
        candidate_id = candidate.id
        full_name = candidate.full_name

    principal = TokenPrincipal(
        user_id=candidate_id, email=email, full_name=full_name,
        role=invitations.CANDIDATE_ROLE, scope="tenant",
        tenant_id=tenant["id"], tenant_slug=tenant["slug"])

    return CandidateSession(
        token=create_token(principal),
        candidate_id=candidate_id,
        full_name=full_name,
        profile_id=profile_id,
        tenant_name=tenant["name"],
    )
