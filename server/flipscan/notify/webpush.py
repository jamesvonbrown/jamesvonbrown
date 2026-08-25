"""Web Push — notifications straight to the installed PWA.

iOS 16.4+ delivers Web Push to a web app that has been added to the Home
Screen, which means the PWA can notify her without ntfy and without an App
Store build. It's a nice upgrade once things are working; ntfy stays the
default because it needs no keys and no install-to-home-screen step.

Requires the `push` extra: pip install 'flipscan[push]'
"""

from __future__ import annotations

import json
import logging

from ..config import Settings
from .base import DealAlert, Notifier, NotifyResult

log = logging.getLogger(__name__)


class WebPushNotifier(Notifier):
    name = "webpush"

    def __init__(self, settings: Settings, subscriptions: list[dict] | None = None):
        self.settings = settings
        self.subscriptions = subscriptions or []

    @property
    def configured(self) -> bool:
        n = self.settings.notify
        return bool(n.vapid_private_key and n.vapid_public_key and self.subscriptions)

    def _payload(self, alert: DealAlert) -> str:
        return json.dumps(
            {
                "title": alert.headline(),
                "body": alert.body(),
                "icon": "/icons/icon-192.png",
                "badge": "/icons/badge.png",
                "image": alert.image_url or None,
                "tag": f"deal-{alert.deal_id}",
                "data": {
                    "deal_id": alert.deal_id,
                    "url": alert.app_url or "/",
                    "listing_url": alert.listing_url,
                },
                "actions": [
                    {"action": "open", "title": "Open listing"},
                    {"action": "pass", "title": "Pass"},
                ],
            }
        )

    async def send(self, alert: DealAlert) -> NotifyResult:
        result = NotifyResult(channel=self.name)
        if not self.configured:
            result.errors.append("web push not configured or no subscriptions")
            return result

        try:
            from pywebpush import WebPushException, webpush
        except ImportError:
            result.errors.append("pywebpush missing — pip install 'flipscan[push]'")
            return result

        import asyncio

        payload = self._payload(alert)
        claims = {"sub": f"mailto:{self.settings.notify.vapid_contact_email or 'admin@example.com'}"}

        def _send_one(subscription: dict) -> tuple[bool, str]:
            try:
                webpush(
                    subscription_info=subscription,
                    data=payload,
                    vapid_private_key=self.settings.notify.vapid_private_key,
                    vapid_claims=dict(claims),
                )
                return True, ""
            except WebPushException as exc:
                # 404/410 mean the browser dropped the subscription — it should
                # be pruned rather than retried forever.
                status = getattr(getattr(exc, "response", None), "status_code", 0)
                return False, f"gone:{status}" if status in (404, 410) else str(exc)
            except Exception as exc:
                return False, str(exc)

        outcomes = await asyncio.gather(
            *(asyncio.to_thread(_send_one, s) for s in self.subscriptions)
        )
        for ok, error in outcomes:
            if ok:
                result.sent += 1
            else:
                result.failed += 1
                result.errors.append(error)

        return result
