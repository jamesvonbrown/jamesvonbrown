"""Database schema.

The shape here is deliberately append-only around `Listing`: a listing is
observed many times, and each observation can change the price or pull the
item off the market. Valuation, photo analysis, and scoring are separate
tables so we can re-run any one of them without losing the others, and so
every number shown on the phone can be traced back to its evidence.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, Index, UniqueConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------
# Enums (stored as plain strings so the DB stays readable + migratable)
# --------------------------------------------------------------------------
class DealStatus(enum.StrEnum):
    NEW = "new"
    NOTIFIED = "notified"
    SAVED = "saved"
    BOUGHT = "bought"
    PASSED = "passed"
    EXPIRED = "expired"
    SOLD = "sold"


class BulkClass(enum.StrEnum):
    """How hard the item is to physically collect. Drives trip cost."""

    POCKET = "pocket"          # fits in a bag: phones, watches, cameras
    BOX = "box"                # one-hand carry: tools, small appliances
    TWO_PERSON = "two_person"  # dresser, mower, e-bike
    TRUCK = "truck"            # couch, fridge, shed


class FunctionalStatus(enum.StrEnum):
    WORKING = "working"
    UNTESTED = "untested"
    PARTIAL = "partial"
    FOR_PARTS = "for_parts"
    UNKNOWN = "unknown"


# --------------------------------------------------------------------------
# Listings
# --------------------------------------------------------------------------
class Listing(SQLModel, table=True):
    __tablename__ = "listing"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_listing_source_ext"),
        Index("ix_listing_fingerprint", "fingerprint"),
        Index("ix_listing_active_seen", "is_active", "last_seen_at"),
    )

    id: int | None = Field(default=None, primary_key=True)

    source: str = Field(index=True)                 # facebook | manual | demo | ...
    external_id: str
    fingerprint: str                                # cross-source dedupe key
    url: str

    title: str
    description: str = ""
    price: float = Field(index=True)
    first_seen_price: float = 0.0
    currency: str = "USD"

    location_text: str | None = None
    lat: float | None = None
    lon: float | None = None
    distance_miles: float | None = None
    location_confident: bool = True

    posted_at: datetime | None = None
    category: str | None = Field(default=None, index=True)
    bulk_class: str = BulkClass.BOX.value

    seller_name: str | None = None
    seller_url: str | None = None
    seller_joined_year: int | None = None

    image_urls: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    local_images: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Whatever the collector saw, kept verbatim. Invaluable when a source
    # changes its markup and the parser starts producing nonsense.
    raw: dict = Field(default_factory=dict, sa_column=Column(JSON))

    first_seen_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow, index=True)
    times_seen: int = 1
    is_active: bool = Field(default=True, index=True)
    delisted_at: datetime | None = None


class PriceObservation(SQLModel, table=True):
    """Price history. A listing that keeps dropping is a listing whose seller
    is getting motivated — that's a buy signal worth surfacing on its own."""

    __tablename__ = "price_observation"

    id: int | None = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)
    price: float
    observed_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------
# Valuation
# --------------------------------------------------------------------------
class CompSet(SQLModel, table=True):
    """What the item realistically resells for, and how sure we are."""

    __tablename__ = "comp_set"

    id: int | None = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)

    query_used: str = ""

    estimate_low: float = 0.0
    estimate_mid: float = 0.0
    estimate_high: float = 0.0

    # 0.0-1.0. Low confidence widens the low/high band and pulls the deal
    # score down; it does not by itself disqualify a listing.
    confidence: float = 0.0
    sample_size: int = 0

    # How quickly it moves. A $200 margin on something that sits for 6 months
    # is worse than a $120 margin that turns in a week.
    sell_through_pct: float | None = None
    est_days_to_sell: int | None = None

    # [{provider, n, median, low, high, weight, note, examples:[{title,price,url}]}]
    sources: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    method: str = ""
    created_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------
# AI analysis
# --------------------------------------------------------------------------
class Analysis(SQLModel, table=True):
    """Photo + description read of the item."""

    __tablename__ = "analysis"

    id: int | None = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)

    # What we think it actually is — often more specific than the title.
    identified_brand: str | None = None
    identified_model: str | None = None
    identified_year: str | None = None
    identification_confidence: float = 0.0

    condition_grade: str = "C"           # A-F
    condition_score: float = 50.0        # 0-100
    condition_summary: str = ""

    damage_flags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    missing_parts: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    positive_signals: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    functional_status: str = FunctionalStatus.UNKNOWN.value

    # Photo trustworthiness. A stock photo on a used-goods listing means you
    # genuinely do not know what you're buying.
    uses_stock_photos: bool = False
    photo_quality: str = "unknown"       # good | poor | misleading | unknown
    photo_caveats: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Description mining
    description_red_flags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    description_green_flags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    scam_risk: float = 0.0               # 0-100
    authenticity_concern: bool = False

    # Best search string for comps, written by the model after it has looked
    # at both the photos and the text.
    suggested_comp_query: str | None = None

    resale_condition_multiplier: float = 1.0
    model_used: str = ""
    cost_usd: float = 0.0
    raw_response: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------
