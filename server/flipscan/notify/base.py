"""Notification payloads and the transport interface.

One `DealAlert` is rendered once and sent through whatever transports are
configured, so the wording is identical whether it arrives as an ntfy push,
a web push, or a text message.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo


@dataclass
class DealAlert:
    """Everything a notification needs, transport-agnostic."""

    deal_id: int
    title: str                     # item title
    buy_price: float
    net_profit: float
    roi_pct: float
    resale_estimate: float
    distance_miles: float
    deal_score: float
    confidence: float

    listing_url: str = ""
    app_url: str = ""
    image_url: str = ""
    location: str = ""
    condition_grade: str = "B"
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    est_days_to_sell: int | None = None

    # -- rendering ----------------------------------------------------------
    def headline(self) -> str:
        """Lock-screen line. Profit first — it's the only number that decides
        whether she opens this or rolls over."""
        return f"${self.net_profit:,.0f} profit · {self.title[:52]}"

    def body(self) -> str:
        lines = [
            f"Buy ${self.buy_price:,.0f} → sells ~${self.resale_estimate:,.0f} "
            f"({self.roi_pct:.0f}% ROI)",
            f"{self.distance_miles:.0f} mi away"
            + (f" · {self.location}" if self.location else ""),
        ]
        if self.est_days_to_sell:
            lines.append(f"Usually sells in ~{self.est_days_to_sell} days")

        if self.confidence < 0.45:
            lines.append("⚠︎ Low-confidence estimate — check the comps yourself")
        if self.warnings:
            lines.append("⚠︎ " + self.warnings[0])

        return "\n".join(lines)

    def priority(self) -> int:
        """1 (min) - 5 (max). Reserve 5 for things genuinely worth waking up
        for; if everything is urgent she'll mute the whole channel by Friday."""
        if self.net_profit >= 750 and self.deal_score >= 80:
            return 5
        if self.net_profit >= 300 or self.deal_score >= 85:
            return 4
        if self.net_profit >= 120:
            return 3
        return 2

    def tags(self) -> list[str]:
        tags = []
        if self.net_profit >= 500:
            tags.append("moneybag")
        elif self.net_profit >= 200:
            tags.append("dollar")
        else:
            tags.append("shopping_cart")
        if self.warnings:
            tags.append("warning")
        if self.confidence >= 0.7:
            tags.append("white_check_mark")
        return tags


@dataclass
class NotifyResult:
    channel: str
    sent: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0 and not self.errors


class Notifier(abc.ABC):
    """A way of getting an alert to her phone."""

    name: str = "base"

    @property
    @abc.abstractmethod
    def configured(self) -> bool:
        """False when credentials are missing — skipped without an error."""

    @abc.abstractmethod
    async def send(self, alert: DealAlert) -> NotifyResult:
        ...

    async def send_text(self, title: str, body: str, priority: int = 3) -> NotifyResult:
        """Plain message, for scan summaries and health warnings."""
        return NotifyResult(channel=self.name, errors=["not implemented"])

    async def close(self) -> None:
        return None


# --------------------------------------------------------------------------
# Quiet hours
# --------------------------------------------------------------------------
def in_quiet_hours(
    start_hour: int, end_hour: int, tz_name: str = "America/Los_Angeles",
    now: datetime | None = None,
) -> bool:
    """Is it currently inside the do-not-disturb window?

    Handles the overnight case (22:00 to 07:00) where the window wraps past
    midnight, which a naive start <= hour < end comparison gets wrong.
    """
    if start_hour == end_hour:
        return False

    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = UTC

    current = (now or datetime.now(UTC)).astimezone(tz).time()
    start, end = time(start_hour % 24), time(end_hour % 24)

    if start < end:
        return start <= current < end
    return current >= start or current < end
