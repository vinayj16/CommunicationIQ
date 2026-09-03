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

from app.deps import Principal, TenantModels, require_roles
from app.engine.pipeline import SCALE_MAX, SCALE_MIN, band_label
from app.gamification import engine as game
from app.schemas import (ListeningAnswer, ListeningPassageOut,
                         ListeningQuestionOut, ListeningResult,
                         ListeningResultItem, ListeningStart, ListeningSubmission)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/student/listening", tags=["listening"],
                   dependencies=[Depends(require_roles("student"))])


def _score(correct: int, total: int) -> float:
    """Proportion correct, on the product's internal 0-100 scale.

    The same scale as every other measure here, so a Listening score can sit
    beside a Speaking one without a silent change of units. Not calibrated
    against human judgement -- nothing in this product is yet -- but it is at
    least the same uncalibrated scale.
    """
    if total <= 0:
        return SCALE_MIN
    return round(SCALE_MIN + (SCALE_MAX - SCALE_MIN) * (correct / total), 1)

@router.get("/random", response_model=ListeningStart)
async def random_passage(principal: Principal, models: TenantModels,
                          company: str = "") -> ListeningStart:
    """Get a random listening passage for practice. Guarantees exactly 10 questions."""
    import random as _rand
    TARGET_QUESTIONS = 10

    query = models.ListeningPassage.find(models.ListeningPassage.status == "published")
    if company:
        all_rows = []
        for p in await query.to_list():
            if p.company and p.company.lower() == company.lower():
                all_rows.append(p)
    else:
        all_rows = await query.to_list()
    if not all_rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No listening passages available")

    # Exclude passages already attempted by this user
    attempted = await models.ListeningAttempt.find(
        models.ListeningAttempt.user_id == principal.user_id
    ).to_list()
    attempted_ids = {a.passage_id for a in attempted}
    if attempted_ids:
        all_rows = [p for p in all_rows if p.id not in attempted_ids]

    coll = models.QuizItem.get_motor_collection()
    q_counts_raw = await coll.aggregate([
        {"$match": {"category": "audio_comprehension", "status": "published"}},
        {"$group": {"_id": "$passage_id", "count": {"$sum": 1}}},
    ]).to_list(None)
    q_counts = {doc["_id"]: doc["count"] for doc in q_counts_raw}

    ready = [p for p in all_rows if q_counts.get(p.id, 0) >= TARGET_QUESTIONS]
    partial = [p for p in all_rows if 0 < q_counts.get(p.id, 0) < TARGET_QUESTIONS]
    empty = [p for p in all_rows if q_counts.get(p.id, 0) == 0]

    if ready:
        passage = _rand.choice(ready)
    elif partial:
        passage = _rand.choice(partial)
        existing = q_counts.get(passage.id, 0)
        await _auto_generate_questions(models, passage, count=TARGET_QUESTIONS - existing)
    elif empty:
        passage = _rand.choice(empty)
        await _auto_generate_questions(models, passage, count=TARGET_QUESTIONS)
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No listening passages available")

    total = int(await models.QuizItem.find(
        models.QuizItem.passage_id == passage.id,
        models.QuizItem.category == "audio_comprehension",
        models.QuizItem.status == "published"
    ).count())
    if total == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Could not prepare questions")

    attempt = models.ListeningAttempt(user_id=principal.user_id,
                                      passage_id=passage.id, total=total)
    await attempt.create()

    return ListeningStart(
        attempt_id=attempt.id, passage_id=passage.id, title=passage.title,
        kind=passage.kind, transcript=passage.transcript, accent=passage.accent,
        plays_allowed=passage.plays_allowed, question_count=total,
        audio_key=passage.audio_key,
    )


