"""Notification transports."""

from __future__ import annotations

import asyncio
import logging

from ..config import Settings
from .apns import APNsNotifier
from .base import DealAlert, Notifier, NotifyResult, in_quiet_hours
from .ntfy import NtfyNotifier
from .sms import SmsNotifier
from .webpush import WebPushNotifier

log = logging.getLogger(__name__)


def build_notifiers(
    settings: Settings,
    *,
    webpush_subscriptions: list[dict] | None = None,
    apns_tokens: list[str] | None = None,
) -> list[Notifier]:
    """Every configured transport. Unconfigured ones are skipped silently —
    having ntfy set up and APNs not is the normal case, not an error."""
    built: list[Notifier] = []
    for name in settings.notify.channels:
        if name == "ntfy":
            built.append(NtfyNotifier(settings))
        elif name == "webpush":
            built.append(WebPushNotifier(settings, webpush_subscriptions))
        elif name == "apns":
            built.append(APNsNotifier(settings, apns_tokens))
        elif name == "sms":
            built.append(SmsNotifier(settings))
        else:
            log.warning("unknown notification channel %r", name)

    active = [n for n in built if n.configured]
    if built and not active:
        log.warning(
            "notification channels %s are all unconfigured — deals will appear "
            "in the app but nothing will be pushed. Run `flipscan init`.",
            settings.notify.channels,
        )
    return active


async def broadcast(notifiers: list[Notifier], alert: DealAlert) -> list[NotifyResult]:
    """Send one alert everywhere at once. A dead transport never blocks the
    others, and never takes the scan down with it."""
    if not notifiers:
        return []

    results = await asyncio.gather(
        *(n.send(alert) for n in notifiers), return_exceptions=True
    )

    out: list[NotifyResult] = []
    for notifier, result in zip(notifiers, results, strict=True):
        if isinstance(result, BaseException):
            out.append(NotifyResult(channel=notifier.name, failed=1,
                                    errors=[f"{type(result).__name__}: {result}"]))
        else:
            out.append(result)
    return out


__all__ = [
    "DealAlert", "Notifier", "NotifyResult", "in_quiet_hours",
    "NtfyNotifier", "WebPushNotifier", "APNsNotifier", "SmsNotifier",
    "build_notifiers", "broadcast",
]
