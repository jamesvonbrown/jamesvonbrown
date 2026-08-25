"""The hourly scan.

Cost is the design constraint. Running the vision model over every listing an
hourly scan turns up would cost roughly $70/day, which is absurd for a
business whose whole point is margin. So the scan is staged, and each stage is
more expensive and sees far fewer listings than the one before it:

    1. collect                     free      ~400 listings
    2. dedupe + text screen        free      ~400  ->  ~60 survive
    3. comps lookup                free-ish   ~60  ->  ~15 look viable
    4. photo analysis (Claude)     paid       ~15  ->  the ones worth alerting
    5. final score + notify        free

Every stage can only *remove* listings, and each one rejects on the cheapest
sufficient evidence. A listing whose asking price can't clear the profit bar
even under generous assumptions is dropped in stage 2 for nothing, and never
costs a model call.

Net effect: about $0.30-0.80 a day instead of $70, with the expensive analysis
spent only on listings she might actually drive to.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from .comps import EbayCompProvider, WebResearchCompProvider, estimate_value
from .comps.priors import get_prior
from .config import Settings
from .db import effective_settings, session_scope
from .enrich import analyze_description, analyze_listing, neutral_analysis
from .geo import driving_miles, resolve_place
from .models import (
    Analysis,
    ApiUsage,
    CompSet,
    Deal,
    DealStatus,
    Listing,
    PriceObservation,
    ScanRun,
    Watchlist,
    utcnow,
)
from .notify import DealAlert, broadcast, build_notifiers, in_quiet_hours
from .scoring import classify_bulk, score_listing

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
def today_key() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def get_usage(session: Session) -> ApiUsage:
    day = today_key()
    row = session.exec(select(ApiUsage).where(ApiUsage.day == day)).first()
    if row is None:
        row = ApiUsage(day=day)
        session.add(row)
        session.flush()
    return row


def budget_remaining(session: Session, settings: Settings) -> float:
    return max(0.0, settings.ai.daily_budget_usd - get_usage(session).cost_usd)


def record_usage(session: Session, cost: float, in_tok: int, out_tok: int) -> None:
    row = get_usage(session)
    row.calls += 1
    row.input_tokens += in_tok
    row.output_tokens += out_tok
    row.cost_usd += cost
    session.add(row)


# --------------------------------------------------------------------------
# Stage 2 — the free screen
# --------------------------------------------------------------------------
# Generous multiplier on the category prior. The screen's job is to reject
# only what could not possibly work, so it errs heavily toward keeping things:
# a false reject here is a missed deal that nothing downstream can recover.
OPTIMISTIC_FACTOR = 1.45

# Assumed resale for a free item, by how hard it is to move. Free listings
# have no asking price to reason from, and passing on all of them would skip
# the highest-ROI category there is.
FREE_ITEM_OPTIMISTIC = {
    "pocket": 120.0, "box": 160.0, "two_person": 280.0, "truck": 400.0,
}


def quick_screen(
    listing, findings, settings: Settings, distance_miles: float, bulk: str
) -> tuple[bool, str]:
    """Could this listing possibly be worth buying? Costs nothing to ask."""
    p = settings.profit

    if findings.scam_risk >= p.max_scam_risk:
        return False, f"scam risk {findings.scam_risk:.0f}"

    if listing.price > p.max_buy_price:
        return False, f"${listing.price:,.0f} over the ${p.max_buy_price:,.0f} cap"

    if 0 < listing.price < p.min_buy_price:
        return False, f"${listing.price:,.0f} under the ${p.min_buy_price:,.0f} floor"

    if listing.price > 0:
        prior = get_prior(getattr(listing, "category_hint", None))
        optimistic = listing.price * prior.markup_over_ask * OPTIMISTIC_FACTOR
    else:
        optimistic = FREE_ITEM_OPTIMISTIC.get(bulk, 160.0)

    # Assume the cheapest plausible cost structure, since the point is to see
    # whether the listing survives its *best* case.
    optimistic_net = optimistic - listing.price - (0.05 * optimistic)

    if optimistic_net < p.min_net_profit:
        return False, (
            f"best case ${optimistic_net:,.0f} can't reach the "
            f"${p.min_net_profit:,.0f} bar"
        )

    # Even generously, is it too far to be worth collecting?
    max_possible = settings.trip.max_radius_miles
    if distance_miles > max_possible:
        return False, f"{distance_miles:.0f} mi is beyond the {max_possible:.0f} mi limit"

    return True, ""


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------
def upsert_listing(
    session: Session, raw, settings: Settings
) -> tuple[Listing, bool, bool]:
    """Store or update one observed listing.

    Returns (row, is_new, price_changed).
    """
    existing = session.exec(
        select(Listing)
        .where(Listing.source == raw.source)
        .where(Listing.external_id == raw.external_id)
    ).first()

    lat, lon, confident = resolve_place(
        raw.location_text, (settings.market.center_lat, settings.market.center_lon)
    )
    distance = driving_miles(
        settings.market.center_lat, settings.market.center_lon, lat, lon
    )
    bulk = classify_bulk(raw.title, raw.description)

    if existing is None:
        row = Listing(
            source=raw.source,
            external_id=raw.external_id,
            fingerprint=raw.fingerprint(),
            url=raw.url,
            title=raw.title,
            description=raw.description or "",
            price=raw.price,
            first_seen_price=raw.price,
            currency=raw.currency,
            location_text=raw.location_text,
            lat=lat, lon=lon,
            distance_miles=distance,
            location_confident=confident,
            posted_at=raw.posted_at,
            category=raw.category_hint,
            bulk_class=bulk,
            seller_name=raw.seller_name,
            seller_url=raw.seller_url,
            image_urls=list(raw.image_urls),
            local_images=[raw.screenshot_path] if raw.screenshot_path else [],
            raw=dict(raw.raw or {}),
        )
        session.add(row)
        session.flush()
        session.add(PriceObservation(listing_id=row.id, price=raw.price))
        return row, True, False

    price_changed = abs(existing.price - raw.price) > 0.01
    if price_changed:
        session.add(PriceObservation(listing_id=existing.id, price=raw.price))
        existing.price = raw.price

    existing.last_seen_at = utcnow()
    existing.times_seen += 1
    existing.is_active = True
    existing.delisted_at = None
    if raw.image_urls and not existing.image_urls:
        existing.image_urls = list(raw.image_urls)
    if raw.screenshot_path and raw.screenshot_path not in (existing.local_images or []):
        existing.local_images = [*(existing.local_images or []), raw.screenshot_path]

    session.add(existing)
    return existing, False, price_changed


def mark_stale_listings(session: Session, hours: int = 30) -> int:
    """Flag listings we stopped seeing as gone.

    A listing that disappears is a listing that sold, which is exactly the
    local price evidence `comps/internal.py` learns from — so this quiet piece
    of bookkeeping is what makes the local comps get better over time.
    """
    cutoff = utcnow() - timedelta(hours=hours)
    stale = session.exec(
        select(Listing)
        .where(Listing.is_active == True)  # noqa: E712
        .where(Listing.last_seen_at < cutoff)
    ).all()

    for listing in stale:
        listing.is_active = False
        listing.delisted_at = listing.last_seen_at
        session.add(listing)
    return len(stale)


# --------------------------------------------------------------------------
# The scan
# --------------------------------------------------------------------------
async def run_scan(
    settings: Settings | None = None,
    *,
    trigger: str = "manual",
    collectors: list | None = None,
    notify: bool = True,
    force_reanalyze: bool = False,
) -> ScanRun:
    """One complete pass. Always returns a ScanRun, even on failure."""
    from .collectors import build_collectors

    with session_scope() as session:
        settings = settings or effective_settings(session)
        run = ScanRun(trigger=trigger)
        session.add(run)
        session.flush()
        run_id = run.id

        watchlists = session.exec(
            select(Watchlist).where(Watchlist.enabled == True)  # noqa: E712
        ).all()
        known_ids = {
            row.external_id
            for row in session.exec(
                select(Listing).where(Listing.last_seen_at >= utcnow() - timedelta(days=3))
            ).all()
        }
        remaining_budget = budget_remaining(session, settings)

    collectors = collectors if collectors is not None else build_collectors(settings)
    errors: list[str] = []
    stats = dict(searches=0, seen=0, new=0, price_changes=0, analyzed=0,
                 deals=0, alerts=0, cost=0.0)

    # ---- stage 1: collect --------------------------------------------------
    raw_listings = []
    limits = {
        "max_searches": settings.scan.max_searches_per_scan,
        "max_listings": settings.scan.max_listings_per_scan,
        "max_details": settings.scan.max_detail_fetches_per_scan,
        "known_external_ids": known_ids,
        # Cast a wider net on a cold database so there's something to look at
        # on day one; after that, only fresh listings matter.
        "days_since_listed": 1 if known_ids else 7,
    }

    for collector in collectors:
        try:
            result = await collector.collect(watchlists, limits)
            raw_listings.extend(result.listings)
            stats["searches"] += result.searches_run
            errors.extend(result.errors)
            for note in result.notes:
                log.info("[%s] %s", collector.name, note)
        except Exception as exc:
            log.exception("collector %s failed", collector.name)
            errors.append(f"{collector.name}: {exc}")

    stats["seen"] = len(raw_listings)

    # ---- stage 2: persist + free screen ------------------------------------
    candidates: list[int] = []

    with session_scope() as session:
        for raw in raw_listings:
            if not raw.is_usable():
                continue
            try:
                row, is_new, price_changed = upsert_listing(session, raw, settings)
            except Exception as exc:
                errors.append(f"upsert {raw.external_id}: {exc}")
                continue

            stats["new"] += int(is_new)
            stats["price_changes"] += int(price_changed)

            if not (is_new or force_reanalyze):
                # Only revisit a known listing when the price moved enough to
                # change the answer.
                if not price_changed:
                    continue
                drop = abs(row.first_seen_price - row.price) / max(1.0, row.first_seen_price)
                if drop * 100 < settings.scan.reprice_threshold_pct:
                    continue

            findings = analyze_description(
                row.title, row.description, row.price, row.category
            )
            keep, reason = quick_screen(
                row, findings, settings, row.distance_miles or 0.0, row.bulk_class
            )
            if not keep:
                log.debug("screened out %r: %s", row.title[:50], reason)
                continue

            candidates.append(row.id)

        stats["stale"] = mark_stale_listings(session)

    log.info(
        "stage 2: %d listings -> %d candidates (%.0f%% screened out for free)",
        stats["seen"], len(candidates),
        100 * (1 - len(candidates) / max(1, stats["seen"])),
    )

    # ---- stage 3: comps ----------------------------------------------------
    ebay = EbayCompProvider(settings)
    research = WebResearchCompProvider(settings)
    shortlist: list[dict] = []

    try:
        for listing_id in candidates:
            with session_scope() as session:
                listing = session.get(Listing, listing_id)
                if listing is None:
                    continue

                try:
                    valuation = await estimate_value(
                        listing, settings, session=session, ebay=ebay,
                        research=research,
                        # Research costs money; hold it back until the free
                        # comps have had their turn on a listing worth it.
                        allow_research=remaining_budget > 0.25,
                    )
                except Exception as exc:
                    errors.append(f"comps {listing_id}: {exc}")
                    continue

                comp_set = CompSet(
                    listing_id=listing.id,
                    query_used=valuation.query_used,
                    estimate_low=valuation.low,
                    estimate_mid=valuation.mid,
                    estimate_high=valuation.high,
                    confidence=valuation.confidence,
                    sample_size=valuation.sample_size,
                    est_days_to_sell=valuation.est_days_to_sell,
                    sources=valuation.sources,
                    method=valuation.method,
                )
                session.add(comp_set)
                session.flush()

                # Score on price and comps alone, with condition held neutral.
                # Anything that fails here would fail with photo analysis too,
                # so there's no reason to pay for the photos.
                provisional = score_listing(
                    buy_price=listing.price,
                    resale_low=valuation.low,
                    resale_mid=valuation.mid,
                    resale_high=valuation.high,
                    comp_confidence=valuation.confidence,
                    comp_sample_size=valuation.sample_size,
                    est_days_to_sell=valuation.est_days_to_sell,
                    distance_miles=listing.distance_miles or 0.0,
                    bulk_class=listing.bulk_class,
                    analysis=neutral_analysis(),
                    settings=settings,
                    first_seen_price=listing.first_seen_price,
                    location_confident=listing.location_confident,
                )

                if provisional.passes_filters:
                    shortlist.append({
                        "listing_id": listing.id,
                        "comp_set_id": comp_set.id,
                        "valuation": valuation,
                    })
                else:
                    log.debug("comps rejected %r: %s",
                              listing.title[:50], provisional.reject_reason)
    finally:
        await ebay.close()

    log.info("stage 3: %d candidates -> %d shortlisted", len(candidates), len(shortlist))

    # ---- stage 4: photo analysis (the expensive part) ----------------------
    # Best-looking deals first, so a budget ceiling truncates the marginal
    # ones rather than whatever happened to be scored last.
    shortlist.sort(key=lambda s: s["valuation"].mid, reverse=True)

    scored: list[dict] = []
    for entry in shortlist:
        with session_scope() as session:
            listing = session.get(Listing, entry["listing_id"])
            if listing is None:
                continue
            remaining_budget = budget_remaining(session, settings)

            raw_stub = _listing_to_raw_stub(listing)
            analysis_result = await analyze_listing(
                raw_stub, settings, budget_remaining=remaining_budget
            )

            if analysis_result.used_ai:
                record_usage(
                    session, analysis_result.cost_usd,
                    analysis_result.input_tokens, analysis_result.output_tokens,
                )
                stats["cost"] += analysis_result.cost_usd
                stats["analyzed"] += 1
            elif analysis_result.error and "budget" in analysis_result.error:
                errors.append("daily AI budget hit — remaining listings scored on text only")

            analysis_row = Analysis(**analysis_result.to_model_kwargs(listing.id))
            session.add(analysis_row)
            session.flush()

            # Photo analysis often produces a better comp query than the title
            # did; re-run the comps when it materially disagrees.
            valuation = entry["valuation"]
            comp_set_id = entry["comp_set_id"]
            better_query = analysis_result.comp_query
            if better_query and better_query.lower() != valuation.query_used.lower():
                try:
                    revised = await estimate_value(
                        listing, settings, session=session,
                        analysis=analysis_result, ebay=ebay, research=research,
                        allow_research=False,
                    )
                    if revised.ok and revised.confidence > valuation.confidence:
                        valuation = revised
                        comp_set = CompSet(
                            listing_id=listing.id,
                            query_used=revised.query_used,
                            estimate_low=revised.low, estimate_mid=revised.mid,
                            estimate_high=revised.high, confidence=revised.confidence,
                            sample_size=revised.sample_size,
                            est_days_to_sell=revised.est_days_to_sell,
                            sources=revised.sources,
                            method=revised.method + " (re-run after photo ID)",
                        )
                        session.add(comp_set)
                        session.flush()
                        comp_set_id = comp_set.id
                except Exception as exc:
                    log.debug("comp re-run failed: %s", exc)

            final = score_listing(
                buy_price=listing.price,
                resale_low=valuation.low,
                resale_mid=valuation.mid,
                resale_high=valuation.high,
                comp_confidence=valuation.confidence,
                comp_sample_size=valuation.sample_size,
                est_days_to_sell=valuation.est_days_to_sell,
                distance_miles=listing.distance_miles or 0.0,
                bulk_class=listing.bulk_class,
                analysis=analysis_result,
                settings=settings,
                first_seen_price=listing.first_seen_price,
                location_confident=listing.location_confident,
            )

            if not final.passes_filters:
                log.debug("photo analysis rejected %r: %s",
                          listing.title[:50], final.reject_reason)
                continue

            deal = Deal(
                listing_id=listing.id,
                comp_set_id=comp_set_id,
                analysis_id=analysis_row.id,
                buy_price=final.buy_price,
                resale_estimate=final.resale_estimate,
                resale_low=final.resale_low,
                resale_high=final.resale_high,
                venue=final.venue,
                gross_spread=final.gross_spread,
                platform_fees=final.platform_fees,
                shipping_cost=final.shipping_cost,
                refurb_cost=final.refurb_cost,
                trip_cost=final.trip_cost,
                net_profit=final.net_profit,
                roi_pct=final.roi_pct,
                deal_score=final.deal_score,
                risk_score=final.risk_score,
                confidence=final.confidence,
                distance_miles=final.distance_miles,
                max_worth_driving_miles=final.max_worth_driving_miles,
                worth_the_drive=final.worth_the_drive,
                bulk_class=final.bulk_class,
                reasons=final.reasons,
                warnings=final.warnings,
            )
            session.add(deal)
            session.flush()
            stats["deals"] += 1

            scored.append({
                "deal_id": deal.id,
                "listing_id": listing.id,
                "net_profit": final.net_profit,
                "deal_score": final.deal_score,
            })

    log.info("stage 4: %d shortlisted -> %d deals ($%.3f of AI spend)",
             len(shortlist), stats["deals"], stats["cost"])

    # ---- stage 5: notify ---------------------------------------------------
    if notify and scored:
        try:
            stats["alerts"] = await _send_alerts(settings, scored)
        except Exception as exc:
            log.exception("notification stage failed")
            errors.append(f"notify: {exc}")

    # ---- close out ---------------------------------------------------------
    with session_scope() as session:
        run = session.get(ScanRun, run_id)
        run.finished_at = utcnow()
        run.searches_run = stats["searches"]
        run.listings_seen = stats["seen"]
        run.new_listings = stats["new"]
        run.price_changes = stats["price_changes"]
        run.analyzed = stats["analyzed"]
        run.deals_found = stats["deals"]
        run.alerts_sent = stats["alerts"]
        run.ai_cost_usd = stats["cost"]
        run.errors = errors[:40]
        run.ok = not errors
        session.add(run)
        # Flush before snapshotting. `session.refresh()` would re-read the row
        # from the database and silently discard everything just assigned,
        # which is how this returned a run full of zeros the first time.
        session.flush()
        detached = ScanRun(**run.model_dump())

    for collector in collectors:
        try:
            await collector.close()
        except Exception:
            pass

    return detached


def _listing_to_raw_stub(listing: Listing):
    """Adapt a stored Listing to what the analyser expects."""
    from .collectors.base import RawListing

    return RawListing(
        source=listing.source,
        external_id=listing.external_id,
        url=listing.url,
        title=listing.title,
        price=listing.price,
        description=listing.description,
        location_text=listing.location_text,
        image_urls=list(listing.image_urls or []),
        category_hint=listing.category,
    )


async def _send_alerts(settings: Settings, scored: list[dict]) -> int:
    """Push the best finds, respecting quiet hours and the per-scan cap."""
    quiet = in_quiet_hours(
        settings.scan.quiet_hours_start,
        settings.scan.quiet_hours_end,
        settings.scan.timezone,
    )

    with session_scope() as session:
        from .models import Device

        devices = session.exec(select(Device).where(Device.enabled == True)).all()  # noqa: E712
        webpush_subs, apns_tokens = [], []
        for device in devices:
            if device.platform == "webpush":
                import json
                try:
                    webpush_subs.append(json.loads(device.token))
                except Exception:
                    pass
            elif device.platform == "apns":
                apns_tokens.append(device.token)

    notifiers = build_notifiers(
        settings, webpush_subscriptions=webpush_subs, apns_tokens=apns_tokens
    )
    if not notifiers:
        return 0

    scored.sort(key=lambda s: (s["deal_score"], s["net_profit"]), reverse=True)
    sent = 0

    for entry in scored[: settings.notify.max_alerts_per_scan]:
        with session_scope() as session:
            deal = session.get(Deal, entry["deal_id"])
            listing = session.get(Listing, entry["listing_id"])
            if not deal or not listing:
                continue

            if deal.alerts_sent >= settings.scan.max_alerts_per_listing:
                continue

            if quiet and deal.net_profit < 500:
                # Held, not dropped: it stays NEW and goes out on the first
                # scan after the quiet window closes.
                log.info("quiet hours — holding alert for %r", listing.title[:40])
                continue

            alert = DealAlert(
                deal_id=deal.id,
                title=listing.title,
                buy_price=deal.buy_price,
                net_profit=deal.net_profit,
                roi_pct=deal.roi_pct,
                resale_estimate=deal.resale_estimate,
                distance_miles=deal.distance_miles,
                deal_score=deal.deal_score,
                confidence=deal.confidence,
                listing_url=listing.url,
                app_url=f"{settings.public_base_url}/app/#/deal/{deal.id}",
                image_url=(listing.image_urls or [""])[0],
                location=listing.location_text or "",
                reasons=list(deal.reasons or []),
                warnings=list(deal.warnings or []),
            )

            results = await broadcast(notifiers, alert)
            if any(r.sent for r in results):
                sent += 1
                deal.alerts_sent += 1
                deal.status = DealStatus.NOTIFIED.value
                deal.notified_at = utcnow()
                session.add(deal)

            for result in results:
                for error in result.errors:
                    log.warning("notify[%s]: %s", result.channel, error)

        # Spread pushes out slightly so six alerts don't arrive as one
        # indistinguishable buzz.
        await asyncio.sleep(random.uniform(0.4, 1.1))

    for notifier in notifiers:
        try:
            await notifier.close()
        except Exception:
            pass

    return sent
