"""Trainer surfaces — read and assign only.

A trainer sees the students in their own cohorts, and cannot alter a recorded
score or an attempt history (TRN-05). Nothing in this router writes to
attempts, responses or score records; the only writes are flags and notes.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.deps import Principal, TenantSession, require_roles
from app.models.tenant import (Attempt, Cohort, CohortMember, ScoreRecord,
                               SimulationProfile, SkillMastery, StudentFlag,
                               User)
from app.readiness import (HIGH_RISK, NEEDS_TRAINING, NOT_STARTED, READY, band)
from app.schemas import (AttemptOut, AttemptResult, CohortOut,
                         CohortReadiness, MasteryOut, StudentSummary, UserOut)

router = APIRouter(prefix="/trainer", tags=["trainer"],
                   dependencies=[Depends(require_roles("trainer", "tenant_admin"))])


async def _visible_cohorts(session: TenantSession, principal: Principal) -> list[Cohort]:
    """Cohorts this caller may see.

    A tenant admin sees the institution; a trainer sees only what they were
    assigned (TRN-01). The narrowing happens here rather than in each endpoint
    so there is one place to get it right.
    """
    stmt = select(Cohort).where(Cohort.active.is_(True))
    if principal.role == "trainer":
        stmt = stmt.where(Cohort.trainer_id == principal.user_id)
    return list((await session.execute(stmt.order_by(Cohort.name))).scalars().all())


async def _latest_overall(session: TenantSession, user_ids: list[str]) -> dict[str, float]:
    """Most recent overall score per student."""
    if not user_ids:
        return {}
    rows = (await session.execute(
        select(Attempt.user_id, ScoreRecord.score, Attempt.scored_at)
        .join(ScoreRecord, ScoreRecord.attempt_id == Attempt.id)
        .where(Attempt.user_id.in_(user_ids),
               ScoreRecord.dimension == "overall",
               ScoreRecord.is_shadow.is_(False))
        .order_by(Attempt.scored_at.desc())
    )).all()
    latest: dict[str, float] = {}
    for user_id, score, _ in rows:
        latest.setdefault(user_id, score)
    return latest


@router.get("/cohorts", response_model=list[CohortOut])
async def cohorts(principal: Principal, session: TenantSession) -> list[CohortOut]:
    rows = await _visible_cohorts(session, principal)
    counts = dict((await session.execute(
        select(CohortMember.cohort_id, func.count()).group_by(CohortMember.cohort_id)
    )).all())
    trainers = dict((await session.execute(
        select(User.id, User.full_name).where(User.role == "trainer")
    )).all())
    return [
        CohortOut(
            id=c.id, name=c.name, branch=c.branch, year_of_study=c.year_of_study,
            section=c.section, trainer_id=c.trainer_id,
            trainer_name=trainers.get(c.trainer_id or "", ""),
            drive_start=c.drive_start, drive_end=c.drive_end,
            member_count=counts.get(c.id, 0), active=c.active,
        )
        for c in rows
    ]


@router.get("/cohorts/{cohort_id}/readiness", response_model=CohortReadiness)
async def cohort_readiness(cohort_id: str, principal: Principal,
                           session: TenantSession) -> CohortReadiness:
    visible = {c.id: c for c in await _visible_cohorts(session, principal)}
    cohort = visible.get(cohort_id)
    if cohort is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cohort not found")

    member_ids = list((await session.execute(
        select(CohortMember.user_id).where(CohortMember.cohort_id == cohort_id)
    )).scalars().all())
    latest = await _latest_overall(session, member_ids)

    bands = [band(latest.get(uid)) for uid in member_ids]
    scores = [s for s in latest.values()]

    return CohortReadiness(
        cohort_id=cohort.id,
        cohort_name=cohort.name,
        total=len(member_ids),
        assessed=len(latest),
        placement_ready=bands.count(READY),
        needs_training=bands.count(NEEDS_TRAINING),
        high_risk=bands.count(HIGH_RISK),
        not_started=bands.count(NOT_STARTED),
        average_overall=round(sum(scores) / len(scores), 1) if scores else None,
        days_to_drive=((cohort.drive_start.date() - date.today()).days
                       if cohort.drive_start else None),
    )


@router.get("/cohorts/{cohort_id}/students", response_model=list[StudentSummary])
async def cohort_students(cohort_id: str, principal: Principal,
                          session: TenantSession) -> list[StudentSummary]:
    visible = {c.id for c in await _visible_cohorts(session, principal)}
    if cohort_id not in visible:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cohort not found")

    users = list((await session.execute(
        select(User).join(CohortMember, CohortMember.user_id == User.id)
        .where(CohortMember.cohort_id == cohort_id, User.role == "student")
        .order_by(User.full_name)
    )).scalars().all())
    ids = [u.id for u in users]
    latest = await _latest_overall(session, ids)

    attempt_rows = (await session.execute(
        select(Attempt.user_id, func.count(), func.max(Attempt.created_at))
        .where(Attempt.user_id.in_(ids or [""])).group_by(Attempt.user_id)
    )).all()
    attempts = {uid: (count, last) for uid, count, last in attempt_rows}

    flagged = set((await session.execute(
        select(StudentFlag.user_id).where(StudentFlag.resolved.is_(False))
    )).scalars().all())

    now = datetime.now(timezone.utc)
    summaries: list[StudentSummary] = []
    for u in users:
        count, last = attempts.get(u.id, (0, None))
        summaries.append(StudentSummary(
            user=UserOut(
                id=u.id, email=u.email, full_name=u.full_name, role=u.role,
                active=u.active, roll_number=u.roll_number, branch=u.branch,
                year_of_study=u.year_of_study, l1_language=u.l1_language,
                created_at=u.created_at,
            ),
            attempts=count,
            last_attempt_at=last,
            overall_score=latest.get(u.id),
            readiness=band(latest.get(u.id)),
            days_since_activity=(now - last).days if last else None,
            flagged=u.id in flagged,
        ))
    return summaries


async def _one_of_mine(session: TenantSession, principal: Principal,
                       user_id: str) -> None:
    """Refuse unless this student is in a cohort this trainer can see.

    404 rather than 403: confirming that a user id exists in this institution
    is itself a disclosure, and a trainer probing ids should not be able to
    tell "not yours" from "not a person".

    Extracted so every trainer route that names a student asks the same
    question. The report route added below is the first one where getting it
    wrong would hand over somebody's whole assessment rather than a mastery
    curve.
    """
    visible = [c.id for c in await _visible_cohorts(session, principal)]
    in_scope = (await session.execute(
        select(CohortMember.id)
        .where(CohortMember.user_id == user_id,
               CohortMember.cohort_id.in_(visible or [""]))
    )).first()
    if in_scope is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not in your cohorts")


@router.get("/students/{user_id}/attempts", response_model=list[AttemptOut])
async def student_attempts(user_id: str, principal: Principal,
                           session: TenantSession) -> list[AttemptOut]:
    """Everything this student has sat, newest first.

    A trainer could see a student's overall score on the cohort table and
    their mastery curve, and had no way to open the report behind either.
    """
    await _one_of_mine(session, principal, user_id)

    rows = list((await session.execute(
        select(Attempt).where(Attempt.user_id == user_id)
        .order_by(Attempt.created_at.desc())
    )).scalars().all())

    names = {p.id: p.name for p in (await session.execute(
        select(SimulationProfile).where(
            SimulationProfile.id.in_([r.profile_id for r in rows] or [""]))
    )).scalars().all()}

    return [AttemptOut(
        id=r.id, profile_id=r.profile_id,
        profile_name=names.get(r.profile_id, ""),
        attempt_number=r.attempt_number, status=r.status, mode=r.mode,
        is_baseline=r.is_baseline, overall_score=None,
        started_at=r.started_at, submitted_at=r.submitted_at,
        scored_at=r.scored_at,
    ) for r in rows]


@router.get("/attempts/{attempt_id}/result", response_model=AttemptResult)
async def student_result(attempt_id: str, principal: Principal,
                         session: TenantSession) -> AttemptResult:
    """One student's report, for the trainer coaching them.

    Authorised through the attempt's owner rather than the attempt id: the id
    alone says nothing about whose cohort that person is in, and a trainer who
    guessed one would otherwise read a report for a student they do not teach.

    The same report the student sees, caveats and all. A coaching view with
    the hedging removed would be a different claim about the same numbers.
    """
    from app.routers.attempts import _result, finalise_attempt, pending_responses

    attempt = await session.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")

    await _one_of_mine(session, principal, attempt.user_id)

    if attempt.status == "scoring" and not await pending_responses(session, attempt_id):
        await finalise_attempt(session, attempt_id)
        await session.refresh(attempt)

    return await _result(session, attempt)


@router.get("/students/{user_id}/mastery", response_model=list[MasteryOut])
async def student_mastery(user_id: str, principal: Principal,
                          session: TenantSession) -> list[MasteryOut]:
    """Sub-skill mastery for one student — cohort-scoped, like every trainer view."""
    await _one_of_mine(session, principal, user_id)

    rows = (await session.execute(
        select(SkillMastery).where(SkillMastery.user_id == user_id)
        .order_by(SkillMastery.mastery)
    )).scalars().all()
    return [
        MasteryOut(skill=m.skill, mastery=m.mastery, baseline=m.baseline,
                   last_change=m.last_change, observations=m.observations)
        for m in rows
    ]
