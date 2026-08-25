"""The game, such as it is.

Duolingo's craft, inverted purpose: the season ends on drive day and the app
celebrates a student leaving. Everything here is built so that the mechanics
which would make it dishonest are absent rather than disabled.

Four properties are structural, not policy:

* **XP is computed here and nowhere else.** No endpoint accepts an amount. The
  ledger is append-only; nothing in the codebase updates or deletes a row.
* **Effort and mastery never mix.** Level comes from the ledger and always
  rises. The gap meter comes from SkillMastery and is allowed to stall. A
  student's readiness, and anything staff see, reads mastery only.
* **Freezes are earned or free, never bought.** There is no price, no
  currency, and no payment hook in this package — which is the only version
  of that promise that cannot quietly change.
* **Quizzes cannot replace speaking.** Quiz XP is capped as a share of the
  week, and when the cap bites the ledger records that it did.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import GamificationConfig
from app.models.tenant import (Badge, Cohort, CohortMember, EarnedBadge,
                               EngagementEvent, Quest, SeasonPlan, SkillMastery,
                               StreakState, XPLedger)

log = logging.getLogger(__name__)

XP_PER_LEVEL = 500

# The sub-skills a chapter can be built around, in the order a student
# generally meets them.
SKILLS = ["pronunciation", "fluency", "response_latency", "listening",
          "grammar", "vocabulary", "content_recall"]

SKILL_LABEL = {
    "pronunciation": "Pronunciation Habits",
    "fluency": "Fluency",
    "response_latency": "Response Speed",
    "listening": "Listening Accuracy",
    "grammar": "Grammar Under Pressure",
    "vocabulary": "Vocabulary",
    "content_recall": "Retell Craft",
}

QUEST_TEMPLATES = {
    "response_latency": ("Start faster", "Answer five items without stalling. "
                                         "Aim to begin inside 1.2 seconds of the tone."),
    "fluency": ("Even out your pace", "Five items at a steady rate, without a "
                                      "long pause in the middle."),
    "listening": ("Catch every word", "Five Repeat Sentence items, aiming to "
                                      "reproduce each one in full."),
    "pronunciation": ("Sharpen your delivery", "Five Read Aloud items, "
                                               "concentrating on clear word endings."),
    "grammar": ("Tighten your sentences", "Five items with attention to tense "
                                          "and agreement."),
    "vocabulary": ("Reach for the right word", "Five items using precise wording."),
    "content_recall": ("Cover the key points", "Five items where you say the "
                                               "whole idea, not part of it."),
}

STREAK_MILESTONES = [7, 14, 30, 60, 90]

BADGES = [
    # Courage first: for this population the hardest button to press is the
    # first one, and that deserves marking more than volume ever does.
    ("first_recording", "First Recording", "courage",
     "You pressed record. That is the hardest part."),
    ("first_open_response", "Spoke Freely", "courage",
     "Completed an Open Response with no script to lean on."),
    ("first_boss_mock", "Full Length", "courage",
     "Completed a full-length simulation start to finish."),
    ("chapter_cleared", "Chapter Cleared", "mastery",
     "Reached mastery in a sub-skill — demonstrated, not just practised."),
    ("latency_under_second", "Quick Off the Mark", "mastery",
     "Averaged under a second to start speaking across a whole attempt."),
    ("personal_best", "Personal Best", "mastery",
     "Beat your own best score on this simulation."),
    ("gap_halved", "Halfway There", "mastery",
     "Closed half the gap you started with."),
    ("streak_7", "Seven Days", "consistency", "A week of daily practice."),
    ("streak_14", "Two Weeks", "consistency", "Fourteen days running."),
    ("streak_30", "Thirty Days", "consistency", "A month of showing up."),
    ("streak_60", "Sixty Days", "consistency", "Two months of it."),
    ("streak_90", "Ninety Days", "consistency", "A full season."),
]

# Mastery at or above this counts as a chapter cleared. Demonstrated on
# evidence (BKT posterior in P2), never on content consumed.
CHAPTER_MASTERY = 0.8


@dataclass
class Award:
    activity: str
    awarded_xp: int
    base_xp: int
    difficulty_multiplier: float
    weakness_multiplier: float
    cap_applied: str
    target_skill: str


def level_for(total_xp: int) -> int:
    return 1 + max(0, total_xp) // XP_PER_LEVEL


def xp_into_level(total_xp: int) -> int:
    return max(0, total_xp) % XP_PER_LEVEL


async def config_for(platform: AsyncSession, tenant_id: str | None) -> GamificationConfig:
    """The economy for this institution, falling back to the global default."""
    if tenant_id:
        row = (await platform.execute(
            select(GamificationConfig).where(GamificationConfig.tenant_id == tenant_id)
        )).scalars().first()
        if row is not None:
            return row
    row = (await platform.execute(
        select(GamificationConfig).where(GamificationConfig.tenant_id.is_(None))
    )).scalars().first()
    if row is None:
        # A tenant with no economy configured still has to be able to practise.
        return GamificationConfig(
            xp_table={"attempt_completed": 120, "drill_completed": 60,
                      "quiz_completed": 25, "quest_completed": 80,
                      "streak_milestone": 150},
            difficulty_multipliers={"below_ability": 0.6, "at_ability": 1.0,
                                    "above_ability": 1.4},
            weakness_multiplier=1.5, free_freezes_per_month=2,
            quiz_xp_cap_percent=40, leagues_enabled=True,
            max_engagement_notifications_per_day=1,
        )
    return row


async def total_xp(tenant: AsyncSession, user_id: str) -> int:
    return int((await tenant.execute(
        select(func.coalesce(func.sum(XPLedger.awarded_xp), 0))
        .where(XPLedger.user_id == user_id)
    )).scalar_one())


async def weakest_skills(tenant: AsyncSession, user_id: str, count: int = 3) -> list[str]:
    rows = list((await tenant.execute(
        select(SkillMastery).where(SkillMastery.user_id == user_id)
        .order_by(SkillMastery.mastery)
    )).scalars().all())
    return [r.skill for r in rows[:count]]


# --------------------------------------------------------------------------
# XP
# --------------------------------------------------------------------------

async def _week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


async def _apply_quiz_cap(tenant: AsyncSession, config: GamificationConfig,
                          user_id: str, amount: int) -> tuple[int, str]:
    """QUIZ-06: quizzes cannot stand in for speaking practice.

    The rule, stated the way a student can be told it: **the first quiz each
    week always counts in full; after that, quiz XP is capped at a share of
    the week's total.**

    The floor exists because the share rule alone collapses. Requiring
    ``quiz <= 40% of (quiz + speaking)`` means that with no speaking XP the
    allowance is exactly zero — a student's first ever quiz would earn
    nothing, which reads as broken rather than principled. One quiz at full
    value per week costs the requirement nothing and keeps the product
    honest-looking as well as honest.

    Beyond the floor the arithmetic is the requirement, solved for the award:
    ``quiz + q <= c(speaking + quiz + q)``  ->  ``q <= c/(1-c) * speaking - quiz``.
    """
    cap_percent = int(config.quiz_xp_cap_percent or 100)
    if cap_percent >= 100:
        return amount, ""

    week_start = await _week_start()
    rows = list((await tenant.execute(
        select(XPLedger.activity, XPLedger.awarded_xp)
        .where(XPLedger.user_id == user_id,
               XPLedger.at >= datetime.combine(week_start, datetime.min.time(),
                                               tzinfo=timezone.utc))
    )).all())
    quiz_total = sum(x for a, x in rows if a == "quiz_completed")
    speaking_total = sum(x for a, x in rows if a != "quiz_completed")

    floor = int(config.xp_table.get("quiz_completed", 0))
    share = cap_percent / 100.0
    from_speaking = int(share / (1 - share) * speaking_total)

    allowance = max(floor, from_speaking) - quiz_total
    if amount <= max(0, allowance):
        return amount, ""

    return max(0, allowance), f"quiz_weekly_{cap_percent}pct"


async def award(tenant: AsyncSession, config: GamificationConfig, user_id: str,
                activity: str, *, ref_type: str = "", ref_id: str = "",
                target_skill: str = "", difficulty: str = "at_ability",
                weakness: bool | None = None) -> Award:
    """Write one XP row. The only way XP is ever created.

    The weakness multiplier is resolved from the student's own mastery record
    rather than trusted from the caller — "this drill targeted a weakness" is
    a claim the server checks (GAM-02).
    """
    base = int(config.xp_table.get(activity, 0))
    difficulty_multiplier = float(config.difficulty_multipliers.get(difficulty, 1.0))

    if weakness is None and target_skill:
        weakness = target_skill in await weakest_skills(tenant, user_id)
    weakness_multiplier = float(config.weakness_multiplier) if weakness else 1.0

    amount = int(round(base * difficulty_multiplier * weakness_multiplier))
    cap_applied = ""

    if activity == "quiz_completed" and amount > 0:
        amount, cap_applied = await _apply_quiz_cap(tenant, config, user_id, amount)

    tenant.add(XPLedger(
        user_id=user_id, activity=activity, ref_type=ref_type, ref_id=ref_id,
        base_xp=base, difficulty_multiplier=difficulty_multiplier,
        weakness_multiplier=weakness_multiplier, awarded_xp=amount,
        cap_applied=cap_applied, target_skill=target_skill,
    ))
    tenant.add(EngagementEvent(
        user_id=user_id, event=activity,
        payload={"xp": amount, "skill": target_skill, "cap": cap_applied},
        weakness_targeted=bool(weakness),
    ))
    return Award(activity=activity, awarded_xp=amount, base_xp=base,
                 difficulty_multiplier=difficulty_multiplier,
                 weakness_multiplier=weakness_multiplier,
                 cap_applied=cap_applied, target_skill=target_skill)


# --------------------------------------------------------------------------
# Streaks
# --------------------------------------------------------------------------

async def streak_state(tenant: AsyncSession, user_id: str) -> StreakState:
    row = (await tenant.execute(
        select(StreakState).where(StreakState.user_id == user_id)
    )).scalars().first()
    if row is None:
        row = StreakState(user_id=user_id)
        tenant.add(row)
        await tenant.flush()
    return row


async def touch_streak(tenant: AsyncSession, config: GamificationConfig,
                       user_id: str, today: date | None = None) -> tuple[StreakState, list[int]]:
    """Advance the streak for a qualifying day, applying freezes to gaps.

    A day counts when the daily quest is completed — not when the app is
    opened (GAM-04). Freezes are spent automatically on missed days so a
    student who was ill comes back to their streak intact and a nudge, not a
    guilt screen.
    """
    today = today or date.today()
    state = await streak_state(tenant, user_id)
    milestones: list[int] = []

    if state.last_qualifying_day == today:
        return state, milestones

    if state.last_qualifying_day is None:
        state.current_streak = 1
    else:
        gap = (today - state.last_qualifying_day).days
        if gap == 1:
            state.current_streak += 1
        elif gap > 1:
            missed = gap - 1
            usable = min(missed, state.freezes_available)
            if usable == missed:
                # Every missed day covered — the streak survives intact.
                state.freezes_available -= usable
                state.freezes_used_this_month += usable
                state.freeze_history = (state.freeze_history or []) + [
                    {"applied_on": today.isoformat(), "days": usable}]
                state.current_streak += 1
            else:
                state.current_streak = 1

    state.last_qualifying_day = today
    state.best_streak = max(state.best_streak, state.current_streak)
    state.updated_at = datetime.now(timezone.utc)

    if state.current_streak in STREAK_MILESTONES:
        milestones.append(state.current_streak)
        # Milestones pay in freezes as well as XP: the reward for consistency
        # is protection for the day life gets in the way.
        state.freezes_available += 1

    return state, milestones


async def qualify_today(tenant: AsyncSession, config: GamificationConfig,
                        user_id: str, today: date | None = None) -> list[int]:
    """Count today if today's quest is done. Idempotent, safe to call anywhere.

    ``touch_streak`` used to be reachable only from the one call that flipped
    the quest to completed, which made the streak a side effect of a single
    transition rather than a function of state. If that one call was lost --
    a rolled-back request, a quest completed by an import or a seeder, two
    tabs racing -- the day could never qualify again, because ``advance_quest``
    early-returns on an already-completed quest. The visible symptom is a
    completed quest sitting above a zero streak, which reads as decoration and
    is what made the whole loop feel fake.

    Deriving it instead means the invariant holds however the quest got
    finished: a completed day is a counted day.
    """
    quest = await daily_quest(tenant, user_id, today)
    if not quest.completed:
        return []

    _state, milestones = await touch_streak(tenant, config, user_id, today)
    for milestone in milestones:
        await award(tenant, config, user_id, "streak_milestone",
                    ref_type="streak", ref_id=str(milestone))
        await grant(tenant, user_id, f"streak_{milestone}")
    return milestones


async def grant_monthly_freezes(tenant: AsyncSession, config: GamificationConfig,
                                user_id: str) -> None:
    """Top the free freezes back up at the start of a month."""
    state = await streak_state(tenant, user_id)
    free = int(config.free_freezes_per_month or 0)
    if state.freezes_used_this_month and date.today().day == 1:
        state.freezes_used_this_month = 0
        state.freezes_available = max(state.freezes_available, free)


# --------------------------------------------------------------------------
# Quests
# --------------------------------------------------------------------------

async def daily_quest(tenant: AsyncSession, user_id: str,
                      for_date: date | None = None) -> Quest:
    """Today's quest, generated from the student's own weakest sub-skill.

    Always targets a real diagnosed gap. Before there is a diagnosis it asks
    for the baseline, because inventing a weakness to have something to show
    would be the first lie in a product whose whole pitch is honesty.
    """
    for_date = for_date or date.today()

    existing = (await tenant.execute(
        select(Quest).where(Quest.user_id == user_id, Quest.kind == "daily",
                            Quest.for_date == for_date)
    )).scalars().first()
    if existing is not None:
        return existing

    weakest = await weakest_skills(tenant, user_id, 1)
    if weakest:
        skill = weakest[0]
        title, description = QUEST_TEMPLATES.get(
            skill, ("Practise " + skill.replace("_", " "), "Five targeted items."))
    else:
        skill = ""
        title = "Take your baseline"
        description = ("One short diagnostic sets your starting point. Everything "
                       "after it is measured against today.")

    quest = Quest(
        user_id=user_id, kind="daily", for_date=for_date, title=title,
        description=description, target_skill=skill,
        objective={"items": 5, "skill": skill} if skill else {"baseline": True},
        progress=0.0, target=5.0 if skill else 1.0, bonus_xp=80,
    )
    tenant.add(quest)
    await tenant.flush()
    return quest


async def advance_quest(tenant: AsyncSession, config: GamificationConfig,
                        user_id: str, *, amount: float = 1.0,
                        skill: str = "", satisfies: bool = False) -> tuple[Quest, bool]:
    """Move today's quest along. Returns the quest and whether it just completed.

    ``satisfies`` is for a full simulation, which always completes the day's
    quest whatever it asked for (GAM-01) — a student who did the harder thing
    should not be told they missed the easier one.
    """
    quest = await daily_quest(tenant, user_id)
    if quest.completed:
        return quest, False

    if satisfies:
        quest.progress = quest.target
    elif not quest.target_skill or quest.target_skill == skill:
        quest.progress = min(quest.target, quest.progress + amount)

    just_completed = quest.progress >= quest.target
    if just_completed:
        quest.completed = True
        quest.completed_at = datetime.now(timezone.utc)
        await award(tenant, config, user_id, "quest_completed",
                    ref_type="quest", ref_id=quest.id,
                    target_skill=quest.target_skill, weakness=True)
    return quest, just_completed


# --------------------------------------------------------------------------
# Badges
# --------------------------------------------------------------------------

async def ensure_badges(tenant: AsyncSession) -> dict[str, Badge]:
    existing = {b.code: b for b in (await tenant.execute(select(Badge))).scalars().all()}
    for code, name, category, description in BADGES:
        if code not in existing:
            badge = Badge(code=code, name=name, category=category,
                          description=description, criteria={"code": code},
                          criteria_version=1)
            tenant.add(badge)
            existing[code] = badge
    await tenant.flush()
    return existing


async def grant(tenant: AsyncSession, user_id: str, code: str) -> bool:
    """Award a badge once. Returns True if this was the first time."""
    badges = await ensure_badges(tenant)
    badge = badges.get(code)
    if badge is None:
        return False

    already = (await tenant.execute(
        select(EarnedBadge).where(EarnedBadge.user_id == user_id,
                                  EarnedBadge.badge_id == badge.id)
    )).scalars().first()
    if already is not None:
        return False

    tenant.add(EarnedBadge(user_id=user_id, badge_id=badge.id,
                           criteria_version=badge.criteria_version))
    return True


# --------------------------------------------------------------------------
# Season
# --------------------------------------------------------------------------

ROLLING_SEASON_DAYS = 90


async def season_for(tenant: AsyncSession, user_id: str) -> SeasonPlan:
    """The plan between today and the real drive date (GAM-07).

    Derived from the cohort's actual placement window. With no date set it is
    a rolling ninety days — never an invented deadline, because the only
    countdown this product is allowed to show is a true one.
    """
    cohort = (await tenant.execute(
        select(Cohort).join(CohortMember, CohortMember.cohort_id == Cohort.id)
        .where(CohortMember.user_id == user_id, Cohort.active.is_(True))
    )).scalars().first()

    drive = cohort.drive_start if cohort else None
    starts = date.today()
    ends = drive.date() if drive else starts + timedelta(days=ROLLING_SEASON_DAYS)
    if ends <= starts:
        ends = starts + timedelta(days=7)

    existing = (await tenant.execute(
        select(SeasonPlan).where(SeasonPlan.user_id == user_id,
                                 SeasonPlan.active.is_(True))
    )).scalars().first()

    weeks = max(1, (ends - starts).days // 7)
    focus = await weakest_skills(tenant, user_id, 4) or SKILLS[:4]
    themes = [
        {"week": i + 1,
         "theme": SKILL_LABEL.get(focus[i % len(focus)], focus[i % len(focus)]),
         "target_skill": focus[i % len(focus)],
         "minutes_target": 25 * 7}
        for i in range(min(weeks, 16))
    ]

    if existing is None:
        plan = SeasonPlan(
            user_id=user_id, cohort_id=cohort.id if cohort else None,
            drive_date=drive, starts_on=starts, ends_on=ends,
            weekly_themes=themes, daily_minutes_target=25,
        )
        tenant.add(plan)
        await tenant.flush()
        return plan

    # Re-plan when the institution moves the date (TEN-13 AC).
    if existing.ends_on != ends or existing.drive_date != drive:
        existing.replans = (existing.replans or []) + [{
            "at": datetime.now(timezone.utc).isoformat(),
            "from": existing.ends_on.isoformat(), "to": ends.isoformat(),
        }]
        existing.drive_date = drive
        existing.ends_on = ends
        existing.weekly_themes = themes
    return existing


# --------------------------------------------------------------------------
# The hook the rest of the app calls
# --------------------------------------------------------------------------

async def on_attempt_scored(tenant: AsyncSession, config: GamificationConfig,
                            user_id: str, attempt_id: str, *,
                            dimensions: dict[str, float],
                            is_full_simulation: bool,
                            previous_best: float | None,
                            overall: float | None,
                            task_types: set[str]) -> dict:
    """Everything the game does when an attempt finishes.

    Called after scoring, never before: the reward is for what was measured,
    not for having pressed a button (ENG-22 — the game rewards getting
    better, not doing more).
    """
    weakest = await weakest_skills(tenant, user_id)
    target = weakest[0] if weakest else ""

    attempt_award = await award(
        tenant, config, user_id, "attempt_completed",
        ref_type="attempt", ref_id=attempt_id, target_skill=target,
        difficulty="at_ability", weakness=bool(target),
    )

    quest, quest_completed = await advance_quest(
        tenant, config, user_id, satisfies=is_full_simulation, skill=target)

    # Unconditional: the quest may already have been completed earlier today by
    # a quiz or a drill, and the day still has to be counted exactly once.
    milestones = await qualify_today(tenant, config, user_id)

    earned: list[str] = []

    attempts_before = int((await tenant.execute(
        select(func.count()).select_from(XPLedger)
        .where(XPLedger.user_id == user_id,
               XPLedger.activity == "attempt_completed")
    )).scalar_one())
    if attempts_before <= 1 and await grant(tenant, user_id, "first_recording"):
        earned.append("first_recording")

    if "open_response" in task_types and await grant(tenant, user_id, "first_open_response"):
        earned.append("first_open_response")
    if is_full_simulation and await grant(tenant, user_id, "first_boss_mock"):
        earned.append("first_boss_mock")

    if (overall is not None and previous_best is not None and overall > previous_best
            and await grant(tenant, user_id, "personal_best")):
        earned.append("personal_best")

    latency = dimensions.get("latency")
    if latency is not None and latency >= 75 and await grant(tenant, user_id,
                                                             "latency_under_second"):
        earned.append("latency_under_second")

    # A chapter clears on demonstrated mastery, never on content consumed.
    mastered = list((await tenant.execute(
        select(SkillMastery).where(SkillMastery.user_id == user_id,
                                   SkillMastery.mastery >= CHAPTER_MASTERY)
    )).scalars().all())
    if mastered and await grant(tenant, user_id, "chapter_cleared"):
        earned.append("chapter_cleared")

    await season_for(tenant, user_id)
    await tenant.commit()

    return {
        "xp_awarded": attempt_award.awarded_xp,
        "quest_completed": quest_completed,
        "quest_title": quest.title,
        "streak_milestones": milestones,
        "badges_earned": earned,
    }
