"""ntfy.sh push — the default transport.

Chosen because it's the only option that gets a working push notification
onto an iPhone in about five minutes: install the free ntfy app, subscribe to
a private topic, done. No Apple Developer Program, no certificates, no build.

The topic name is the only secret. Anyone who knows it can read the alerts,
so it needs to be long and random rather than "flipscan-deals" — `flipscan
init` generates one.
"""

from __future__ import annotations

import logging

import httpx

from ..config import Settings
from .base import DealAlert, Notifier, NotifyResult

log = logging.getLogger(__name__)


class NtfyNotifier(Notifier):
    name = "ntfy"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.notify.ntfy_topic)

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _url(self) -> str:
        return f"{self.settings.notify.ntfy_server.rstrip('/')}/{self.settings.notify.ntfy_topic}"

    def _headers(self, alert: DealAlert) -> dict[str, str]:
        n = self.settings.notify
        headers = {
            # ntfy reads these as latin-1; an em dash or a £ in a listing title
            # would otherwise throw at request time.
            "Title": alert.headline().encode("ascii", "replace").decode("ascii"),
            "Priority": str(alert.priority()),
            "Tags": ",".join(alert.tags()),
            "Markdown": "yes",
        }
        if n.ntfy_token:
            headers["Authorization"] = f"Bearer {n.ntfy_token}"

        # Tapping the notification opens the deal in the app.
        if alert.app_url:
            headers["Click"] = alert.app_url

        # The listing photo, shown inline on the lock screen. Being able to see
        # the item without opening anything is most of the value of the alert.
        if alert.image_url:
            headers["Attach"] = alert.image_url

        # Action buttons, straight from the notification. "Pass" from the lock
        # screen is what keeps the feed from filling up with things she's
        # already rejected.
        actions = []
        if alert.listing_url:
            actions.append(f"view, Open listing, {alert.listing_url}")
        if alert.app_url:
            base = alert.app_url.split("/app")[0]
            actions.append(
                f"http, Save, {base}/api/deals/{alert.deal_id}/feedback, "
                f"method=POST, body='{{\"action\":\"saved\"}}', clear=true"
            )
            actions.append(
                f"http, Pass, {base}/api/deals/{alert.deal_id}/feedback, "
                f"method=POST, body='{{\"action\":\"passed\"}}', clear=true"
            )
        if actions:
            headers["Actions"] = "; ".join(actions)

        return headers

    async def send(self, alert: DealAlert) -> NotifyResult:
        result = NotifyResult(channel=self.name)
        if not self.configured:
            result.errors.append("no ntfy topic configured")
            return result

        try:
            client = await self._http()
            response = await client.post(
                self._url(),
                headers=self._headers(alert),
                content=alert.body().encode("utf-8"),
            )
            response.raise_for_status()
            result.sent = 1
        except Exception as exc:
            result.failed = 1
            result.errors.append(f"{type(exc).__name__}: {exc}")
            log.warning("ntfy send failed: %s", exc)

        return result

    async def send_text(self, title: str, body: str, priority: int = 3) -> NotifyResult:
        result = NotifyResult(channel=self.name)
        if not self.configured:
            result.errors.append("no ntfy topic configured")
            return result

        headers = {
            "Title": title.encode("ascii", "replace").decode("ascii"),
            "Priority": str(priority),
        }
        if self.settings.notify.ntfy_token:
            headers["Authorization"] = f"Bearer {self.settings.notify.ntfy_token}"

        try:
            client = await self._http()
            response = await client.post(
                self._url(), headers=headers, content=body.encode("utf-8")
            )
            response.raise_for_status()
            result.sent = 1
        except Exception as exc:
            result.failed = 1
            result.errors.append(str(exc))

        return result
