"""Writing practice: a real task, and five measures of the answer.

The scoring lives in ``app.writing``; this exposes it and keeps the text.

Submissions are stored in full. A writing score with no writing behind it
cannot be checked by a trainer, appealed by a student, or re-marked when the
scorer improves -- and this scorer is a first version that will improve. The
measures are stored exactly as produced, alongside the version that produced
them, so a later re-mark can be compared against what the student was told at
the time.
"""
from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app import writing as scorer
from app.deps import Principal, PlatformSession, TenantSession, require_roles
from app.gamification import engine as game
from app.models.tenant import SkillMastery, WritingPrompt, WritingSubmissionRow
from app.schemas import (WritingMeasureOut, WritingPromptOut, WritingResult,
                         WritingSubmission)

log = logging.getLogger(__name__)

SCORER_VERSION = "0.1.0"

router = APIRouter(prefix="/student/writing", tags=["writing"],
                   dependencies=[Depends(require_roles("student"))])


def _label(point) -> str:
    """The student-facing half of a rubric point, without its cues."""
    return str(point.get("point", "")) if isinstance(point, dict) else str(point)


@router.get("/prompts", response_model=list[WritingPromptOut])
async def prompts(principal: Principal,
                  session: TenantSession) -> list[WritingPromptOut]:
    rows = list((await session.execute(
        select(WritingPrompt).where(WritingPrompt.status == "published")
        .order_by(WritingPrompt.difficulty)
    )).scalars().all())

    best = dict((await session.execute(
        select(WritingSubmissionRow.prompt_id,
               func.max(WritingSubmissionRow.overall))
        .where(WritingSubmissionRow.user_id == principal.user_id,
               WritingSubmissionRow.overall.is_not(None))
        .group_by(WritingSubmissionRow.prompt_id)
    )).all())

    return [
        WritingPromptOut(
            id=p.id, title=p.title, kind=p.kind, scenario=p.scenario,
            prompt=p.prompt, min_words=p.min_words,
            suggested_minutes=p.suggested_minutes,
            # The rubric labels are shown. This is practice, and a student
            # who knows what a competent answer must cover learns more than
            # one guessing at it -- the points say what to address, never what
            # to say.
            #
            # The cues are stripped. They are the words the scorer looks for,
            # and handing them over would let a student paste them in and
            # score full marks on task response without writing anything: the
            # measure would be checking whether they read the API response.
            key_points=[_label(point) for point in (p.key_points or [])],
            best_score=best.get(p.id),
        )
        for p in rows
    ]


@router.post("/prompts/{prompt_id}/submit", response_model=WritingResult)
async def submit(prompt_id: str, body: WritingSubmission,
                 principal: Principal, session: TenantSession,
                 platform: PlatformSession) -> WritingResult:
    prompt = await session.get(WritingPrompt, prompt_id)
    if prompt is None or prompt.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such prompt")

    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing was written")

    result = await scorer.score_essay(
        text, key_points=list(prompt.key_points or []),
        min_words=int(prompt.min_words or 0))

    row = WritingSubmissionRow(
        user_id=principal.user_id, prompt_id=prompt_id, text=text,
        word_count=result.word_count,
        minutes_spent=max(0, int(body.minutes_spent or 0)),
        overall=result.overall,
        measures={m.name: {"score": m.score, "confidence": m.confidence,
                           "basis": m.basis} for m in result.measures},
        scorer_version=SCORER_VERSION,
    )
    session.add(row)

    if result.overall is not None:
        await _update_writing_mastery(session, principal.user_id, result.overall)
    await session.commit()

    xp, day_counted, streak_now = (0, False, 0)
    if result.overall is not None:
        xp, day_counted, streak_now = await _reward(
            session, platform, principal, row.id, result.overall)

    return WritingResult(
        submission_id=row.id, title=prompt.title,
        word_count=result.word_count, overall=result.overall,
        too_short=result.too_short, notes=list(result.notes),
        measures=[WritingMeasureOut(**asdict(m)) for m in result.measures],
        # Returned so the student can read their own writing against the
        # feedback rather than from memory.
        text=text,
        xp_awarded=xp, day_counted_now=day_counted, streak_current=streak_now,
    )


@router.get("/submissions", response_model=list[WritingResult])
async def submissions(principal: Principal,
                      session: TenantSession) -> list[WritingResult]:
    """Everything this student has written, newest first.

    Kept visible because improvement in writing is only legible over time:
    one piece is a data point, six is a direction.
    """
    rows = list((await session.execute(
        select(WritingSubmissionRow)
        .where(WritingSubmissionRow.user_id == principal.user_id)
        .order_by(WritingSubmissionRow.submitted_at.desc()).limit(20)
    )).scalars().all())

    titles = dict((await session.execute(
        select(WritingPrompt.id, WritingPrompt.title))).all())

    return [
        WritingResult(
            submission_id=r.id, title=titles.get(r.prompt_id, ""),
            word_count=r.word_count, overall=r.overall,
            too_short=False, notes=[],
            measures=[
                WritingMeasureOut(name=name, score=float(v.get("score", 0)),
                                  confidence=float(v.get("confidence", 0)),
                                  basis=str(v.get("basis", "")), detail={})
                for name, v in (r.measures or {}).items()
            ],
            text=r.text,
        )
        for r in rows
    ]


async def _update_writing_mastery(session, user_id: str, overall: float) -> None:
    """Writing feeds the `grammar` mastery track for now.

    There is no `writing` skill in the mastery vocabulary. Adding one is a
    psychometrics change -- the BKT parameters are fitted per skill and there
    is nothing here to fit them against yet -- so this shares the closest
    existing track and the skills card says so, the same disclosure rule
    Listening and Reading follow.
    """
    row = (await session.execute(
        select(SkillMastery).where(SkillMastery.user_id == user_id,
                                   SkillMastery.skill == "grammar")
    )).scalars().first()

    observed = max(0.0, min(1.0, (overall - scorer.SCALE_MIN)
                            / (scorer.SCALE_MAX - scorer.SCALE_MIN)))
    if row is None:
        session.add(SkillMastery(user_id=user_id, skill="grammar",
                                 mastery=round(observed, 4),
                                 baseline=round(observed, 4),
                                 confidence=0.3, observations=1, last_change=0.0))
        return
    prior = float(row.mastery)
    posterior = 0.8 * prior + 0.2 * observed
    row.last_change = round(posterior - prior, 4)
    row.mastery = round(posterior, 4)
    row.observations = int(row.observations or 0) + 1
    row.confidence = min(0.9, float(row.confidence or 0.3) + 0.04)


async def _reward(session, platform, principal, submission_id: str,
                  overall: float) -> tuple[int, bool, int]:
    try:
        config = await game.config_for(platform, principal.tenant_id)
        award = await game.award(
            session, config, principal.user_id, "drill_completed",
            ref_type="writing", ref_id=submission_id, target_skill="grammar",
            difficulty="at_ability",
        )
        await game.advance_quest(session, config, principal.user_id,
                                 amount=5.0, skill="grammar")
        before = await game.streak_state(session, principal.user_id)
        counted_before = before.last_qualifying_day
        await game.qualify_today(session, config, principal.user_id)
        after = await game.streak_state(session, principal.user_id)
        await session.commit()
        return (award.awarded_xp,
                after.last_qualifying_day != counted_before,
                after.current_streak)
    except Exception as exc:  # noqa: BLE001
        log.warning("writing reward hook failed for %s: %s", submission_id, exc)
        await session.rollback()
        return 0, False, 0
