"""The narration recovery worker.

Two ways in, one body:
  * the in-process sweeper started in the app lifespan (settings-gated), which
    is the restart-safety net — a job left pending or half-processed by a crash
    is picked up on the next tick;
  * ``python -m app.narration`` for running it out of process, the same shape
    as ``python -m app.retention``.

The fast path is separate: the moment an attempt is scored, a BackgroundTask
calls kick() to generate immediately. The sweeper exists so that nothing is
*lost* if that fast path never ran or died mid-flight — durability does not
depend on the process that created the job staying alive.
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import select

from app.config import settings
from app.db import platform_sessionmaker, tenant_sessionmaker
from app.models.platform import Tenant
from app.narration import service

log = logging.getLogger("narration.worker")


async def tick_tenant(slug: str, *, batch: int | None = None) -> dict[str, int]:
    """Claim and generate one batch of due jobs for one tenant.

    Deterministic and awaitable, so a test can drive exactly one pass rather
    than racing a loop. Returns a small counts dict for observability.
    """
    batch = batch or settings.narration_worker_batch
    counts = {"claimed": 0, "ready": 0, "retry_pending": 0, "failed": 0}
    async with tenant_sessionmaker(slug)() as session:
        ids = await service.claim_due(session, batch=batch)
    counts["claimed"] = len(ids)
    for narration_id in ids:
        # A fresh session per job: one bad job cannot poison the batch, and the
        # lease already protects the row from another worker.
        async with tenant_sessionmaker(slug)() as session:
            outcome = await service.generate_one(session, narration_id)
        if outcome in counts:
            counts[outcome] += 1
    return counts


async def tick_all(*, batch: int | None = None) -> dict[str, dict[str, int]]:
    async with platform_sessionmaker()() as session:
        slugs = list((await session.execute(select(Tenant.slug))).scalars().all())
    return {slug: await tick_tenant(slug, batch=batch) for slug in slugs}


async def kick(slug: str, narration_id: str) -> str:
    """Generate one specific job now — the fast path after an attempt is scored.

    Claims the row itself (so it cannot double-run against the sweeper), then
    generates. Safe to call fire-and-forget from a BackgroundTask.
    """
    async with tenant_sessionmaker(slug)() as session:
        won = await service.claim_one(session, narration_id)
    if not won:
        # The sweeper already owns it, or it is no longer claimable. Not an
        # error: the job will still be generated, just not by this call.
        return "not_claimed"
    async with tenant_sessionmaker(slug)() as session:
        return await service.generate_one(session, narration_id)


async def run_forever() -> None:
    """The lifespan sweeper. Sleeps between ticks; never crashes the loop."""
    interval = settings.narration_worker_interval_s
    log.info("narration sweeper started (interval=%ss)", interval)
    while True:
        try:
            await tick_all()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — a bad tick must not stop the sweeper
            log.exception("narration sweeper tick failed")
        await asyncio.sleep(interval)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate pending AI narrations.")
    parser.add_argument("--once", action="store_true",
                        help="run a single pass and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.once:
        print(asyncio.run(tick_all()))
    else:
        asyncio.run(run_forever())


if __name__ == "__main__":
    _main()
