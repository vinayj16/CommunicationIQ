"""The durable narration job: create, claim, generate, validate, persist, retry.

The row IS the job (app.models.tenant.AttemptNarration). This module never
touches a ScoreRecord and never runs inside a scoring transaction — it reads a
finished AttemptResult and writes only its own row.

Concurrency safety is a database lease, not a lock in memory: claiming a job
sets it to `processing` with a `lease_until`, under SELECT ... FOR UPDATE SKIP
LOCKED, so two workers (or a restart racing the kick) can never both own the
same row, and a job whose worker died is reclaimable once its lease expires.
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Attempt, AttemptNarration, ConsentRecord, User
from app.narration import evidence as evidence_mod
from app.narration import validate as validate_mod
from app.narration.contract import NarratorError, RETRYABLE
from app.narration.providers import get_narrator

log = logging.getLogger("narration")

CLAIMABLE = ("pending", "retry_pending")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def ai_consent_granted(session: AsyncSession, user_id: str) -> bool:
    """The student's latest ai_explanation decision. Absent = not granted."""
    row = (await session.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id,
               ConsentRecord.scope == "ai_explanation")
        .order_by(ConsentRecord.at.desc())
    )).scalars().first()
    return bool(row and row.granted)


async def ensure_row(session: AsyncSession, attempt: Attempt) -> AttemptNarration | None:
    """Create the pending job for a scored attempt, once.

    Idempotent by the unique attempt_id: a second call returns the existing
    row. Returns None when narration is disabled or the student has not
    consented — in both cases the report simply renders without a card, and no
    job is created, so nothing later claims work that must not run.
    """
    if not settings.narration_enabled:
        return None
    if attempt.status != "scored":
        return None

    existing = (await session.execute(
        select(AttemptNarration).where(AttemptNarration.attempt_id == attempt.id)
    )).scalars().first()
    if existing is not None:
        return existing

    user = await session.get(User, attempt.user_id)
    if user is None or not await ai_consent_granted(session, user.id):
        return None

    row = AttemptNarration(
        attempt_id=attempt.id, status="pending", attempt_count=0,
        prompt_version=settings.narration_prompt_version,
        model_version=settings.narration_model,
        provider_key=settings.narration_provider,
    )
    session.add(row)
    await session.commit()
    return row


async def claim_due(session: AsyncSession, *, batch: int) -> list[str]:
    """Atomically claim up to `batch` due jobs; return their ids.

    Due = pending, or retry_pending past next_retry_at, or processing past a
    dead lease. The row is flipped to processing with a fresh lease and its
    attempt_count incremented, inside one transaction, under SKIP LOCKED.
    """
    now = _now()
    stmt = (
        select(AttemptNarration)
        .where(
            or_(
                AttemptNarration.status == "pending",
                (AttemptNarration.status == "retry_pending")
                & (AttemptNarration.next_retry_at <= now),
                (AttemptNarration.status == "processing")
                & (AttemptNarration.lease_until <= now),
            )
        )
        .order_by(AttemptNarration.created_at)
        .limit(batch)
        .with_for_update(skip_locked=True)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    lease = now + timedelta(seconds=settings.narration_lease_seconds)
    claimed: list[str] = []
    for row in rows:
        row.status = "processing"
        row.lease_until = lease
        row.next_retry_at = None
        row.attempt_count += 1
        claimed.append(row.id)
    await session.commit()
    return claimed


async def claim_one(session: AsyncSession, narration_id: str) -> bool:
    """Atomically claim one specific job by id. Returns True if this call won it.

    The fast path (kick after an attempt is scored) targets exactly one row.
    SELECT ... FOR UPDATE SKIP LOCKED means that if the sweeper already holds
    it, this returns False rather than blocking or double-running.
    """
    now = _now()
    row = (await session.execute(
        select(AttemptNarration)
        .where(AttemptNarration.id == narration_id,
               or_(AttemptNarration.status == "pending",
                   (AttemptNarration.status == "retry_pending")
                   & (AttemptNarration.next_retry_at <= now),
                   (AttemptNarration.status == "processing")
                   & (AttemptNarration.lease_until <= now)))
        .with_for_update(skip_locked=True)
    )).scalars().first()
    if row is None:
        return False
    row.status = "processing"
    row.lease_until = now + timedelta(seconds=settings.narration_lease_seconds)
    row.next_retry_at = None
    row.attempt_count += 1
    await session.commit()
    return True


def _backoff_seconds(attempt_count: int) -> float:
    """Exponential backoff with full jitter, capped."""
    base = settings.narration_backoff_base_s * (2 ** max(0, attempt_count - 1))
    capped = min(base, settings.narration_backoff_cap_s)
    return random.uniform(capped / 2, capped)


async def generate_one(session: AsyncSession, narration_id: str) -> str:
    """Generate one claimed job to a terminal-or-retry state. Returns status.

    Assumes the row is already `processing` (claimed by this worker). On
    success → ready. On a transient failure with attempts left → retry_pending
    with backoff. Otherwise → failed. Never raises: a job that cannot be
    generated is a recorded state, not an exception that kills the worker.
    """
    row = await session.get(AttemptNarration, narration_id)
    if row is None or row.status != "processing":
        return "skipped"

    try:
        attempt = await session.get(Attempt, row.attempt_id)
        if attempt is None:
            raise NarratorError("no_evidence", "attempt vanished")

        # Import here to avoid an import cycle with the attempts router.
        from app.routers.attempts import _result

        result = await _result(session, attempt)
        user = await session.get(User, attempt.user_id)
        l1 = (user.l1_language if user else "") or ""

        ev = evidence_mod.build(result, l1_language=l1)
        provider = get_narrator(row.provider_key)
        draft = await provider.narrate(ev, timeout_s=settings.narration_timeout_s)
        clean = validate_mod.check(draft, ev)

    except NarratorError as err:
        return await _record_failure(session, row, err)
    except Exception as err:  # noqa: BLE001 — unexpected: treat as transient once
        return await _record_failure(session, row,
                                     NarratorError("transient", type(err).__name__))

    row.status = "ready"
    row.headline = clean.headline
    row.summary = clean.summary
    row.primary_focus = clean.primary_focus
    row.practice_action = clean.practice_action
    row.caveats = clean.caveats
    row.model_version = clean.model_version or row.model_version
    row.provider_latency_ms = clean.latency_ms
    row.input_tokens = clean.input_tokens
    row.output_tokens = clean.output_tokens
    row.last_error_category = ""
    row.last_error_detail = ""
    row.next_retry_at = None
    row.lease_until = None
    row.generated_at = _now()
    await session.commit()
    log.info("narration ready id=%s attempts=%s latency_ms=%s tokens=%s/%s",
             row.id, row.attempt_count, row.provider_latency_ms,
             row.input_tokens, row.output_tokens)
    return "ready"


async def _record_failure(session: AsyncSession, row: AttemptNarration,
                          err: NarratorError) -> str:
    row.last_error_category = err.category
    row.last_error_detail = err.detail
    row.lease_until = None
    retryable = err.category in RETRYABLE
    if retryable and row.attempt_count < settings.narration_max_attempts:
        row.status = "retry_pending"
        row.next_retry_at = _now() + timedelta(
            seconds=_backoff_seconds(row.attempt_count))
        outcome = "retry_pending"
    else:
        row.status = "failed"
        row.next_retry_at = None
        outcome = "failed"
    await session.commit()
    log.warning("narration %s id=%s category=%s attempts=%s detail=%s",
                outcome, row.id, err.category, row.attempt_count, err.detail)
    return outcome
