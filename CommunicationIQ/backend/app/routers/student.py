"""Student surfaces.

Everything here is scoped to the caller: a student reads their own record and
nothing else. There is no student endpoint that takes another user's id.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app import formats, skills
from app import deadline as app_deadline
from app.deps import Principal, TenantSession, require_roles
from app.models.tenant import (Attempt, Cohort, CohortMember, ConsentRecord,
                               Quest, ScoreRecord, SimulationProfile,
                               SkillMastery, StreakState, User, XPLedger)
from app.schemas import (AttemptOut, ConsentRequest, MasteryOut,
                         SkillModuleOut, SkillsOverview,
                         ProfileSectionOut, QuestOut, SimulationProfileOut,
                         StreakOut, StudentHome, UserOut)

router = APIRouter(prefix="/student", tags=["student"],
                   dependencies=[Depends(require_roles("student"))])

# Consent, on its own router.
#
# Everything else under /student is a student's: their practice, their
# history, their progress. Consent is not -- it is the thing that must happen
# before anything is recorded, and an invited candidate has to be asked in
# exactly the same way. Leaving it on the student-only router meant a
# candidate could be admitted, handed an assessment, and then blocked at the
# first item by a permission they had no way to give.
#
# Its own router rather than widening the whole of /student, so the exception
# is one endpoint wide and visible in one line.
consent_router = APIRouter(
    prefix="/student", tags=["student"],
    dependencies=[Depends(require_roles("student", "candidate"))])

# Level thresholds. Deliberately generous and monotonic: Level is effort
# recognition and always moves up (GAM-03). Honesty lives in the Gap Meter.
_LEVEL_STEP = 500


def _level_for(xp: int) -> int:
    return 1 + xp // _LEVEL_STEP


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role,
        active=user.active, roll_number=user.roll_number, branch=user.branch,
        year_of_study=user.year_of_study, l1_language=user.l1_language,
        created_at=user.created_at,
    )


def _profile_out(profile: SimulationProfile) -> SimulationProfileOut:
    blueprint = formats.BY_CODE.get(profile.code)
    budgets = formats.section_budgets(profile.code)
    return SimulationProfileOut(
        id=profile.id, code=profile.code, name=profile.name, style=profile.style,
        company=profile.company,
        description=profile.description, status=profile.status,
        estimated_minutes=profile.estimated_minutes, is_baseline=profile.is_baseline,
        typical_minutes=(formats.typical_minutes(blueprint) if blueprint
                         else profile.estimated_minutes),
        sitting_limit_minutes=app_deadline.allowance_minutes(profile.estimated_minutes),
        # The scoring configuration, so it can be read back and edited.
        scoring_weights=dict(profile.scoring_weights or {}),
        pass_threshold=profile.pass_threshold,
        skill_thresholds=dict(profile.skill_thresholds or {}),
        target_role=profile.target_role, department=profile.department,
        difficulty_band=profile.difficulty_band,
        # From the blueprint where the profile came from one. A round an admin
        # authored by hand has none, and says nothing rather than something
        # generic and wrong.
        what_to_expect=list(blueprint.what_to_expect) if blueprint else [],
        not_included=blueprint.not_included if blueprint else "",
        provenance=blueprint.provenance if blueprint else "",
        sections=[
            ProfileSectionOut(
                id=s.id, position=s.position, title=s.title, task_type=s.task_type,
                instructions=s.instructions, item_count=s.item_count,
                prep_seconds=s.prep_seconds, response_seconds=s.response_seconds,
                prompt_plays_allowed=s.prompt_plays_allowed, allow_replay=s.allow_replay,
                budget_seconds=budgets.get(s.title, 0),
                weight=s.weight,
                # The filter, not the items it selects. A student seeing that
                # a section draws hard banking material is fine; seeing which
                # items it drew would not be.
                selection=dict(s.selection or {}),
            )
            for s in profile.sections
        ],
    )


@router.get("/home", response_model=StudentHome)
async def home(principal: Principal, session: TenantSession) -> StudentHome:
    user = await session.get(User, principal.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")

    consent = (await session.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user.id, ConsentRecord.scope == "recording")
        .order_by(ConsentRecord.at.desc())
    )).scalars().first()

    attempts = (await session.execute(
        select(Attempt).where(Attempt.user_id == user.id)
        .order_by(Attempt.created_at.desc()).limit(10)
    )).scalars().all()

    # Asked as its own question rather than read off the display list above.
    #
    # This used to be `any(a.is_baseline and a.status == "scored" for a in
    # attempts)` over that ten-row slice, so it really answered "is there a
    # scored baseline among your ten most recent attempts". A student who took
    # the baseline and then practised eleven more times was told they had
    # never taken it -- on a screen that was simultaneously listing their
    # scored baseline results underneath.
    baseline_done = bool((await session.execute(
        select(Attempt.id).where(Attempt.user_id == user.id,
                                 Attempt.is_baseline.is_(True),
                                 Attempt.status == "scored").limit(1)
    )).scalars().first())

    # Sections are loaded eagerly: an async session cannot lazy-load a
    # relationship mid-serialisation, and the runner needs the full shape.
    profiles = (await session.execute(
        select(SimulationProfile).where(SimulationProfile.status == "published")
        .options(selectinload(SimulationProfile.sections))
        .order_by(SimulationProfile.is_baseline.desc(), SimulationProfile.name)
    )).scalars().all()
    profile_names = {p.id: p.name for p in profiles}

    overall = dict((await session.execute(
        select(ScoreRecord.attempt_id, ScoreRecord.score)
        .where(ScoreRecord.dimension == "overall",
               ScoreRecord.is_shadow.is_(False),
               ScoreRecord.attempt_id.in_([a.id for a in attempts] or [""]))
    )).all())

    mastery = (await session.execute(
        select(SkillMastery).where(SkillMastery.user_id == user.id)
        .order_by(SkillMastery.mastery)
    )).scalars().all()

    total_xp = (await session.execute(
        select(func.coalesce(func.sum(XPLedger.awarded_xp), 0))
        .where(XPLedger.user_id == user.id)
    )).scalar_one()

    streak = (await session.execute(
        select(StreakState).where(StreakState.user_id == user.id)
    )).scalars().first()

    quest = (await session.execute(
        select(Quest).where(Quest.user_id == user.id, Quest.kind == "daily",
                            Quest.for_date == date.today())
    )).scalars().first()

    # Days to the real drive date, from the student's cohort. There is no other
    # countdown in the product (GAM-25).
    days_to_drive: int | None = None
    cohort = (await session.execute(
        select(Cohort).join(CohortMember, CohortMember.cohort_id == Cohort.id)
        .where(CohortMember.user_id == user.id, Cohort.active.is_(True))
    )).scalars().first()
    if cohort is not None and cohort.drive_start is not None:
        days_to_drive = (cohort.drive_start.date() - date.today()).days

    # The Gap Meter reads mastery only — never XP (GAM-23).
    gap_percent = round(100 * sum(m.mastery for m in mastery) / len(mastery), 1) if mastery else None

    return StudentHome(
        user=_to_user_out(user),
        consent_given=bool(consent and consent.granted),
        baseline_done=baseline_done,
        total_xp=int(total_xp),
        level=_level_for(int(total_xp)),
        gap_percent=gap_percent,
        streak=StreakOut(
            current_streak=streak.current_streak if streak else 0,
            best_streak=streak.best_streak if streak else 0,
            freezes_available=streak.freezes_available if streak else 0,
            last_qualifying_day=streak.last_qualifying_day if streak else None,
        ),
        quest=QuestOut(
            id=quest.id, kind=quest.kind, title=quest.title,
            description=quest.description, target_skill=quest.target_skill,
            progress=quest.progress, target=quest.target, completed=quest.completed,
            bonus_xp=quest.bonus_xp, for_date=quest.for_date,
        ) if quest else None,
        days_to_drive=days_to_drive,
        assigned_profiles=[_profile_out(p) for p in profiles],
        recent_attempts=[
            AttemptOut(
                id=a.id, profile_id=a.profile_id,
                profile_name=profile_names.get(a.profile_id, ""),
                attempt_number=a.attempt_number, status=a.status, mode=a.mode,
                is_baseline=a.is_baseline, overall_score=overall.get(a.id),
                started_at=a.started_at, submitted_at=a.submitted_at,
                scored_at=a.scored_at,
            )
            for a in attempts
        ],
        mastery=[
            MasteryOut(skill=m.skill, mastery=m.mastery, baseline=m.baseline,
                       last_change=m.last_change, observations=m.observations)
            for m in mastery
        ],
    )


@router.get("/skills", response_model=SkillsOverview)
async def skills_overview(principal: Principal,
                          session: TenantSession) -> SkillsOverview:
    """Reading, Writing, Listening and Speaking, and what each can really do.

    The headline is deliberately blunt. A student comparing this against a
    four-skill test should learn in one line that it measures one of them
    properly, rather than working it out from four cards.
    """
    modules = await skills.modules_for(session, principal.user_id)
    live = [m.label for m in modules if m.status == "live"]

    if len(live) == 4:
        headline = "All four skills are measured here."
    elif live:
        headline = (
            f"{' and '.join(live)} {'is' if len(live) == 1 else 'are'} fully "
            f"measured. The others are partly built or not started — each card "
            f"says which.")
    else:
        headline = "None of the four are fully measured yet."

    return SkillsOverview(
        headline=headline,
        modules=[SkillModuleOut(**vars(m)) for m in modules],
    )


@router.get("/profiles", response_model=list[SimulationProfileOut])
async def profiles(session: TenantSession) -> list[SimulationProfileOut]:
    rows = (await session.execute(
        select(SimulationProfile).where(SimulationProfile.status == "published")
        .options(selectinload(SimulationProfile.sections))
        .order_by(SimulationProfile.is_baseline.desc(), SimulationProfile.name)
    )).scalars().all()
    return [_profile_out(p) for p in rows]


@consent_router.post("/consent", status_code=status.HTTP_201_CREATED)
async def give_consent(body: ConsentRequest, principal: Principal,
                       session: TenantSession, request: Request) -> dict:
    """Record consent before anything is recorded (STU-02).

    Append-only. Withdrawing later writes a new row with ``granted=False``, so
    what a student had agreed to on any past date stays answerable.
    """
    granted = set(body.scopes)
    # ai_explanation covers sending a student's *scores* (never their words or
    # identity — see app/narration/evidence.py) to an external AI service that
    # writes a plain-language explanation of the result. Opting out is fully
    # non-blocking: the assessment and the deterministic report are unaffected.
    known = {"recording", "training_data", "outcome_sharing", "notifications",
             "ai_explanation"}
    unknown = granted - known
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Unknown consent scope(s): {', '.join(sorted(unknown))}")

    client_ip = request.client.host if request.client else ""
    for scope in sorted(known):
        session.add(ConsentRecord(
            user_id=principal.user_id, scope=scope, granted=scope in granted,
            notice_version=body.notice_version, notice_language=body.notice_language,
            ip_address=client_ip,
        ))
    await session.commit()
    return {"recorded": sorted(known), "granted": sorted(granted),
            "at": datetime.now(timezone.utc)}


@router.get("/attempts", response_model=list[AttemptOut])
async def attempts(principal: Principal, session: TenantSession) -> list[AttemptOut]:
    rows = (await session.execute(
        select(Attempt).where(Attempt.user_id == principal.user_id)
        .order_by(Attempt.created_at.desc())
    )).scalars().all()
    names = dict((await session.execute(
        select(SimulationProfile.id, SimulationProfile.name)
    )).all())
    overall = dict((await session.execute(
        select(ScoreRecord.attempt_id, ScoreRecord.score)
        .where(ScoreRecord.dimension == "overall", ScoreRecord.is_shadow.is_(False))
    )).all())
    return [
        AttemptOut(
            id=a.id, profile_id=a.profile_id, profile_name=names.get(a.profile_id, ""),
            attempt_number=a.attempt_number, status=a.status, mode=a.mode,
            is_baseline=a.is_baseline, overall_score=overall.get(a.id),
            started_at=a.started_at, submitted_at=a.submitted_at, scored_at=a.scored_at,
        )
        for a in rows
    ]
