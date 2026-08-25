"""Engine, sessions, schema creation, and the settings-merge layer."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from .config import Settings, get_settings
from .models import UserSettings, Watchlist, utcnow

log = logging.getLogger(__name__)

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        s = get_settings()
        connect_args: dict[str, Any] = {}
        if s.database_url.startswith("sqlite"):
            # The scheduler thread and the API threads share one engine.
            connect_args["check_same_thread"] = False
        _engine = create_engine(
            s.database_url,
            echo=False,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        if s.database_url.startswith("sqlite"):
            _enable_sqlite_pragmas(_engine)
    return _engine


def _enable_sqlite_pragmas(engine: Engine) -> None:
    """WAL keeps the API readable while a scan is writing."""

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session. Commits on clean exit, rolls back on error."""
    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with Session(get_engine()) as session:
        yield session


def init_db(seed: bool = True) -> None:
    SQLModel.metadata.create_all(get_engine())
    if seed:
        seed_watchlists()


# --------------------------------------------------------------------------
# Runtime settings overlay
# --------------------------------------------------------------------------
# Deploy-time config lives in env vars; the handful of knobs she'll actually
# want to change from the couch live in the DB and win over the env defaults.
OVERRIDABLE = {
    "profit.min_net_profit",
    "profit.min_roi_pct",
    "profit.max_buy_price",
    "profit.min_buy_price",
    "profit.min_deal_score",
    "profit.high_value_profit_override",
    "profit.high_value_min_roi_pct",
    "trip.min_radius_miles",
    "trip.max_radius_miles",
    "trip.cost_per_mile",
    "trip.hourly_time_value",
    "trip.max_trip_cost_fraction",
    "scan.interval_minutes",
    "scan.quiet_hours_start",
    "scan.quiet_hours_end",
    "notify.max_alerts_per_scan",
    "fees.default_venue",
    "market.center_lat",
    "market.center_lon",
    "market.search_radius_miles",
}


def load_overrides(session: Session) -> dict[str, Any]:
    row = session.get(UserSettings, 1)
    return dict(row.data) if row and row.data else {}


def save_overrides(session: Session, updates: dict[str, Any]) -> dict[str, Any]:
    """Merge `updates` into the stored overrides. Unknown keys are rejected so
    a typo from the client can't silently do nothing forever."""
    unknown = set(updates) - OVERRIDABLE
    if unknown:
        raise ValueError(f"not overridable: {sorted(unknown)}")

    row = session.get(UserSettings, 1)
    if row is None:
        row = UserSettings(id=1, data={})
        session.add(row)

    merged = dict(row.data or {})
    merged.update(updates)
    row.data = merged
    row.updated_at = utcnow()
    # SQLModel/SQLAlchemy won't see an in-place dict mutation; reassigning the
    # attribute above is what marks the column dirty.
    session.add(row)
    return merged


def effective_settings(session: Session | None = None) -> Settings:
    """Env-file settings with the DB overrides applied on top."""
    base = get_settings()
    if session is None:
        return base

    overrides = load_overrides(session)
    if not overrides:
        return base

    patched = base.model_copy(deep=True)
    for dotted, value in overrides.items():
        section, _, field = dotted.partition(".")
        try:
            if field:
                setattr(getattr(patched, section), field, value)
            else:
                setattr(patched, section, value)
        except (AttributeError, ValueError) as exc:
            log.warning("ignoring bad settings override %s=%r (%s)", dotted, value, exc)
    return patched


