"""Hourly cadence.

APScheduler rather than cron because the scan has to share a process with the
API — they use the same SQLite database and the same in-memory manual queue —
and because the jitter and overlap protection below are easier to get right
in one place than spread across a crontab and a lockfile.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import Settings
from .db import effective_settings, session_scope
from .pipeline import run_scan

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_scan_lock = asyncio.Lock()
_last_run: datetime | None = None


async def scheduled_scan() -> None:
    """One scheduled pass, with jitter and overlap protection."""
    global _last_run

    if _scan_lock.locked():
        # A previous scan is still going. Skipping is the right call: two
        # browser sessions hitting Marketplace at once is exactly the pattern
        # that gets an account flagged.
        log.warning("previous scan still running — skipping this tick")
        return

    async with _scan_lock:
        # Never fire at exactly :00. Predictable timing is a bot signature,
        # and a few minutes' delay costs nothing on an hourly cadence.
        with session_scope() as session:
            settings = effective_settings(session)

        jitter = random.uniform(0, settings.scan.jitter_seconds)
        log.info("scan starting in %.0fs (jitter)", jitter)
        await asyncio.sleep(jitter)

        try:
            run = await run_scan(settings, trigger="schedule")
            _last_run = datetime.now(UTC)
            log.info(
                "scan complete: %d seen, %d new, %d deals, %d alerts, $%.4f",
                run.listings_seen, run.new_listings, run.deals_found,
                run.alerts_sent, run.ai_cost_usd,
            )
            if run.errors:
                log.warning("scan finished with %d error(s): %s",
                            len(run.errors), run.errors[:3])
        except Exception:
            log.exception("scheduled scan failed")


def start_scheduler(settings: Settings | None = None) -> AsyncIOScheduler:
    """Start the hourly job. Idempotent."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    settings = settings or effective_settings()
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        scheduled_scan,
        trigger=IntervalTrigger(minutes=settings.scan.interval_minutes),
        id="hourly_scan",
        name="Marketplace scan",
        # If the process was down over several intervals, run once on restart
        # rather than firing a burst of catch-up scans.
        coalesce=True,
        max_instances=1,
        misfire_grace_time=600,
    )
    _scheduler.start()
    log.info("scheduler started — scanning every %d minutes (+ up to %ds jitter)",
             settings.scan.interval_minutes, settings.scan.jitter_seconds)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler stopped")


def scheduler_status() -> dict:
    if _scheduler is None or not _scheduler.running:
        return {"running": False, "next_run": None, "last_run": None}
    job = _scheduler.get_job("hourly_scan")
    return {
        "running": True,
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "last_run": _last_run.isoformat() if _last_run else None,
        "scanning_now": _scan_lock.locked(),
    }