async def _auto_generate_questions(models, passage, count: int = 10) -> None:
    """Generate comprehension questions for a listening passage."""
    import random as _rand
    transcript = passage.transcript or ""
    title = passage.title or "the passage"
    sentences = [s.strip() for s in transcript.replace('\n', ' ').split('.') if len(s.strip()) > 15]
    if not sentences:
        sentences = [title]
    third = sentences[2] if len(sentences) > 2 else sentences[-1]
    last = sentences[-1] if len(sentences) > 1 else sentences[0]

    templates = [
        {
            "stem": f"What is the main topic discussed in this audio?",
            "options": [
                f"The audio discusses important aspects of {title.lower()}.",
                "The audio is about an unrelated subject.",
                "The audio discusses only historical dates.",
                "The audio gives no information about the subject."
            ],
            "correct_index": 0,
        },
        {
            "stem": "Which detail is mentioned in the audio?",
            "options": [
                sentences[0][:120] + ('.' if not sentences[0].endswith('.') else ''),
                "The audio rejects the subject completely.",
                "The audio says the subject has no practical value.",
                "The audio provides no explanation."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What can you infer from the audio?",
            "options": [
                f"The audio provides useful information about {title.lower()}.",
                "The audio contradicts itself.",
                "The audio has no clear point.",
                "The audio is purely fictional."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What is the speaker's main purpose?",
            "options": [
                f"To inform listeners about {title.lower()}.",
                "To entertain with a fictional story.",
                "To persuade listeners to buy a product.",
                "To criticize a specific individual."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What is the best summary of the audio?",
            "options": [
                transcript[:200] + ('...' if len(transcript) > 200 else ''),
                "It says the topic has no value at all.",
                "It focuses on a completely different subject.",
                "It gives no practical information."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What is the tone of the speaker?",
            "options": [
                "Informative and professional.",
                "Angry and emotional.",
                "Humorous and sarcastic.",
                "Confused and uncertain."
            ],
            "correct_index": 0,
        },
        {
            "stem": "Which additional detail supports the main idea?",
            "options": [
                third[:120] + ('.' if not third.endswith('.') else ''),
                "The audio provides no supporting details.",
                "All details are contradictory.",
                "The audio only contains opinions, not facts."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What conclusion does the speaker reach?",
            "options": [
                last[:120] + ('.' if not last.endswith('.') else ''),
                "The speaker reaches no conclusion.",
                "The conclusion contradicts the main point.",
                "The conclusion is unrelated to the topic."
            ],
            "correct_index": 0,
        },
        {
            "stem": "Who is the intended audience for this audio?",
            "options": [
                f"People interested in {title.lower()}.",
                "Only children.",
                "Only scientists.",
                "Only politicians."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What type of audio is this?",
            "options": [
                f"An informational passage about {title.lower()}.",
                "A fictional story.",
                "A song.",
                "A sports commentary."
            ],
            "correct_index": 0,
        },
    ]

    for tmpl in templates[:count]:
        correct_text = tmpl["options"][tmpl["correct_index"]]
        shuffled = tmpl["options"][:]
        _rand.shuffle(shuffled)
        tmpl["options"] = shuffled
        tmpl["correct_index"] = shuffled.index(correct_text)

        item = models.QuizItem(
            stem=tmpl["stem"],
            options=tmpl["options"],
            correct_index=tmpl["correct_index"],
            explanation="Based on the audio content.",
            category="audio_comprehension",
            passage_id=passage.id,
            company=passage.company or "",
            status="published",
            difficulty=0.5,
            seconds_allowed=30,
        )
        await item.create()


@router.get("/passages", response_model=list[ListeningPassageOut])
async def passages(principal: Principal,
                   models: TenantModels,
                   company: str = "",
                   limit: int = 10) -> list[ListeningPassageOut]:
    """Everything available, with how the student has done on each.

    Includes passages already attempted: re-listening to something you scored
    badly on is the point, not a loophole.
    """
    # Practice shows general passages by default.
    # "General" and empty company both count as general (non-company) content.
    # Company-specific passages are only shown when company param is provided.
    query = models.ListeningPassage.find(models.ListeningPassage.status == "published")
    if company:
        query = query.find(models.ListeningPassage.company == company)
    import random as _rand
    all_rows = await query.to_list()
    _rand.shuffle(all_rows)
    rows = all_rows[:max(1, min(limit, 50))]

    coll = models.QuizItem.get_motor_collection()
    counts = {doc["_id"]: doc["count"] for doc in await coll.aggregate([
        {"$match": {"category": "audio_comprehension", "status": "published"}},
        {"$group": {"_id": "$passage_id", "count": {"$sum": 1}}},
    ]).to_list(None)}

    coll = models.ListeningAttempt.get_motor_collection()
    best = {doc["_id"]: doc["max"] for doc in await coll.aggregate([
        {"$match": {"user_id": principal.user_id, "score": {"$ne": None}}},
        {"$group": {"_id": "$passage_id", "max": {"$max": "$score"}}},
    ]).to_list(None)}

    return [
        ListeningPassageOut(
            id=p.id, title=p.title, kind=p.kind,
            approx_seconds=p.approx_seconds, plays_allowed=p.plays_allowed,
            question_count=int(counts.get(p.id, 0)),
            best_score=best.get(p.id),
            # No transcript here. It is the answer sheet.
            has_recording=bool(p.audio_key),
        )
        for p in rows
    ]


@router.post("/passages/{passage_id}/start", response_model=ListeningStart)
async def start(passage_id: str, principal: Principal,
                models: TenantModels) -> ListeningStart:
    """Open an attempt and hand over the words to be spoken -- not the questions.

    The transcript goes to the client because there is no recording yet and
    the browser speaks it. That is a real weakness of doing it this way: a
    determined student can read it out of the network tab instead of
    listening. It is disclosed rather than pretended away, and it is why this
    is practice rather than assessment. A recorded passage would close it.
    """
    # Subscription check for general users
    from app.subscription import require_subscription
    await require_subscription(principal)

    passage = await models.ListeningPassage.get(passage_id)
    if passage is None or passage.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such passage")

    total = int(await models.QuizItem.find(
        models.QuizItem.passage_id == passage_id,
        models.QuizItem.category == "audio_comprehension",
        models.QuizItem.status == "published"
    ).count())
    if total == 0:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "That passage has no questions written for it yet")

    attempt = models.ListeningAttempt(user_id=principal.user_id,
                                      passage_id=passage_id, total=total)
    await attempt.create()

    return ListeningStart(
        attempt_id=attempt.id, passage_id=passage.id, title=passage.title,
        kind=passage.kind, transcript=passage.transcript, accent=passage.accent,
        plays_allowed=passage.plays_allowed, question_count=total,
        audio_key=passage.audio_key,
    )


@router.get("/attempts/{attempt_id}/questions",
            response_model=list[ListeningQuestionOut])
async def questions(attempt_id: str, principal: Principal,
                    models: TenantModels) -> list[ListeningQuestionOut]:
    """The questions, once the passage has been heard.

    Correct answers are not included. They arrive with the result.
    """
    attempt = await models.ListeningAttempt.get(attempt_id)
    if attempt is None or attempt.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such attempt")
    if attempt.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That attempt is finished")

    rows = await models.QuizItem.find(
        models.QuizItem.passage_id == attempt.passage_id,
        models.QuizItem.category == "audio_comprehension",
        models.QuizItem.status == "published"
    ).sort(models.QuizItem.id).to_list()

    return [ListeningQuestionOut(id=q.id, stem=q.stem, options=list(q.options))
            for q in rows]


@router.post("/attempts/{attempt_id}/submit", response_model=ListeningResult)
async def submit(attempt_id: str, body: ListeningSubmission,
                 principal: Principal, models: TenantModels) -> ListeningResult:
    """Mark the answers, record the score, and move the daily loop."""
    attempt = await models.ListeningAttempt.get(attempt_id)
    if attempt is None or attempt.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such attempt")
    if attempt.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already submitted")

    rows = {q.id: q for q in await models.QuizItem.find(
        models.QuizItem.passage_id == attempt.passage_id,
        models.QuizItem.category == "audio_comprehension",
        models.QuizItem.status == "published").to_list()}

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
    await attempt.save()
    await _update_listening_mastery(models, principal.user_id, score)

    passage = await models.ListeningPassage.get(attempt.passage_id)

    award_xp, day_counted, streak_now = await _reward(
        models, principal, attempt.id, correct, total)

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


async def _update_listening_mastery(models, user_id: str, score: float) -> None:
    """Move the listening mastery from a real comprehension result.

    Kept out of the frozen scoring pipeline on purpose: that pipeline is
    hashed for the validation study and this is a new measure that has never
    been part of it. The arithmetic is a plain exponential update rather than
    the BKT the speech dimensions use, because BKT parameters for listening
    comprehension have not been fitted to anything.
    """
    row = await models.SkillMastery.find_one(
        models.SkillMastery.user_id == user_id,
        models.SkillMastery.skill == "listening")

    observed = max(0.0, min(1.0, (score - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)))
    if row is None:
        await models.SkillMastery(user_id=user_id, skill="listening",
                                  mastery=round(observed, 4),
                                  baseline=round(observed, 4),
                                  confidence=0.3, observations=1,
                                  last_change=0.0).create()
        return

    prior = float(row.mastery)
    # Weighted toward the record rather than the newest sitting: one bad
    # morning should move a mastery estimate, not replace it.
    posterior = 0.7 * prior + 0.3 * observed
    row.last_change = round(posterior - prior, 4)
    row.mastery = round(posterior, 4)
    row.observations = int(row.observations or 0) + 1
    row.confidence = min(0.9, float(row.confidence or 0.3) + 0.05)
    await row.save()


async def _reward(models, principal, attempt_id: str,
                  correct: int, total: int) -> tuple[int, bool, int]:
    """XP, quest and streak. Never costs a student their result if it fails."""
    try:
        config = await game.config_for(principal.tenant_id)
        award = await game.award(
            models, config, principal.user_id, "quiz_completed",
            ref_type="listening", ref_id=attempt_id, target_skill="listening",
            difficulty=("above_ability" if correct < total * 0.5
                        else "at_ability" if correct < total * 0.85
                        else "below_ability"),
        )
        await game.advance_quest(models, config, principal.user_id,
                                 amount=float(total), skill="listening")
        before = await game.streak_state(models, principal.user_id)
        counted_before = before.last_qualifying_day
        await game.qualify_today(models, config, principal.user_id)
        after = await game.streak_state(models, principal.user_id)
        return (award.awarded_xp,
                after.last_qualifying_day != counted_before,
                after.current_streak)
    except Exception as exc:  # noqa: BLE001
        log.warning("listening reward hook failed for %s: %s", attempt_id, exc)
        return 0, False, 0
