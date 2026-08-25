"""Apple Push Notification service — for the native SwiftUI build.

Only relevant once there's a Mac, an Apple Developer Program membership
($99/yr), and a real device build. Written now so that day is a config
change rather than a project.

Uses token-based auth (a .p8 key) over HTTP/2, which is simpler and longer-
lived than certificate auth. Requires the `push` extra.
"""

from __future__ import annotations

import json
import logging
import time

from ..config import Settings
from .base import DealAlert, Notifier, NotifyResult

log = logging.getLogger(__name__)

PROD_HOST = "https://api.push.apple.com"
SANDBOX_HOST = "https://api.sandbox.push.apple.com"


class APNsNotifier(Notifier):
    name = "apns"

    def __init__(self, settings: Settings, device_tokens: list[str] | None = None):
        self.settings = settings
        self.device_tokens = device_tokens or []
        self._jwt: str | None = None
        self._jwt_issued: float = 0.0
        self._client = None

    @property
    def configured(self) -> bool:
        n = self.settings.notify
        return bool(
            n.apns_key_id and n.apns_team_id and n.apns_key_path and self.device_tokens
        )

    def _auth_token(self) -> str | None:
        """APNs JWTs are valid for an hour; Apple rejects refreshes more often
        than every 20 minutes, so this refreshes at 45."""
        if self._jwt and (time.time() - self._jwt_issued) < 2700:
            return self._jwt

        try:
            import jwt
        except ImportError:
            log.error("PyJWT missing — pip install 'flipscan[push]'")
            return None

        n = self.settings.notify
        try:
            with open(n.apns_key_path) as handle:
                private_key = handle.read()
            self._jwt = jwt.encode(
                {"iss": n.apns_team_id, "iat": int(time.time())},
                private_key,
                algorithm="ES256",
                headers={"kid": n.apns_key_id},
            )
            self._jwt_issued = time.time()
            return self._jwt
        except Exception as exc:
            log.error("APNs JWT generation failed: %s", exc)
            return None

    async def send(self, alert: DealAlert) -> NotifyResult:
        result = NotifyResult(channel=self.name)
        if not self.configured:
            result.errors.append("APNs not configured or no registered devices")
            return result

        token = self._auth_token()
        if not token:
            result.errors.append("could not build APNs auth token")
            return result

        try:
            import httpx
        except ImportError:  # pragma: no cover
            result.errors.append("httpx missing")
            return result

        n = self.settings.notify
        host = SANDBOX_HOST if n.apns_use_sandbox else PROD_HOST
        payload = {
            "aps": {
                "alert": {"title": alert.headline(), "body": alert.body()},
                "sound": "default",
                "badge": 1,
                # Lets the app fetch the photo before the banner renders.
                "mutable-content": 1,
                "interruption-level": "time-sensitive" if alert.priority() >= 4 else "active",
            },
            "deal_id": alert.deal_id,
            "url": alert.app_url,
            "listing_url": alert.listing_url,
            "image_url": alert.image_url,
        }

        # HTTP/2 is mandatory for APNs.
        if self._client is None:
            self._client = httpx.AsyncClient(http2=True, timeout=15.0)

        for device_token in self.device_tokens:
            try:
                response = await self._client.post(
                    f"{host}/3/device/{device_token}",
                    headers={
                        "authorization": f"bearer {token}",
                        "apns-topic": n.apns_bundle_id,
                        "apns-push-type": "alert",
                        "apns-priority": "10",
                    },
                    content=json.dumps(payload),
                )
                if response.status_code == 200:
                    result.sent += 1
                else:
                    result.failed += 1
                    result.errors.append(f"{response.status_code}: {response.text[:120]}")
            except Exception as exc:
                result.failed += 1
                result.errors.append(f"{type(exc).__name__}: {exc}")

        return result

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
