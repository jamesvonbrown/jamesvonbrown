"""Scan control and health."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlmodel import Session, select

from ..config import Settings
from ..models import ApiUsage, Deal, Listing, ScanRun
from ..scheduler import scheduler_status
from .deps import get_db, require_token, settings_dep

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scans"], dependencies=[Depends(require_token)])

_manual_scan_running = False


@router.get("/scans")
def list_scans(session: Session = Depends(get_db), limit: int = 20) -> list[dict]:
    rows = session.exec(
        select(ScanRun).order_by(ScanRun.started_at.desc()).limit(limit)
    ).all()
    return [r.model_dump() for r in rows]


@router.post("/scans/run")
async def trigger_scan(
    background: BackgroundTasks,
    settings: Settings = Depends(settings_dep),
    demo: bool = False,
    notify: bool = True,
) -> dict:
    """Kick off a scan now, without waiting for the hour."""
    global _manual_scan_running

    if _manual_scan_running:
        return {"ok": False, "note": "a scan is already running"}

    async def _run() -> None:
        global _manual_scan_running
        _manual_scan_running = True
        try:
            from ..collectors import DemoCollector
            from ..pipeline import run_scan

            collectors = [DemoCollector(settings)] if demo else None
            await run_scan(settings, trigger="api", collectors=collectors, notify=notify)
        except Exception:
            log.exception("manual scan failed")
        finally:
            _manual_scan_running = False

    background.add_task(lambda: asyncio.create_task(_run()))
    return {"ok": True, "note": "scan started — poll /api/scans for the result"}


@router.get("/status")
def status(session: Session = Depends(get_db),
           settings: Settings = Depends(settings_dep)) -> dict:
    """Everything the app needs to show a health screen."""
    last = session.exec(
        select(ScanRun).order_by(ScanRun.started_at.desc()).limit(1)
    ).first()
    usage = session.exec(
        select(ApiUsage).order_by(ApiUsage.day.desc()).limit(1)
    ).first()

    active_listings = len(
        session.exec(select(Listing).where(Listing.is_active == True)).all()  # noqa: E712
    )
    open_deals = len(
        session.exec(select(Deal).where(Deal.status.in_(["new", "notified", "saved"]))).all()
    )

    warnings: list[str] = []
    if not settings.anthropic_api_key:
        warnings.append(
            "No Anthropic API key — photo condition analysis is off, and deals "
            "are being graded from listing text alone."
        )
    if not (settings.sources.ebay_client_id and settings.sources.ebay_client_secret):
        warnings.append(
            "No eBay keys — resale values are category estimates rather than "
            "real comparable sales. This is the single biggest accuracy win "
            "available, and the keys are free."
        )
    if not settings.notify.ntfy_topic and "ntfy" in settings.notify.channels:
        warnings.append("No ntfy topic set — nothing will be pushed to the phone.")
    if last and last.errors:
        warnings.append(f"Last scan reported {len(last.errors)} error(s).")
    if last and last.listings_seen == 0 and last.trigger == "schedule":
        warnings.append(
            "Last scheduled scan found zero listings. The Facebook session may "
            "have logged out — run `flipscan login`."
        )

    return {
        "scheduler": scheduler_status(),
        "manual_scan_running": _manual_scan_running,
        "active_listings": active_listings,
        "open_deals": open_deals,
        "last_scan": last.model_dump() if last else None,
        "ai_spend_today": {
            "cost_usd": round(usage.cost_usd, 4) if usage else 0.0,
            "budget_usd": settings.ai.daily_budget_usd,
            "calls": usage.calls if usage else 0,
        },
        "collectors": settings.sources.collectors,
        "notify_channels": settings.notify.channels,
        "market": settings.market.name,
        "warnings": warnings,
    }


@router.get("/calibration")
def calibration(session: Session = Depends(get_db)) -> dict:
    """How well have the resale estimates matched what actually happened?"""
    from ..comps import calibration_factor

    overall_factor, overall_n, overall_text = calibration_factor(session)
    per_category = {}
    for category in ["tools", "furniture", "electronics", "bikes", "outdoor",
                     "appliances", "baby", "lawn"]:
        factor, n, text = calibration_factor(session, category)
        if n:
            per_category[category] = {"factor": factor, "samples": n, "note": text}

    return {
        "overall": {"factor": overall_factor, "samples": overall_n, "note": overall_text},
        "by_category": per_category,
    }