# Deals
# --------------------------------------------------------------------------
class Deal(SQLModel, table=True):
    """A scored buying opportunity. One per (listing, scoring run)."""

    __tablename__ = "deal"
    __table_args__ = (Index("ix_deal_score_created", "deal_score", "created_at"),)

    id: int | None = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)
    comp_set_id: int | None = Field(default=None, foreign_key="comp_set.id")
    analysis_id: int | None = Field(default=None, foreign_key="analysis.id")

    buy_price: float
    resale_estimate: float
    resale_low: float = 0.0
    resale_high: float = 0.0
    venue: str = "facebook_local"

    # Full cost breakdown — every number the phone shows traces to one of these.
    gross_spread: float = 0.0
    platform_fees: float = 0.0
    shipping_cost: float = 0.0
    refurb_cost: float = 0.0
    trip_cost: float = 0.0
    net_profit: float = 0.0
    roi_pct: float = 0.0

    deal_score: float = Field(default=0.0, index=True)
    risk_score: float = 0.0
    confidence: float = 0.0

    distance_miles: float = 0.0
    max_worth_driving_miles: float = 0.0
    worth_the_drive: bool = True
    bulk_class: str = BulkClass.BOX.value

    # Human-readable justification, shown in the app and the notification.
    reasons: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    status: str = Field(default=DealStatus.NEW.value, index=True)
    alerts_sent: int = 0
    notified_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow, index=True)


class Feedback(SQLModel, table=True):
    """Ground truth. This is what makes the tool get better instead of just
    repeating the same estimate errors forever — see comps/internal.py."""

    __tablename__ = "feedback"

    id: int | None = Field(default=None, primary_key=True)
    deal_id: int = Field(foreign_key="deal.id", index=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)

    action: str                              # bought | passed | sold | dud
    actual_buy_price: float | None = None
    actual_sale_price: float | None = None
    actual_days_to_sell: int | None = None
    sold_venue: str | None = None
    note: str = ""
    created_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------
# Operational
# --------------------------------------------------------------------------
class Watchlist(SQLModel, table=True):
    """A saved search. The scanner walks the enabled ones every hour."""

    __tablename__ = "watchlist"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    query: str
    category: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    bulk_class: str = BulkClass.BOX.value

    # Typical resale multiplier hint for this category, used as a prior when
    # comps are thin. e.g. name-brand power tools hold value; TVs do not.
    value_retention_hint: float | None = None

    enabled: bool = True
    priority: int = 5                    # 1 (highest) .. 9
    notes: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Device(SQLModel, table=True):
    """A push destination."""

    __tablename__ = "device"
    __table_args__ = (UniqueConstraint("platform", "token", name="uq_device_token"),)

    id: int | None = Field(default=None, primary_key=True)
    platform: str                            # apns | webpush | ntfy
    token: str                               # device token, or JSON endpoint blob
    label: str = ""
    enabled: bool = True
    created_at: datetime = Field(default_factory=utcnow)
    last_used_at: datetime | None = None
    failure_count: int = 0


class ScanRun(SQLModel, table=True):
    """One pass of the scanner. Useful for spotting a collector that has
    silently started returning zero results because the site changed."""

    __tablename__ = "scan_run"

    id: int | None = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=utcnow, index=True)
    finished_at: datetime | None = None
    trigger: str = "schedule"                # schedule | manual | api

    searches_run: int = 0
    listings_seen: int = 0
    new_listings: int = 0
    price_changes: int = 0
    analyzed: int = 0
    deals_found: int = 0
    alerts_sent: int = 0

    ai_cost_usd: float = 0.0
    errors: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    ok: bool = True


class UserSettings(SQLModel, table=True):
    """Runtime-editable overrides, so she can change the profit bar from her
    phone without redeploying. Single row, id=1."""

    __tablename__ = "user_settings"

    id: int | None = Field(default=1, primary_key=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=utcnow)


class ApiUsage(SQLModel, table=True):
    """Daily AI spend, enforcing the budget cap in AISettings."""

    __tablename__ = "api_usage"

    id: int | None = Field(default=None, primary_key=True)
    day: str = Field(index=True)             # YYYY-MM-DD
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