# --------------------------------------------------------------------------
# Seed data
# --------------------------------------------------------------------------
# Starting watchlists chosen for the Portland market specifically: a wet,
# outdoorsy, bike-and-tools city with a lot of home renovation, a big
# secondhand furniture culture, and no sales tax to distort pricing.
#
# `value_retention_hint` is the fraction of a category's typical new price
# that a good used example holds — used as a weak prior only when real comps
# come back thin.
SEED_WATCHLISTS: list[dict] = [
    # -- Tools: the reseller's bread and butter. Brand-name tools barely
    #    depreciate, sell in days, and people constantly liquidate them.
    dict(name="DeWalt / Milwaukee tools", query="dewalt milwaukee tool lot",
         category="tools", min_price=40, max_price=900, bulk_class="box",
         value_retention_hint=0.62, priority=1,
         notes="Cordless kits and bare tools. Check for the battery — a kit "
               "without batteries is worth far less than the photo suggests."),
    dict(name="Makita / Festool", query="makita festool", category="tools",
         min_price=50, max_price=1500, bulk_class="box",
         value_retention_hint=0.65, priority=2),
    dict(name="Table saw / miter saw", query="table saw miter saw",
         category="tools", min_price=75, max_price=1200, bulk_class="truck",
         value_retention_hint=0.55, priority=3),
    dict(name="Generators / pressure washers", query="generator pressure washer",
         category="tools", min_price=80, max_price=1200, bulk_class="two_person",
         value_retention_hint=0.5, priority=4,
         notes="Small engines: ask when it last ran. Old fuel gums a carb and "
               "that's a real repair, not a wipe-down."),

    # -- Bikes: Portland is a cycling city; good bikes move fast year-round.
    dict(name="Road & gravel bikes", query="road bike gravel bike carbon",
         category="bikes", min_price=100, max_price=2500, bulk_class="two_person",
         value_retention_hint=0.45, priority=2,
         notes="Frame size drives price more than components. A 56cm sells; a "
               "48cm or 62cm sits."),
    dict(name="E-bikes", query="electric bike ebike", category="bikes",
         min_price=200, max_price=3000, bulk_class="truck",
         value_retention_hint=0.42, priority=3,
         notes="Battery health is the whole ballgame. A dead pack can cost "
               "$400-800 to replace and often can't be sourced at all."),

    # -- Outdoor gear: high margin, easy to ship, and Portland is full of it.
    dict(name="Camping & backpacking gear", query="backpacking tent sleeping bag arcteryx patagonia",
         category="outdoor", min_price=30, max_price=800, bulk_class="box",
         value_retention_hint=0.5, priority=2),
    dict(name="Snowboards / skis", query="snowboard skis burton", category="outdoor",
         min_price=50, max_price=900, bulk_class="two_person",
         value_retention_hint=0.4, priority=5,
         notes="Strongly seasonal — buy in April, sell in November."),

    # -- Furniture: heavy, but the spreads are enormous and locals underprice
    #    real mid-century pieces constantly.
    dict(name="Mid-century / solid wood furniture",
         query="mid century modern teak walnut dresser credenza",
         category="furniture", min_price=50, max_price=1500, bulk_class="truck",
         value_retention_hint=0.7, priority=1,
         notes="Look for dovetail joints and a maker's stamp in the drawer. "
               "Veneer over particleboard is not worth the truck."),
    dict(name="Herman Miller / Steelcase chairs",
         query="herman miller aeron steelcase leap chair",
         category="furniture", min_price=80, max_price=1200, bulk_class="two_person",
         value_retention_hint=0.55, priority=1,
         notes="Aerons are the single most reliable flip in this category. "
               "Size B is the common one; check the cylinder holds height."),

    # -- Appliances: big spreads, but verify it runs before you load it.
    dict(name="Washer / dryer sets", query="washer dryer set", category="appliances",
         min_price=100, max_price=900, bulk_class="truck",
         value_retention_hint=0.4, priority=6,
         notes="Only buy if you can see it run. 'Worked when removed' means "
               "it doesn't work."),

    # -- Electronics: fast turns, but verify everything and beware fakes.
    dict(name="Apple: MacBook / iPad", query="macbook ipad", category="electronics",
         min_price=100, max_price=2000, bulk_class="pocket",
         value_retention_hint=0.55, priority=1,
         notes="Check Activation Lock and iCloud sign-out in person. A locked "
               "device is worth parts value only."),
    dict(name="Game consoles", query="playstation xbox nintendo switch",
         category="electronics", min_price=40, max_price=700, bulk_class="pocket",
         value_retention_hint=0.6, priority=2),
    dict(name="Cameras & lenses", query="canon nikon sony camera lens dslr",
         category="electronics", min_price=60, max_price=2000, bulk_class="pocket",
         value_retention_hint=0.55, priority=3,
         notes="Check the lens for fungus and the sensor for dust. Shutter "
               "count matters on bodies."),

    # -- Baby gear: constant churn, motivated sellers, strong local demand.
    dict(name="Strollers & baby gear", query="stroller uppababy nuna bugaboo doona",
         category="baby", min_price=50, max_price=900, bulk_class="two_person",
         value_retention_hint=0.5, priority=3,
         notes="Never resell a car seat — expiry dates and recall liability "
               "make it a legal headache, not a flip."),

    # -- Lawn & garden: seasonal spike March-September in the Willamette Valley.
    dict(name="Mowers & yard equipment", query="lawn mower chainsaw leaf blower stihl honda",
         category="lawn", min_price=50, max_price=800, bulk_class="two_person",
         value_retention_hint=0.45, priority=5),

    # -- Broad sweeps that catch the mispriced-because-they-just-want-it-gone
    #    listings the targeted searches miss.
    dict(name="Moving / estate liquidation", query="moving sale must go estate",
         category="mixed", min_price=20, max_price=1500, bulk_class="box",
         priority=2,
         notes="Deadline-driven sellers are where the real spreads live."),
    dict(name="Free & curb alert", query="free curb alert", category="mixed",
         min_price=0, max_price=1, bulk_class="two_person", priority=7,
         notes="Zero cost basis. Even a modest resale is pure margin, but "
               "it's first-come and you'll lose most of them."),
]


def seed_watchlists() -> None:
    """Insert the starter watchlists once, on an empty table."""
    with session_scope() as session:
        existing = session.exec(select(Watchlist).limit(1)).first()
        if existing:
            return
        for entry in SEED_WATCHLISTS:
            session.add(Watchlist(**entry))
        log.info("seeded %d starter watchlists", len(SEED_WATCHLISTS))
