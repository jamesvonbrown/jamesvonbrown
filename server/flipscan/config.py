"""All tunable behaviour lives here.

Every value can be overridden with an environment variable (or a `.env` file)
using the `FLIPSCAN_` prefix, and nested values use `__`:

    FLIPSCAN_MARKET__CENTER_LAT=45.5152
    FLIPSCAN_TRIP__COST_PER_MILE=0.42

The per-user tunables (profit bar, categories, radius) are ALSO editable at
runtime from the phone via `/api/settings` — those live in the database and
override what's here. This module supplies the defaults and the deploy-time
secrets.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


def _parse_str_list(value):
    """Accept either a comma-separated string or a JSON array.

    NoDecode (used on the list fields below) switches off pydantic-settings'
    automatic JSON parsing, which is what makes `FOO=a,b` work — but it also
    means a JSON value arrives here as a raw string. Left unhandled, that
    silently produces `['["a"', '"b"]']` rather than an error, so both forms
    are parsed explicitly.
    """
    if not isinstance(value, str):
        return value

    text = value.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except (json.JSONDecodeError, ValueError):
            pass  # fall through and treat it as comma-separated

    return [part.strip() for part in text.split(",") if part.strip()]


# --------------------------------------------------------------------------
# Market: where she's shopping
# --------------------------------------------------------------------------
class MarketSettings(BaseModel):
    """The geographic market being scanned. Defaults to Portland, OR."""

    name: str = "Portland, OR"
    center_lat: float = 45.5152
    center_lon: float = -122.6784

    # Facebook's own search radius, in miles. This is the widest net we cast;
    # the per-deal radius logic below decides what's actually worth driving to.
    # FB only accepts a fixed set of values.
    search_radius_miles: int = 60

    # Facebook's internal city id for the market. Optional — the collector
    # falls back to lat/lon search when this is unset.
    fb_location_id: str | None = None

    @field_validator("search_radius_miles")
    @classmethod
    def _snap_to_fb_allowed(cls, v: int) -> int:
        allowed = [1, 2, 5, 10, 20, 40, 60, 80, 100, 250, 500]
        return min(allowed, key=lambda a: abs(a - v))


# --------------------------------------------------------------------------
# Trip economics: the "how far is it worth driving" model
# --------------------------------------------------------------------------
class TripSettings(BaseModel):
    """Turns a dollar figure into a drive radius.

    The question isn't "how far will I drive" in the abstract — it's "does
    this trip pay for itself?" A round trip costs gas, wear, and an hour of
    your life. We compute the largest radius where that cost stays under a
    fraction of the expected profit, so a $2,000 spread earns a long drive
    and a $40 flip stays in the neighborhood. That is exactly the behaviour
    you'd get from a tiered table, but it degrades sensibly at every dollar
    figure in between instead of jumping at the tier boundaries.
    """

    # Vehicle + time costs.
    cost_per_mile: float = 0.35          # gas + wear, close to the IRS rate
    average_speed_mph: float = 32.0      # Portland metro surface streets + I-5
    hourly_time_value: float = 25.00     # what an hour of her time is worth

    # Never spend more than this share of the expected profit getting there.
    max_trip_cost_fraction: float = 0.25

    # Hard clamps, so the model can't produce something absurd.
    min_radius_miles: float = 5.0
    max_radius_miles: float = 60.0

    # Small items are worth batching: several pickups on one loop divides the
    # trip cost. Keyed by bulk class (see scoring/radius.py).
    expected_batch_size: dict[str, float] = Field(
        default_factory=lambda: {
            "pocket": 4.0,      # phones, game consoles, jewelry
            "box": 2.5,         # power tools, small appliances, bike parts
            "two_person": 1.0,  # dressers, mowers, e-bikes
            "truck": 1.0,       # couches, sheds, appliances
        }
    )

    # Fixed surcharge for items that need a truck or a second set of hands.
    bulk_fixed_cost: dict[str, float] = Field(
        default_factory=lambda: {
            "pocket": 0.0,
            "box": 0.0,
            "two_person": 15.0,   # helper / hassle premium
            "truck": 60.0,        # truck rental or borrowed-truck favour
        }
    )


# --------------------------------------------------------------------------
# Profit bar: what counts as a deal
# --------------------------------------------------------------------------
class ProfitSettings(BaseModel):
    """Thresholds a listing must clear before it's worth a notification."""

    # A deal must clear BOTH an absolute floor and a percentage return.
    # The floor stops $8 profits on $12 items; the ROI stops thin margins on
    # expensive items where you're tying up a lot of cash.
    min_net_profit: float = 60.0
    min_roi_pct: float = 45.0

    # Above this profit, relax the ROI requirement — a $900 profit at 30% ROI
    # is a very good day even though it fails the default percentage bar.
    high_value_profit_override: float = 500.0
    high_value_min_roi_pct: float = 25.0

    # Don't tie up more than this in one item, regardless of margin.
    max_buy_price: float = 2500.0
    min_buy_price: float = 15.0

    # Composite score (0-100) below which we stay quiet even if the math works.
    # Catches things that pencil out but look risky in the photos.
    min_deal_score: float = 55.0

    # Hard block, independent of how good the margin looks. A listing that
    # reads as a scam is not a deal at any price — the downside isn't a bad
    # flip, it's meeting a stranger with cash in your pocket.
    max_scam_risk: float = 70.0


