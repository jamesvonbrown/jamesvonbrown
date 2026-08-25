"""Twilio SMS — a backup channel for the rare very large find.

Deliberately gated behind a high profit threshold. At an hourly cadence, SMS
gets annoying fast, costs about a cent a message, and can't show the photo
that makes an alert useful. It earns its place only for the $800-spread find
she'd want to know about even with her phone face-down.
"""

from __future__ import annotations

import logging

import httpx

from ..config import Settings
from .base import DealAlert, Notifier, NotifyResult

log = logging.getLogger(__name__)

API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class SmsNotifier(Notifier):
    name = "sms"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        n = self.settings.notify
        return bool(n.twilio_account_sid and n.twilio_auth_token
                    and n.twilio_from and n.twilio_to)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def send(self, alert: DealAlert) -> NotifyResult:
        result = NotifyResult(channel=self.name)
        n = self.settings.notify

        if not self.configured:
            result.errors.append("Twilio not configured")
            return result

        if alert.net_profit < n.sms_min_profit:
            # Not a failure — this alert simply isn't big enough for a text.
            return result

        body = (
            f"{alert.headline()}\n"
            f"${alert.buy_price:,.0f} → ~${alert.resale_estimate:,.0f} "
            f"({alert.roi_pct:.0f}% ROI), {alert.distance_miles:.0f} mi\n"
            f"{alert.app_url or alert.listing_url}"
        )

        try:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=15.0)
            response = await self._client.post(
                API.format(sid=n.twilio_account_sid),
                auth=(n.twilio_account_sid, n.twilio_auth_token),
                data={"From": n.twilio_from, "To": n.twilio_to, "Body": body[:1500]},
            )
            response.raise_for_status()
            result.sent = 1
        except Exception as exc:
            result.failed = 1
            result.errors.append(f"{type(exc).__name__}: {exc}")

        return result
