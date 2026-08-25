"""Listening practice: hear a passage, then answer questions about it.

The order is the whole design. Questions are withheld until the audio has
been played, because a student who can read the questions first knows what to
listen for, and that measures scanning rather than comprehension. Real rounds
do not show you the questions in advance and neither does this.

The correct answers never leave the server before an attempt is submitted --
the same rule the quiz engine follows, for the same reason.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.deps import Principal, PlatformSession, TenantSession, require_roles
from app.engine.pipeline import SCALE_MAX, SCALE_MIN, band_label
from app.gamification import engine as game
from app.models.tenant import (ListeningAttempt, ListeningPassage, QuizItem,
                               SkillMastery)
from app.schemas import (ListeningAnswer, ListeningPassageOut,
                         ListeningQuestionOut, ListeningResult,
                         ListeningResultItem, ListeningStart, ListeningSubmission)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/student/listening", tags=["listening"],
                   dependencies=[Depends(require_roles("student"))])


def _score(correct: int, total: int) -> float:
    """Proportion correct, on the product's internal 20-80 scale.

    The same scale as every other measure here, so a Listening score can sit
    beside a Speaking one without a silent change of units. Not calibrated
    against human judgement -- nothing in this product is yet -- but it is at
    least the same uncalibrated scale.
    """
    if total <= 0:
        return SCALE_MIN
    return round(SCALE_MIN + (SCALE_MAX - SCALE_MIN) * (correct / total), 1)


@router.get("/passages", response_model=list[ListeningPassageOut])
async def passages(principal: Principal,
                   session: TenantSession) -> list[ListeningPassageOut]:
    """Everything available, with how the student has done on each.

    Includes passages already attempted: re-listening to something you scored
    badly on is the point, not a loophole.
    """
    rows = list((await session.execute(
        select(ListeningPassage).where(ListeningPassage.status == "published")
        .order_by(ListeningPassage.difficulty)
    )).scalars().all())

    counts = dict((await session.execute(
        select(QuizItem.passage_id, func.count())
        .where(QuizItem.category == "audio_comprehension",
               QuizItem.status == "published")
        .group_by(QuizItem.passage_id)
    )).all())

    best: dict[str, float] = {}
    for passage_id, score in (await session.execute(
        select(ListeningAttempt.passage_id, func.max(ListeningAttempt.score))
        .where(ListeningAttempt.user_id == principal.user_id,
               ListeningAttempt.score.is_not(None))
        .group_by(ListeningAttempt.passage_id)
    )).all():
        best[passage_id] = score

    return [
        ListeningPassageOut(
            id=p.id, title=p.title, kind=p.kind,
            approx_seconds=p.approx_seconds, plays_allowed=p.plays_allowed,
            question_count=int(counts.get(p.id, 0)),
            best_score=best.get(p.id),
            # No transcript here. It is the answer sheet.
            has_recording=bool(p.audio_key),
        )
        for p in rows if counts.get(p.id, 0) > 0
    ]


@router.post("/passages/{passage_id}/start", response_model=ListeningStart)
async def start(passage_id: str, principal: Principal,
                session: TenantSession) -> ListeningStart:
    """Open an attempt and hand over the words to be spoken -- not the questions.

    The transcript goes to the client because there is no recording yet and
    the browser speaks it. That is a real weakness of doing it this way: a
    determined student can read it out of the network tab instead of
    listening. It is disclosed rather than pretended away, and it is why this
    is practice rather than assessment. A recorded passage would close it.
    """
    passage = await session.get(ListeningPassage, passage_id)
    if passage is None or passage.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such passage")

    total = int((await session.execute(
        select(func.count()).select_from(QuizItem)
        .where(QuizItem.passage_id == passage_id,
               QuizItem.category == "audio_comprehension",
               QuizItem.status == "published")
    )).scalar_one())
    if total == 0:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "That passage has no questions written for it yet")

    attempt = ListeningAttempt(user_id=principal.user_id, passage_id=passage_id,
                               total=total)
    session.add(attempt)
    await session.commit()

    return ListeningStart(
        attempt_id=attempt.id, passage_id=passage.id, title=passage.title,
        kind=passage.kind, transcript=passage.transcript, accent=passage.accent,
        plays_allowed=passage.plays_allowed, question_count=total,
        audio_key=passage.audio_key,
    )


@router.get("/attempts/{attempt_id}/questions",
            response_model=list[ListeningQuestionOut])
async def questions(attempt_id: str, principal: Principal,
                    session: TenantSession) -> list[ListeningQuestionOut]:
    """The questions, once the passage has been heard.

    Correct answers are not included. They arrive with the result.
    """
    attempt = await session.get(ListeningAttempt, attempt_id)
    if attempt is None or attempt.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such attempt")
    if attempt.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That attempt is finished")

    rows = list((await session.execute(
        select(QuizItem).where(QuizItem.passage_id == attempt.passage_id,
                               QuizItem.category == "audio_comprehension",
                               QuizItem.status == "published")
        .order_by(QuizItem.id)
    )).scalars().all())

    return [ListeningQuestionOut(id=q.id, stem=q.stem, options=list(q.options))
            for q in rows]


@router.post("/attempts/{attempt_id}/submit", response_model=ListeningResult)
async def submit(attempt_id: str, body: ListeningSubmission,
                 principal: Principal, session: TenantSession,
                 platform: PlatformSession) -> ListeningResult:
    """Mark the answers, record the score, and move the daily loop."""
    attempt = await session.get(ListeningAttempt, attempt_id)
    if attempt is None or attempt.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such attempt")
    if attempt.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already submitted")

    rows = {q.id: q for q in (await session.execute(
        select(QuizItem).where(QuizItem.passage_id == attempt.passage_id,
                               QuizItem.category == "audio_comprehension",
                               QuizItem.status == "published")
    )).scalars().all()}

    chosen = {a.item_id: a.selected_index for a in body.answers}
    results: list[ListeningResultItem] = []
    correct = 0
    for item_id, item in rows.items():
        picked = chosen.get(item_id)
        is_right = picked == item.correct_index
        correct += int(is_right)
        results.append(ListeningResultItem(
            item_id=item_id, stem=item.stem, options=list(item.options),
            selected_index=picked, correct_index=item.correct_index,
            is_correct=is_right, explanation=item.explanation,
        ))

    total = len(rows)
    score = _score(correct, total)

    attempt.correct = correct
    attempt.total = total
    attempt.score = score
    attempt.plays_used = max(1, int(body.plays_used or 1))
    attempt.completed_at = datetime.now(timezone.utc)

    # Deliberately not a ScoreRecord. That table hangs off a speaking attempt
    # by a non-nullable foreign key, and manufacturing an empty Attempt row to
    # carry a listening score would put a fake speaking attempt into every
    # report that counts them. The ListeningAttempt row is the record; mastery
    # below is how this reaches the rest of the product.

    # This is a direct measurement of listening, unlike the repeat-accuracy
    # signal the skill has been fed until now.
    await _update_listening_mastery(session, principal.user_id, score)

    passage = await session.get(ListeningPassage, attempt.passage_id)
    await session.commit()

    award_xp, day_counted, streak_now = await _reward(
        session, platform, principal, attempt.id, correct, total)

    return ListeningResult(
        attempt_id=attempt.id,
        title=passage.title if passage else "",
        correct=correct, total=total, score=score,
        band=band_label(score),
        transcript=passage.transcript if passage else "",
        items=results,
        xp_awarded=award_xp,
        day_counted_now=day_counted,
        streak_current=streak_now,
    )


async def _update_listening_mastery(session, user_id: str, score: float) -> None:
    """Move the listening mastery from a real comprehension result.

    Kept out of the frozen scoring pipeline on purpose: that pipeline is
    hashed for the validation study and this is a new measure that has never
    been part of it. The arithmetic is a plain exponential update rather than
    the BKT the speech dimensions use, because BKT parameters for listening
    comprehension have not been fitted to anything.
    """
    row = (await session.execute(
        select(SkillMastery).where(SkillMastery.user_id == user_id,
                                   SkillMastery.skill == "listening")
    )).scalars().first()

    observed = max(0.0, min(1.0, (score - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)))
    if row is None:
        session.add(SkillMastery(user_id=user_id, skill="listening",
                                 mastery=round(observed, 4),
                                 baseline=round(observed, 4),
                                 confidence=0.3, observations=1,
                                 last_change=0.0))
        return

    prior = float(row.mastery)
    # Weighted toward the record rather than the newest sitting: one bad
    # morning should move a mastery estimate, not replace it.
    posterior = 0.7 * prior + 0.3 * observed
    row.last_change = round(posterior - prior, 4)
    row.mastery = round(posterior, 4)
    row.observations = int(row.observations or 0) + 1
    row.confidence = min(0.9, float(row.confidence or 0.3) + 0.05)


async def _reward(session, platform, principal, attempt_id: str,
                  correct: int, total: int) -> tuple[int, bool, int]:
    """XP, quest and streak. Never costs a student their result if it fails."""
    try:
        config = await game.config_for(platform, principal.tenant_id)
        award = await game.award(
            session, config, principal.user_id, "quiz_completed",
            ref_type="listening", ref_id=attempt_id, target_skill="listening",
            difficulty=("above_ability" if correct < total * 0.5
                        else "at_ability" if correct < total * 0.85
                        else "below_ability"),
        )
        await game.advance_quest(session, config, principal.user_id,
                                 amount=float(total), skill="listening")
        before = await game.streak_state(session, principal.user_id)
        counted_before = before.last_qualifying_day
        await game.qualify_today(session, config, principal.user_id)
        after = await game.streak_state(session, principal.user_id)
        await session.commit()
        return (award.awarded_xp,
                after.last_qualifying_day != counted_before,
                after.current_streak)
    except Exception as exc:  # noqa: BLE001
        log.warning("listening reward hook failed for %s: %s", attempt_id, exc)
        await session.rollback()
        return 0, False, 0