# --------------------------------------------------------------------------
# Platform fees: what you actually keep
# --------------------------------------------------------------------------
class FeeSettings(BaseModel):
    """Selling costs by resale venue. Percentages are of the sale price."""

    venues: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            # Local cash sale — no fee, but slower and needs a meetup.
            "facebook_local": {"pct": 0.0, "flat": 0.0},
            "facebook_shipping": {"pct": 5.0, "flat": 0.40},
            "ebay": {"pct": 13.25, "flat": 0.40},
            "mercari": {"pct": 10.0, "flat": 0.50},
            "offerup_shipping": {"pct": 12.9, "flat": 0.30},
            "craigslist": {"pct": 0.0, "flat": 0.0},
            "poshmark": {"pct": 20.0, "flat": 0.0},
        }
    )

    default_venue: str = "facebook_local"

    # Consumables when shipping: box, tape, label, filler.
    shipping_supplies_cost: float = 3.50

    # Typical cleanup cost so an item shows well: cleaner, a bulb, a belt,
    # touch-up paint. Scales with condition grade in scoring/fees.py.
    refurb_cost_by_grade: dict[str, float] = Field(
        default_factory=lambda: {
            "A": 0.0, "B": 8.0, "C": 25.0, "D": 60.0, "F": 0.0,
        }
    )


# --------------------------------------------------------------------------
# Scanning cadence + politeness
# --------------------------------------------------------------------------
class ScanSettings(BaseModel):
    """How often we look, and how hard we're willing to lean on a source."""

    interval_minutes: int = 60

    # Randomised offset so we never hit the source at exactly :00 every hour.
    jitter_seconds: int = 420

    # Hard ceilings per scan. These exist to keep the tool a personal shopping
    # assistant rather than a bulk harvester — see docs/LEGAL.md.
    max_listings_per_scan: int = 400
    max_searches_per_scan: int = 25
    max_detail_fetches_per_scan: int = 60

    # Seconds to wait between page actions, randomised within the range.
    delay_between_actions: tuple[float, float] = (1.8, 4.5)

    # Skip listings we've already scored unless the price moved by this much.
    reprice_threshold_pct: float = 8.0

    # Stop notifying about a listing after this many alerts.
    max_alerts_per_listing: int = 2

    # Quiet hours (local time, 24h). No pushes during these hours; deals are
    # queued and delivered at the end of the window.
    quiet_hours_start: int = 22
    quiet_hours_end: int = 7
    timezone: str = "America/Los_Angeles"


