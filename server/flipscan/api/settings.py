"""Settings and watchlists, editable from the phone."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..config import Settings, get_settings
from ..db import OVERRIDABLE, load_overrides, save_overrides
from ..models import Watchlist
from .deps import get_db, require_token, settings_dep
from .schemas import SettingsPatch, WatchlistIn

router = APIRouter(prefix="/api", tags=["settings"], dependencies=[Depends(require_token)])


@router.get("/settings")
def read_settings(
    session: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> dict:
    """Current effective config, plus what may be changed from here."""
    return {
        "effective": settings.redacted(),
        "overrides": load_overrides(session),
        "overridable_keys": sorted(OVERRIDABLE),
        # Surfaced so the app can explain each number rather than just
        # showing a slider with no context.
        "explanations": {
            "profit.min_net_profit":
                "Don't alert unless the profit after every cost clears this.",
            "profit.min_roi_pct":
                "Minimum return on the cash you put in. Stops thin margins on "
                "expensive items that tie up money.",
            "profit.min_deal_score":
                "Overall quality bar, 0-100. Catches deals that pencil out but "
                "look risky in the photos.",
            "trip.max_trip_cost_fraction":
                "The most of a deal's profit you'll spend getting there. Raise "
                "it to drive further for the same money.",
            "trip.hourly_time_value":
                "What an hour of your time is worth. Drives how far a given "
                "profit justifies travelling.",
            "trip.max_radius_miles":
                "Hard ceiling on driving distance, however good the deal.",
            "scan.quiet_hours_start":
                "No pushes after this hour. Big finds (over $500) still come "
                "through.",
        },
    }


@router.patch("/settings")
def patch_settings(
    payload: SettingsPatch,
    session: Session = Depends(get_db),
) -> dict:
    try:
        merged = save_overrides(session, payload.updates)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    session.commit()
    return {"ok": True, "overrides": merged}


@router.delete("/settings/overrides")
def clear_overrides(session: Session = Depends(get_db)) -> dict:
    """Back to the values in .env."""
    from ..models import UserSettings

    row = session.get(UserSettings, 1)
    if row:
        row.data = {}
        session.add(row)
        session.commit()
    get_settings.cache_clear()
    return {"ok": True, "overrides": {}}


# --------------------------------------------------------------------------
# Watchlists
# --------------------------------------------------------------------------
@router.get("/watchlists")
def list_watchlists(session: Session = Depends(get_db)) -> list[dict]:
    rows = session.exec(
        select(Watchlist).order_by(Watchlist.priority, Watchlist.name)
    ).all()
    return [r.model_dump() for r in rows]


@router.post("/watchlists")
def create_watchlist(payload: WatchlistIn, session: Session = Depends(get_db)) -> dict:
    row = Watchlist(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row.model_dump()


@router.patch("/watchlists/{watchlist_id}")
def update_watchlist(
    watchlist_id: int, payload: dict, session: Session = Depends(get_db)
) -> dict:
    row = session.get(Watchlist, watchlist_id)
    if row is None:
        raise HTTPException(404, "Watchlist not found")

    allowed = {
        "name", "query", "category", "min_price", "max_price", "bulk_class",
        "enabled", "priority", "notes", "value_retention_hint",
    }
    for key, value in payload.items():
        if key in allowed:
            setattr(row, key, value)

    session.add(row)
    session.commit()
    session.refresh(row)
    return row.model_dump()


@router.delete("/watchlists/{watchlist_id}")
def delete_watchlist(watchlist_id: int, session: Session = Depends(get_db)) -> dict:
    row = session.get(Watchlist, watchlist_id)
    if row is None:
        raise HTTPException(404, "Watchlist not found")
    session.delete(row)
    session.commit()
    return {"ok": True}
