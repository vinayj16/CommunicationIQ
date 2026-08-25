"""Institution console — the tenant admin's own view of their institution.

Every query runs against the caller's schema. There is no institution
identifier in any signature here, because there is nowhere else to look.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.deps import PlatformSession, Principal, TenantSession, require_roles
from app.models.platform import Plan, Tenant
from app.models.tenant import (Attempt, Cohort, CohortMember, ConsentRecord,
                               SimulationProfile, User)
from app.schemas import (CohortOut, ProfileSectionOut, SimulationProfileOut,
                         TenantOverview, UserOut)

router = APIRouter(prefix="/tenant", tags=["tenant-admin"],
                   dependencies=[Depends(require_roles("tenant_admin"))])


@router.get("/overview", response_model=TenantOverview)
async def overview(principal: Principal, session: TenantSession,
                   platform: PlatformSession) -> TenantOverview:
    tenant = await platform.get(Tenant, principal.tenant_id or "")
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")
    plan = await platform.get(Plan, tenant.plan_id) if tenant.plan_id else None

    counts = dict((await session.execute(
        select(User.role, func.count()).where(User.active.is_(True)).group_by(User.role)
    )).all())
    cohorts = (await session.execute(
        select(func.count()).select_from(Cohort).where(Cohort.active.is_(True))
    )).scalar_one()
    attempts = (await session.execute(select(func.count()).select_from(Attempt))).scalar_one()

    students = counts.get("student", 0)
    consented = (await session.execute(
        select(func.count(func.distinct(ConsentRecord.user_id)))
        .where(ConsentRecord.scope == "recording", ConsentRecord.granted.is_(True))
    )).scalar_one()

    return TenantOverview(
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        plan_name=plan.name if plan else "",
        seats_used=students + counts.get("trainer", 0) + counts.get("tenant_admin", 0),
        seat_limit=tenant.seat_limit,
        students=students,
        trainers=counts.get("trainer", 0),
        cohorts=int(cohorts),
        attempts_total=int(attempts),
        consent_pending=max(students - int(consented), 0),
    )


@router.get("/users", response_model=list[UserOut])
async def users(session: TenantSession, role: str | None = None) -> list[UserOut]:
    stmt = select(User).order_by(User.role, User.full_name)
    if role:
        stmt = stmt.where(User.role == role)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        UserOut(
            id=u.id, email=u.email, full_name=u.full_name, role=u.role, active=u.active,
            roll_number=u.roll_number, branch=u.branch, year_of_study=u.year_of_study,
            l1_language=u.l1_language, created_at=u.created_at,
        )
        for u in rows
    ]


@router.get("/cohorts", response_model=list[CohortOut])
async def cohorts(session: TenantSession) -> list[CohortOut]:
    rows = (await session.execute(select(Cohort).order_by(Cohort.name))).scalars().all()
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


@router.get("/profiles", response_model=list[SimulationProfileOut])
async def profiles(session: TenantSession,
                   include_retired: bool = False) -> list[SimulationProfileOut]:
    """The assessment library.

    Retired assessments are excluded unless asked for, and the default is the
    important part.

    Retiring is how an assessment leaves circulation here, and it is a
    deliberate choice over deleting: attempts name their profile, and a result
    whose profile vanished cannot be read back. The consequence is that
    retired rows accumulate permanently, and this endpoint returned every one
    of them with its sections attached. On the demo estate that was 1466 rows
    and a 1.25 MB response, on a screen that also renders each of them as a
    card -- so the library an admin actually works in was 190 KB of
    assessments nobody can sit.

    That is not a seeding artefact. It is what any customer's library becomes
    after a few years of ordinary use.
    """
    stmt = (select(SimulationProfile)
            .options(selectinload(SimulationProfile.sections))
            .order_by(SimulationProfile.style, SimulationProfile.name))
    if not include_retired:
        stmt = stmt.where(SimulationProfile.status != "retired")
    rows = (await session.execute(stmt)).scalars().all()
    # Sections are loaded here now: the console is a builder rather than a
    # list, and an admin cannot edit a section they were never sent.
    return [
        SimulationProfileOut(
            id=p.id, code=p.code, name=p.name, style=p.style, company=p.company,
            description=p.description,
            status=p.status, estimated_minutes=p.estimated_minutes,
            is_baseline=p.is_baseline,
            # The scoring configuration, so it can be read back and edited.
            scoring_weights=dict(p.scoring_weights or {}),
            pass_threshold=p.pass_threshold,
            skill_thresholds=dict(p.skill_thresholds or {}),
            target_role=p.target_role, department=p.department,
            difficulty_band=p.difficulty_band,
            sections=[
                ProfileSectionOut(
                    id=x.id, position=x.position, title=x.title,
                    task_type=x.task_type, instructions=x.instructions,
                    item_count=x.item_count, prep_seconds=x.prep_seconds,
                    response_seconds=x.response_seconds,
                    prompt_plays_allowed=x.prompt_plays_allowed,
                    allow_replay=x.allow_replay,
                    weight=x.weight,
                )
                for x in sorted(p.sections, key=lambda x: x.position)
            ],
        )
        for p in rows
    ]


@router.get("/season")
async def season(session: TenantSession) -> list[dict]:
    """Each cohort's real placement window and what it implies (TEN-13)."""
    rows = (await session.execute(
        select(Cohort).where(Cohort.active.is_(True)).order_by(Cohort.name)
    )).scalars().all()
    out = []
    for c in rows:
        days = (c.drive_start.date() - date.today()).days if c.drive_start else None
        out.append({
            "cohort_id": c.id,
            "cohort_name": c.name,
            "drive_start": c.drive_start,
            "drive_end": c.drive_end,
            "days_to_drive": days,
            # No date set means a rolling 90-day season, never an invented deadline.
            "season_source": "drive_date" if c.drive_start else "rolling_90_day",
        })
    return out
