"""Reading practice: read a passage, then answer without it in front of you.

Two measures, kept apart on purpose.

**Comprehension** is the questions. **Rate** is how long the passage was on
screen, in words per minute. Blending them into one number would hide the
thing a student most needs to know: fast with poor comprehension is skimming,
slow with good comprehension is a different problem with a different fix, and
a single figure makes those two look identical.

The passage is withdrawn before the questions appear. Leaving it up would
make this a search task -- find the sentence containing the keyword -- which
is a real skill but not the one being claimed, and it would make the rate
measure meaningless because nobody would need to finish reading.
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import Principal, TenantModels, require_roles
from app.engine.pipeline import SCALE_MAX, SCALE_MIN, band_label
from app.gamification import engine as game
from app.schemas import (ReadingPassageOut, ReadingQuestionOut, ReadingResult,
                         ReadingResultItem, ReadingStart, ReadingSubmission)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/student/reading", tags=["reading"],
                   dependencies=[Depends(require_roles("student"))])

# Rate bands for the comment beside the number. Adult reading of workplace
# prose sits around 200-250 wpm; below 120 is slow enough to cost a candidate
# real time in a paper, and above 400 with good comprehension is genuinely
# fast rather than skimming -- which is why the comment always pairs the rate
# with the score rather than judging speed alone.
SLOW_WPM = 120
FAST_WPM = 400
# Below this, the passage cannot have been read. Recorded, not scored.
IMPLAUSIBLE_WPM = 700


def _score(correct: int, total: int) -> float:
    if total <= 0:
        return SCALE_MIN
    return round(SCALE_MIN + (SCALE_MAX - SCALE_MIN) * (correct / total), 1)


def _rate_note(wpm: int | None, correct: int, total: int) -> str:
    """What the two numbers mean together. Never speed on its own."""
    if wpm is None:
        return ("Reading rate was not measured for this attempt.")
    share = correct / total if total else 0.0

    if wpm >= IMPLAUSIBLE_WPM:
        return (f"{wpm} words per minute is faster than the passage can be "
                f"read, so the rate is recorded but not treated as a "
                f"measurement. Your comprehension score stands on its own.")
    if wpm > FAST_WPM and share < 0.6:
        return (f"{wpm} words per minute with {correct} of {total} correct is "
                f"skimming. The speed is real; it is costing you the content.")
    if wpm > FAST_WPM:
        return (f"{wpm} words per minute with {correct} of {total} correct is "
                f"genuinely fast reading, not skimming.")
    if wpm < SLOW_WPM and share >= 0.8:
        return (f"{wpm} words per minute is slow, but you took it in â€” "
                f"{correct} of {total}. In a timed paper the speed is what "
                f"would cost you, not the understanding.")
    if wpm < SLOW_WPM:
        return (f"{wpm} words per minute is slow for workplace prose, and the "
                f"comprehension has not been bought by the extra time.")
    return (f"{wpm} words per minute is a normal working pace for this kind of "
            f"text.")

@router.get("/random", response_model=ReadingStart)
async def random_passage(principal: Principal, models: TenantModels,
                          company: str = "") -> ReadingStart:
    """Get a random passage for practice. Guarantees exactly 10 questions.

    Finds a passage, ensures it has at least 10 linked quiz_items (generates
    more if needed), then starts the attempt.
    """
    TARGET_QUESTIONS = 10

    query = models.ReadingPassage.find(models.ReadingPassage.status == "published")
    if company:
        all_rows = []
        for p in await query.to_list():
            if p.company and p.company.lower() == company.lower():
                all_rows.append(p)
    else:
        all_rows = await query.to_list()
    if not all_rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No reading passages available")

    # Exclude passages already attempted by this user
    attempted = await models.ReadingAttempt.find(
        models.ReadingAttempt.user_id == principal.user_id
    ).all()
    attempted_ids = {a.passage_id for a in attempted}
    if attempted_ids:
        all_rows = [p for p in all_rows if p.id not in attempted_ids]

    # Find which passages already have enough questions
    coll = models.QuizItem.get_motor_collection()
    q_counts_raw = await coll.aggregate([
        {"$match": {"category": "reading_comprehension", "status": "published"}},
        {"$group": {"_id": "$passage_id", "count": {"$sum": 1}}},
    ]).to_list(None)
    q_counts = {doc["_id"]: doc["count"] for doc in q_counts_raw}

    # Prefer passages that already have >=10 questions
    ready = [p for p in all_rows if q_counts.get(p.id, 0) >= TARGET_QUESTIONS]
    # Passages with some but not enough questions
    partial = [p for p in all_rows if 0 < q_counts.get(p.id, 0) < TARGET_QUESTIONS]
    # Passages with no questions at all
    empty = [p for p in all_rows if q_counts.get(p.id, 0) == 0]

    if ready:
        passage = random.choice(ready)
    elif partial:
        passage = random.choice(partial)
        # Top up to 10
        existing = q_counts.get(passage.id, 0)
        await _auto_generate_questions(models, passage, count=TARGET_QUESTIONS - existing)
    elif empty:
        passage = random.choice(empty)
        await _auto_generate_questions(models, passage, count=TARGET_QUESTIONS)
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No reading passages available")

    total = int(await models.QuizItem.find(
        models.QuizItem.passage_id == passage.id,
        models.QuizItem.category == "reading_comprehension",
        models.QuizItem.status == "published"
    ).count())
    if total == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Could not prepare questions for this passage")

    attempt = models.ReadingAttempt(user_id=principal.user_id,
                                    passage_id=passage.id, total=total)
    await attempt.create()

    return ReadingStart(
        attempt_id=attempt.id, passage_id=passage.id, title=passage.title,
        kind=passage.kind, body=passage.body, word_count=passage.word_count,
        question_count=total,
    )


async def _auto_generate_questions(models, passage, count: int = 10) -> None:
    """Generate comprehension questions for a reading passage.

    Uses simple template-based generation (no external API needed).
    Creates quiz_items with category 'reading_comprehension' linked to the passage.
    """
    body = passage.body or ""
    title = passage.title or "the passage"
    sentences = [s.strip() for s in body.replace('\n', ' ').split('.') if len(s.strip()) > 20]
    if not sentences:
        sentences = [title]
    # Get 3rd sentence or last for variety
    third = sentences[2] if len(sentences) > 2 else sentences[-1]
    last = sentences[-1] if len(sentences) > 1 else sentences[0]

    templates = [
        {
            "stem": f"What is the main topic of {title}?",
            "options": [
                f"The passage discusses important aspects of {title.lower()}.",
                "The passage is about an unrelated subject.",
                "The passage discusses only historical dates.",
                "The passage gives no information about the subject."
            ],
            "correct_index": 0,
        },
        {
            "stem": f"Which idea is directly supported by the passage?",
            "options": [
                sentences[0][:120] + ('.' if not sentences[0].endswith('.') else ''),
                "The passage rejects the subject completely.",
                "The passage says the subject has no practical value.",
                "The passage provides no explanation."
            ],
            "correct_index": 0,
        },
        {
            "stem": "Which statement is best supported by the passage?",
            "options": [
                f"The passage explains important points about {title.lower()}.",
                "The passage says no consideration is necessary.",
                "The passage gives no practical consideration.",
                "The topic has no limitations or conditions."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What can be inferred from the passage?",
            "options": [
                f"The passage provides useful information about {title.lower()}.",
                "The passage contradicts itself.",
                "The passage has no clear point.",
                "The passage is purely fictional."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What is the best summary of the passage?",
            "options": [
                body[:200] + ('...' if len(body) > 200 else ''),
                "It says the topic has no value at all.",
                "It focuses on a completely different subject.",
                "It gives no practical information."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What is the author's main argument in this passage?",
            "options": [
                f"The author presents a case for the importance of {title.lower()}.",
                "The author argues against the topic entirely.",
                "The author provides no clear argument.",
                "The author is purely describing historical events."
            ],
            "correct_index": 0,
        },
        {
            "stem": "Which detail from the passage is most important?",
            "options": [
                third[:120] + ('.' if not third.endswith('.') else ''),
                "The passage mentions no important details.",
                "All details mentioned are trivial.",
                "The passage focuses only on opinions, not facts."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What conclusion does the passage lead to?",
            "options": [
                last[:120] + ('.' if not last.endswith('.') else ''),
                "The passage reaches no conclusion.",
                "The conclusion contradicts the passage.",
                "The conclusion is unrelated to the topic."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What type of text is this passage?",
            "options": [
                f"A workplace text about {title.lower()}.",
                "A fictional short story.",
                "A poem.",
                "A legal document."
            ],
            "correct_index": 0,
        },
        {
            "stem": "What is the tone of this passage?",
            "options": [
                "Informative and professional.",
                "Angry and emotional.",
                "Humorous and satirical.",
                "Confused and contradictory."
            ],
            "correct_index": 0,
        },
    ]

    for tmpl in templates[:count]:
        correct_text = tmpl["options"][tmpl["correct_index"]]
        shuffled = tmpl["options"][:]
        random.shuffle(shuffled)
        tmpl["options"] = shuffled
        tmpl["correct_index"] = shuffled.index(correct_text)

        item = models.QuizItem(
            stem=tmpl["stem"],
            options=tmpl["options"],
            correct_index=tmpl["correct_index"],
            explanation="Based on the passage content.",
            category="reading_comprehension",
            passage_id=passage.id,
            company=passage.company or "",
            status="published",
            difficulty=0.5,
            seconds_allowed=30,
        )
        await item.create()


@router.get("/passages", response_model=list[ReadingPassageOut])
async def passages(principal: Principal,
                   models: TenantModels,
                   company: str = "",
                   limit: int = 10) -> list[ReadingPassageOut]:
    # Practice shows general passages by default.
    # "General" and empty company both count as general (non-company) content.
    # Company-specific passages are only shown when company param is provided.
    query = models.ReadingPassage.find(models.ReadingPassage.status == "published")
    if company:
        query = query.find(models.ReadingPassage.company == company)
    all_rows = await query.to_list()
    random.shuffle(all_rows)
    rows = all_rows[:max(1, min(limit, 50))]

    coll = models.QuizItem.get_motor_collection()
    counts = {doc["_id"]: doc["count"] for doc in await coll.aggregate([
        {"$match": {"category": "reading_comprehension", "status": "published"}},
        {"$group": {"_id": "$passage_id", "count": {"$sum": 1}}},
    ]).to_list(None)}

    coll = models.ReadingAttempt.get_motor_collection()
    best = {doc["_id"]: doc["max"] for doc in await coll.aggregate([
        {"$match": {"user_id": principal.user_id, "score": {"$ne": None}}},
        {"$group": {"_id": "$passage_id", "max": {"$max": "$score"}}},
    ]).to_list(None)}

    return [
        ReadingPassageOut(
            id=p.id, title=p.title, kind=p.kind, word_count=p.word_count,
            question_count=int(counts.get(p.id, 0)),
            best_score=best.get(p.id),
            # The body is not here. It is the thing being timed.
        )
        for p in rows
    ]


@router.post("/passages/{passage_id}/start", response_model=ReadingStart)
async def start(passage_id: str, principal: Principal,
                models: TenantModels) -> ReadingStart:
    """Open an attempt and release the passage. The clock starts on the client.

    Timed client-side because the measurement is "how long was this on your
    screen", and a server timestamp would include network latency and the
    student's own delay in pressing the button. The trade is that the number
    is reported by the client and could be faked; it is a practice measure,
    not an invigilated one, and an implausible rate is flagged rather than
    trusted.
    """
    passage = await models.ReadingPassage.get(passage_id)
    if passage is None or passage.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such passage")

    total = int(await models.QuizItem.find(
        models.QuizItem.passage_id == passage_id,
        models.QuizItem.category == "reading_comprehension",
        models.QuizItem.status == "published"
    ).count())
    if total == 0:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "That passage has no questions written for it yet")

    attempt = models.ReadingAttempt(user_id=principal.user_id,
                                    passage_id=passage_id, total=total)
    await attempt.create()

    return ReadingStart(
        attempt_id=attempt.id, passage_id=passage.id, title=passage.title,
        kind=passage.kind, body=passage.body, word_count=passage.word_count,
        question_count=total,
    )


@router.get("/attempts/{attempt_id}/questions",
            response_model=list[ReadingQuestionOut])
async def questions(attempt_id: str, principal: Principal,
                    models: TenantModels) -> list[ReadingQuestionOut]:
    attempt = await models.ReadingAttempt.get(attempt_id)
    if attempt is None or attempt.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such attempt")
    if attempt.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That attempt is finished")

    rows = await models.QuizItem.find(
        models.QuizItem.passage_id == attempt.passage_id,
        models.QuizItem.category == "reading_comprehension",
        models.QuizItem.status == "published"
    ).sort(models.QuizItem.id).to_list()
    random.shuffle(rows)
    return [ReadingQuestionOut(id=q.id, stem=q.stem, options=list(q.options))
            for q in rows]


@router.post("/attempts/{attempt_id}/submit", response_model=ReadingResult)
async def submit(attempt_id: str, body: ReadingSubmission,
                 principal: Principal, models: TenantModels) -> ReadingResult:
    attempt = await models.ReadingAttempt.get(attempt_id)
    if attempt is None or attempt.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such attempt")
    if attempt.completed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already submitted")

    passage = await models.ReadingPassage.get(attempt.passage_id)
    rows = {q.id: q for q in await models.QuizItem.find(
        models.QuizItem.passage_id == attempt.passage_id,
        models.QuizItem.category == "reading_comprehension",
        models.QuizItem.status == "published").to_list()}

    chosen = {a.item_id: a.selected_index for a in body.answers}
    results: list[ReadingResultItem] = []
    correct = 0
    for item_id, item in rows.items():
        picked = chosen.get(item_id)
        is_right = picked == item.correct_index
        correct += int(is_right)
        results.append(ReadingResultItem(
            item_id=item_id, stem=item.stem, options=list(item.options),
            selected_index=picked, correct_index=item.correct_index,
            is_correct=is_right, explanation=item.explanation,
        ))

    total = len(rows)
    score = _score(correct, total)

    read_ms = max(0, int(body.read_ms or 0))
    words = passage.word_count if passage else 0
    wpm: int | None = None
    if read_ms > 0 and words > 0:
        wpm = int(round(words / (read_ms / 60_000)))

    attempt.read_ms = read_ms
    attempt.words_per_minute = wpm
    attempt.correct = correct
    attempt.total = total
    attempt.score = score
    attempt.completed_at = datetime.now(timezone.utc)

    await _update_reading_mastery(models, principal.user_id, score)
    await attempt.save()

    xp, day_counted, streak_now = await _reward(
        models, principal, attempt.id, correct, total)

    return ReadingResult(
        attempt_id=attempt.id, title=passage.title if passage else "",
        correct=correct, total=total, score=score, band=band_label(score),
        words_per_minute=wpm, word_count=words,
        rate_note=_rate_note(wpm, correct, total),
        # Released now so a student can check an answer against the text.
        body=passage.body if passage else "",
        items=results, xp_awarded=xp,
        day_counted_now=day_counted, streak_current=streak_now,
    )


async def _update_reading_mastery(models, user_id: str, score: float) -> None:
    """Reading comprehension feeds the `vocabulary` skill for now.

    There is no `reading` skill in the mastery vocabulary, and adding one is a
    psychometrics change rather than a content one: the BKT parameters are
    fitted per skill and there is nothing to fit this against yet. Vocabulary
    is the closest existing home and the skills card says where the number
    came from, which is the same disclosure rule Listening follows.
    """
    row = await models.SkillMastery.find_one(
        models.SkillMastery.user_id == user_id,
        models.SkillMastery.skill == "vocabulary")

    observed = max(0.0, min(1.0, (score - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)))
    if row is None:
        await models.SkillMastery(user_id=user_id, skill="vocabulary",
                                  mastery=round(observed, 4),
                                  baseline=round(observed, 4),
                                  confidence=0.3, observations=1,
                                  last_change=0.0).create()
        return
    prior = float(row.mastery)
    posterior = 0.8 * prior + 0.2 * observed
    row.last_change = round(posterior - prior, 4)
    row.mastery = round(posterior, 4)
    row.observations = int(row.observations or 0) + 1
    row.confidence = min(0.9, float(row.confidence or 0.3) + 0.04)
    await row.save()


async def _reward(models, principal, attempt_id: str,
                  correct: int, total: int) -> tuple[int, bool, int]:
    try:
        config = await game.config_for(principal.tenant_id)
        award = await game.award(
            models, config, principal.user_id, "quiz_completed",
            ref_type="reading", ref_id=attempt_id, target_skill="vocabulary",
            difficulty=("above_ability" if correct < total * 0.5
                        else "at_ability" if correct < total * 0.85
                        else "below_ability"),
        )
        await game.advance_quest(models, config, principal.user_id,
                                 amount=float(total), skill="vocabulary")
        before = await game.streak_state(models, principal.user_id)
        counted_before = before.last_qualifying_day
        await game.qualify_today(models, config, principal.user_id)
        after = await game.streak_state(models, principal.user_id)
        return (award.awarded_xp,
                after.last_qualifying_day != counted_before,
                after.current_streak)
    except Exception as exc:  # noqa: BLE001
        log.warning("reading reward hook failed for %s: %s", attempt_id, exc)
        return 0, False, 0
