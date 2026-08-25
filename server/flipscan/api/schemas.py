"""Response shapes for the phone clients."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, field_serializer


def utc_iso(value: datetime | None) -> str | None:
    """Serialise a datetime with an explicit UTC offset.

    SQLite has no timezone type, so a value stored as aware UTC reads back
    naive. Emitted as-is it becomes '2026-08-25T04:27:08' — which every client
    interprets as *local* time, silently shifting every "found 3m ago" by the
    viewer's offset. Everything written here is UTC, so stamping it is correct
    rather than merely convenient.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


class MoneyBreakdown(BaseModel):
    """Every dollar between the asking price and the profit, itemised, so the
    number in the app can be checked rather than trusted."""

    buy_price: float
    resale_estimate: float
    resale_low: float
    resale_high: float
    gross_spread: float
    platform_fees: float
    shipping_cost: float
    refurb_cost: float
    trip_cost: float
    net_profit: float
    roi_pct: float
    venue: str


class ConditionInfo(BaseModel):
    grade: str = "C"
    score: float = 50.0
    summary: str = ""
    functional_status: str = "unknown"
    damage_flags: list[str] = []
    missing_parts: list[str] = []
    positive_signals: list[str] = []
    photo_quality: str = "unknown"
    photo_caveats: list[str] = []
    uses_stock_photos: bool = False
    identified_brand: str | None = None
    identified_model: str | None = None
    analyzed_by_ai: bool = False


class CompsInfo(BaseModel):
    estimate_low: float = 0.0
    estimate_mid: float = 0.0
    estimate_high: float = 0.0
    confidence: float = 0.0
    sample_size: int = 0
    est_days_to_sell: int | None = None
    method: str = ""
    query_used: str = ""
    sources: list[dict] = []


class SafetyInfo(BaseModel):
    level: str
    headline: str
    rules: list[str]
    payment_note: str


class DealSummary(BaseModel):
    """One row in the feed."""

    id: int
    title: str
    buy_price: float
    net_profit: float
    roi_pct: float
    resale_estimate: float
    deal_score: float
    confidence: float
    risk_score: float
    distance_miles: float
    max_worth_driving_miles: float
    worth_the_drive: bool
    bulk_class: str
    condition_grade: str
    location: str | None = None
    image_url: str | None = None
    listing_url: str
    status: str
    category: str | None = None
    est_days_to_sell: int | None = None
    warning_count: int = 0
    created_at: datetime
    posted_at: datetime | None = None

    @field_serializer("created_at", "posted_at")
    def _serialize_times(self, value: datetime | None, _info) -> str | None:
        return utc_iso(value)


class DealDetail(DealSummary):
    """Everything about one deal."""

    description: str = ""
    seller_name: str | None = None
    money: MoneyBreakdown
    condition: ConditionInfo
    comps: CompsInfo
    safety: SafetyInfo
    reasons: list[str] = []
    warnings: list[str] = []
    inspection_checklist: list[str] = []
    image_urls: list[str] = []
    screenshot_url: str | None = None
    price_history: list[dict] = []
    first_seen_price: float = 0.0


class FeedbackIn(BaseModel):
    action: str                              # saved | passed | bought | sold | dud
    actual_buy_price: float | None = None
    actual_sale_price: float | None = None
    actual_days_to_sell: int | None = None
    sold_venue: str | None = None
    note: str = ""


class RunSummary(BaseModel):
    """A cluster of pickups worth doing in one drive."""

    label: str
    center_lat: float
    center_lon: float
    deal_ids: list[int]
    deal_count: int
    distance_from_home: float
    total_net_profit: float
    profit_after_trip: float
    est_hours: float
    summary: str


class ManualListingIn(BaseModel):
    url: str | None = None
    text: str = ""
    title: str | None = None
    price: float | None = None
    location: str | None = None


class SettingsPatch(BaseModel):
    updates: dict


class DeviceIn(BaseModel):
    platform: str                            # apns | webpush
    token: str
    label: str = ""


class WatchlistIn(BaseModel):
    name: str
    query: str
    category: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    bulk_class: str = "box"
    enabled: bool = True
    priority: int = 5
    notes: str = ""
