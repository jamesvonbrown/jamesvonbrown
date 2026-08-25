"""Push-target registration and notification testing."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..config import Settings, get_settings
from ..models import Device, utcnow
from ..notify import DealAlert, broadcast, build_notifiers
from .deps import get_db, require_token, settings_dep
from .schemas import DeviceIn

router = APIRouter(prefix="/api/devices", tags=["devices"],
                   dependencies=[Depends(require_token)])


@router.get("")
def list_devices(session: Session = Depends(get_db)) -> list[dict]:
    rows = session.exec(select(Device)).all()
    return [
        {
            "id": r.id,
            "platform": r.platform,
            "label": r.label,
            "enabled": r.enabled,
            # Never echo a full push token back to a client.
            "token_preview": (r.token[:18] + "…") if len(r.token) > 18 else r.token,
            "created_at": r.created_at,
            "failure_count": r.failure_count,
        }
        for r in rows
    ]


@router.post("")
def register_device(payload: DeviceIn, session: Session = Depends(get_db)) -> dict:
    if payload.platform not in ("apns", "webpush"):
        raise HTTPException(400, "platform must be 'apns' or 'webpush'")

    if payload.platform == "webpush":
        try:
            parsed = json.loads(payload.token)
            if "endpoint" not in parsed:
                raise ValueError("missing endpoint")
        except Exception as exc:
            raise HTTPException(400, f"webpush token must be a subscription JSON: {exc}") from exc

    existing = session.exec(
        select(Device)
        .where(Device.platform == payload.platform)
        .where(Device.token == payload.token)
    ).first()

    if existing:
        existing.enabled = True
        existing.failure_count = 0
        existing.last_used_at = utcnow()
        session.add(existing)
        session.commit()
        return {"ok": True, "id": existing.id, "created": False}

    row = Device(platform=payload.platform, token=payload.token, label=payload.label)
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"ok": True, "id": row.id, "created": True}


@router.delete("/{device_id}")
def delete_device(device_id: int, session: Session = Depends(get_db)) -> dict:
    row = session.get(Device, device_id)
    if row is None:
        raise HTTPException(404, "Device not found")
    session.delete(row)
    session.commit()
    return {"ok": True}


@router.get("/vapid-public-key")
def vapid_public_key() -> dict:
    """Public key the PWA needs to subscribe to Web Push."""
    return {"key": get_settings().notify.vapid_public_key}


@router.post("/test")
async def send_test(settings: Settings = Depends(settings_dep),
                    session: Session = Depends(get_db)) -> dict:
    """Fire a sample alert through every configured channel."""
    subs, tokens = [], []
    for device in session.exec(select(Device).where(Device.enabled == True)).all():  # noqa: E712
        if device.platform == "webpush":
            try:
                subs.append(json.loads(device.token))
            except Exception:
                pass
        elif device.platform == "apns":
            tokens.append(device.token)

    notifiers = build_notifiers(settings, webpush_subscriptions=subs, apns_tokens=tokens)
    if not notifiers:
        raise HTTPException(
            400,
            "No notification channel is configured. Set FLIPSCAN_NOTIFY__NTFY_TOPIC "
            "in .env, or register a device for web push.",
        )

    alert = DealAlert(
        deal_id=0,
        title="Herman Miller Aeron Chair Size B (test alert)",
        buy_price=180, net_profit=570, roi_pct=248, resale_estimate=800,
        distance_miles=12, deal_score=94, confidence=0.85,
        listing_url="https://www.facebook.com/marketplace/",
        app_url=f"{settings.public_base_url}/app/",
        location="Beaverton, OR", est_days_to_sell=9,
    )

    results = await broadcast(notifiers, alert)
    for notifier in notifiers:
        await notifier.close()

    return {
        "sent": sum(r.sent for r in results),
        "results": [
            {"channel": r.channel, "sent": r.sent, "failed": r.failed, "errors": r.errors}
            for r in results
        ],
    }