# --------------------------------------------------------------------------
# AI analysis
# --------------------------------------------------------------------------
class AISettings(BaseModel):
    """Claude usage for photo grading, description parsing, and comp research."""

    model: str = "claude-opus-5"

    # A cheaper pass for the first-stage triage over every listing, keeping the
    # expensive model for listings that survive the initial price screen.
    triage_model: str = "claude-haiku-4-5"

    effort: str = "medium"

    # Photos sent to the vision grader per listing. More photos = better read
    # on condition, but each one costs tokens.
    max_images_per_listing: int = 4

    # Longest edge in pixels before upload. Listing photos are often 2000px+;
    # 1024 is plenty to spot scratches and cracks and cuts token cost sharply.
    image_max_edge_px: int = 1024

    # Rough daily ceiling on analysis spend, in USD. The pipeline stops calling
    # the API for the rest of the day when this is hit and logs a warning.
    daily_budget_usd: float = 3.00

    # Let Claude use web search when structured comp sources come up empty.
    enable_web_research: bool = True


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
class NotifySettings(BaseModel):
    """Where deal alerts go. ntfy is the default: free, instant, no Apple
    Developer account, and it works on an iPhone in about five minutes."""

    # Comma-separated in env: FLIPSCAN_NOTIFY__CHANNELS=ntfy,webpush
    #
    # NoDecode is required. Without it pydantic-settings treats any list field
    # as JSON and calls json.loads("ntfy,webpush") before the validator below
    # ever runs, which raises at import time — so the app won't start at all
    # rather than falling back to a default.
    channels: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["ntfy"]
    )

    # ntfy.sh — pick a long unguessable topic; anyone who knows it can read
    # your alerts. See docs/SETUP.md.
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str | None = None
    ntfy_token: str | None = None

    # Web Push (works for the installed PWA on iOS 16.4+). Generate keys with
    # `flipscan vapid-keys`.
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_contact_email: str | None = None

    # APNs — only needed for the native SwiftUI build.
    apns_key_id: str | None = None
    apns_team_id: str | None = None
    apns_bundle_id: str = "com.flipscan.app"
    apns_key_path: str | None = None
    apns_use_sandbox: bool = True

    # Twilio SMS, as a backup channel for very high-value finds only.
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from: str | None = None
    twilio_to: str | None = None
    sms_min_profit: float = 400.0

    # Don't send more than this many pushes per scan; the rest go to the feed.
    max_alerts_per_scan: int = 6

    @field_validator("channels", mode="before")
    @classmethod
    def _split_csv(cls, v):
        return _parse_str_list(v)


# --------------------------------------------------------------------------
# Data sources
# --------------------------------------------------------------------------
class SourceSettings(BaseModel):
    """Credentials and switches for where listings and comps come from."""

    # Which collectors run each scan. NoDecode for the same reason as
    # NotifySettings.channels — see the note there.
    collectors: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["facebook"]
    )

    # Browser profile dir for the logged-in Marketplace session. Persisted so
    # she logs in once. Never commit this directory — it holds session cookies.
    browser_profile_dir: str = str(REPO_ROOT / "data" / "browser-profile")
    browser_headless: bool = True

    # eBay Browse API — free developer keys, gives active-listing comps.
    ebay_client_id: str | None = None
    ebay_client_secret: str | None = None
    ebay_marketplace: str = "EBAY_US"

    # eBay Marketplace Insights gives real SOLD prices, which are far better
    # comps than asking prices, but access requires a separate application.
    ebay_has_insights_access: bool = False

    @field_validator("collectors", mode="before")
    @classmethod
    def _split_csv(cls, v):
        return _parse_str_list(v)


# --------------------------------------------------------------------------
# Root
# --------------------------------------------------------------------------
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLIPSCAN_",
        env_nested_delimiter="__",
        env_file=(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Shared secret the phone sends as `Authorization: Bearer <token>`.
    # Generated on first run if unset — see cli.py.
    api_token: str | None = None

    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'flipscan.db'}"
    media_dir: str = str(REPO_ROOT / "data" / "media")

    host: str = "0.0.0.0"
    port: int = 8000

    # Public base URL, used to build image links inside push notifications.
    public_base_url: str = "http://localhost:8000"

    anthropic_api_key: str | None = None

    log_level: str = "INFO"

    market: MarketSettings = Field(default_factory=MarketSettings)
    trip: TripSettings = Field(default_factory=TripSettings)
    profit: ProfitSettings = Field(default_factory=ProfitSettings)
    fees: FeeSettings = Field(default_factory=FeeSettings)
    scan: ScanSettings = Field(default_factory=ScanSettings)
    ai: AISettings = Field(default_factory=AISettings)
    notify: NotifySettings = Field(default_factory=NotifySettings)
    sources: SourceSettings = Field(default_factory=SourceSettings)

    def ensure_dirs(self) -> None:
        Path(self.media_dir).mkdir(parents=True, exist_ok=True)
        Path(self.sources.browser_profile_dir).mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite:///"):
            Path(self.database_url[len("sqlite:///"):]).parent.mkdir(
                parents=True, exist_ok=True
            )

    def redacted(self) -> dict:
        """Config dump safe to show in the API / logs."""
        secret_markers = ("key", "token", "secret", "password")
        raw = json.loads(self.model_dump_json())

        def scrub(node):
            if isinstance(node, dict):
                return {
                    k: ("***set***" if v and any(m in k.lower() for m in secret_markers)
                        else scrub(v))
                    for k, v in node.items()
                }
            if isinstance(node, list):
                return [scrub(v) for v in node]
            return node

        return scrub(raw)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
