"""Deal feed, detail, feedback, and pickup runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..config import Settings
from ..models import (
    Analysis,
    CompSet,
    Deal,
    DealStatus,
    Feedback,
    Listing,
    PriceObservation,
    utcnow,
)
from ..safety import build_brief
from ..scoring import plan_runs
from .deps import get_db, require_token, settings_dep
from .schemas import (
    CompsInfo,
    ConditionInfo,
    DealDetail,
    DealSummary,
    FeedbackIn,
    ManualListingIn,
    MoneyBreakdown,
    RunSummary,
    SafetyInfo,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deals", tags=["deals"], dependencies=[Depends(require_token)])


def _first_image(listing: Listing) -> str | None:
    urls = listing.image_urls or []
    return urls[0] if urls else None


def _to_summary(deal: Deal, listing: Listing, analysis: Analysis | None,
                comps: CompSet | None) -> DealSummary:
    return DealSummary(
        id=deal.id,
        title=listing.title,
        buy_price=deal.buy_price,
        net_profit=deal.net_profit,
        roi_pct=deal.roi_pct,
        resale_estimate=deal.resale_estimate,
        deal_score=deal.deal_score,
        confidence=deal.confidence,
        risk_score=deal.risk_score,
        distance_miles=deal.distance_miles,
        max_worth_driving_miles=deal.max_worth_driving_miles,
        worth_the_drive=deal.worth_the_drive,
        bulk_class=deal.bulk_class,
        condition_grade=(analysis.condition_grade if analysis else "C"),
        location=listing.location_text,
        image_url=_first_image(listing),
        listing_url=listing.url,
        status=deal.status,
        category=listing.category,
        est_days_to_sell=(comps.est_days_to_sell if comps else None),
        warning_count=len(deal.warnings or []),
        created_at=deal.created_at,
        posted_at=listing.posted_at,
    )


@router.get("", response_model=list[DealSummary])
def list_deals(
    session: Session = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    min_profit: float | None = None,
    max_distance: float | None = None,
    category: str | None = None,
    worth_driving_only: bool = True,
    include_dismissed: bool = False,
    hours: int | None = Query(None, description="Only deals found in the last N hours"),
    limit: int = Query(50, le=200),
    offset: int = 0,
    sort: str = Query("score", pattern="^(score|profit|newest|distance|roi)$"),
) -> list[DealSummary]:
    """The feed. Defaults to everything currently actionable, best first."""
    statement = select(Deal, Listing).join(Listing, Deal.listing_id == Listing.id)

    if status_filter:
        statement = statement.where(Deal.status == status_filter)
    elif not include_dismissed:
        # Things she's already dealt with shouldn't keep reappearing.
        statement = statement.where(
            Deal.status.notin_([DealStatus.PASSED.value, DealStatus.EXPIRED.value])
        )

    if min_profit is not None:
        statement = statement.where(Deal.net_profit >= min_profit)
    if max_distance is not None:
        statement = statement.where(Deal.distance_miles <= max_distance)
    if category:
        statement = statement.where(Listing.category == category)
    if worth_driving_only:
        statement = statement.where(Deal.worth_the_drive == True)  # noqa: E712
    if hours:
        statement = statement.where(
            Deal.created_at >= datetime.now(UTC) - timedelta(hours=hours)
        )

    order = {
        "score": Deal.deal_score.desc(),
        "profit": Deal.net_profit.desc(),
        "newest": Deal.created_at.desc(),
        "distance": Deal.distance_miles.asc(),
        "roi": Deal.roi_pct.desc(),
    }[sort]

    rows = session.exec(statement.order_by(order).offset(offset).limit(limit)).all()

    out = []
    for deal, listing in rows:
        analysis = session.get(Analysis, deal.analysis_id) if deal.analysis_id else None
        comps = session.get(CompSet, deal.comp_set_id) if deal.comp_set_id else None
        out.append(_to_summary(deal, listing, analysis, comps))
    return out


@router.get("/runs", response_model=list[RunSummary])
def pickup_runs(
    session: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
    cluster_miles: float = Query(6.0, ge=1.0, le=25.0),
    min_run_size: int = Query(2, ge=2, le=10),
) -> list[RunSummary]:
    """Deals grouped into single drives.

    Batching is where a lot of the real money is: three $80 flips scattered
    across the metro are three separate trips, while the same three clustered
    in Gresham are one afternoon. The trip cost is charged once per run rather
    than once per item, so a run can be worth doing even when its members
    wouldn't be individually.
    """
    rows = session.exec(
        select(Deal, Listing)
        .join(Listing, Deal.listing_id == Listing.id)
        .where(Deal.status.in_([DealStatus.NEW.value, DealStatus.NOTIFIED.value,
                                DealStatus.SAVED.value]))
        .where(Deal.worth_the_drive == True)  # noqa: E712
        .limit(200)
    ).all()

    # A lightweight carrier rather than setting attributes on the Deal rows:
    # SQLModel rejects unknown fields, and mutating live ORM objects to pass
    # data to a pure function invites accidental writes on the next flush.
    @dataclass
    class _Stop:
        id: int
        lat: float | None
        lon: float | None
        net_profit: float
        trip_cost: float
        bulk_class: str

    enriched = [
        _Stop(
            id=deal.id, lat=listing.lat, lon=listing.lon,
            net_profit=deal.net_profit, trip_cost=deal.trip_cost,
            bulk_class=deal.bulk_class,
        )
        for deal, listing in rows
    ]

    runs = plan_runs(
        enriched, settings.trip,
        settings.market.center_lat, settings.market.center_lon,
        cluster_radius_miles=cluster_miles, min_run_size=min_run_size,
    )

    return [
        RunSummary(
            label=run.label,
            center_lat=run.center_lat,
            center_lon=run.center_lon,
            deal_ids=[d.id for d in run.deals],
            deal_count=run.size,
            distance_from_home=round(run.distance_from_home, 1),
            total_net_profit=round(run.total_net_profit, 2),
            profit_after_trip=round(run.profit_after_trip, 2),
            est_hours=round(run.est_hours, 2),
            summary=run.summary(),
        )
        for run in runs
    ]


@router.get("/{deal_id}", response_model=DealDetail)
def get_deal(
    deal_id: int,
    session: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> DealDetail:
    deal = session.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(404, "Deal not found")

    listing = session.get(Listing, deal.listing_id)
    if listing is None:
        raise HTTPException(404, "Listing not found")

    analysis = session.get(Analysis, deal.analysis_id) if deal.analysis_id else None
    comps = session.get(CompSet, deal.comp_set_id) if deal.comp_set_id else None

    history = session.exec(
        select(PriceObservation)
        .where(PriceObservation.listing_id == listing.id)
        .order_by(PriceObservation.observed_at)
    ).all()

    # Only genuine fraud indicators escalate the brief; cosmetic condition
    # notes are passed through as context, not as alarm.
    scam_signals: list[str] = []
    if analysis and analysis.raw_response:
        scam_signals = list(analysis.raw_response.get("additional_scam_signals") or [])
    if analysis and analysis.scam_risk >= 35:
        scam_signals.extend(
            f for f in (analysis.description_red_flags or [])
            if any(k in f.lower() for k in
                   ("zelle", "deposit", "gift card", "ship", "meet", "code",
                    "wire", "paypal", "off-platform", "off platform", "away"))
        )

    brief = build_brief(
        price=deal.buy_price,
        bulk_class=deal.bulk_class,
        scam_risk=(analysis.scam_risk if analysis else 0.0),
        scam_signals=scam_signals,
        red_flags=list(analysis.description_red_flags) if analysis else [],
    )

    summary = _to_summary(deal, listing, analysis, comps)

    checklist = []
    if analysis and analysis.raw_response:
        checklist = list(analysis.raw_response.get("inspection_checklist") or [])

    screenshot = None
    for path in listing.local_images or []:
        if path and path.endswith(".png"):
            screenshot = f"/media/screenshots/{path.rsplit('/', 1)[-1]}"
            break

    return DealDetail(
        **summary.model_dump(),
        description=listing.description or "",
        seller_name=listing.seller_name,
        first_seen_price=listing.first_seen_price,
        money=MoneyBreakdown(
            buy_price=deal.buy_price,
            resale_estimate=deal.resale_estimate,
            resale_low=deal.resale_low,
            resale_high=deal.resale_high,
            gross_spread=deal.gross_spread,
            platform_fees=deal.platform_fees,
            shipping_cost=deal.shipping_cost,
            refurb_cost=deal.refurb_cost,
            trip_cost=deal.trip_cost,
            net_profit=deal.net_profit,
            roi_pct=deal.roi_pct,
            venue=deal.venue,
        ),
        condition=ConditionInfo(
            grade=analysis.condition_grade if analysis else "C",
            score=analysis.condition_score if analysis else 50.0,
            summary=analysis.condition_summary if analysis else "",
            functional_status=analysis.functional_status if analysis else "unknown",
            damage_flags=list(analysis.damage_flags) if analysis else [],
            missing_parts=list(analysis.missing_parts) if analysis else [],
            positive_signals=list(analysis.positive_signals) if analysis else [],
            photo_quality=analysis.photo_quality if analysis else "unknown",
            photo_caveats=list(analysis.photo_caveats) if analysis else [],
            uses_stock_photos=analysis.uses_stock_photos if analysis else False,
            identified_brand=analysis.identified_brand if analysis else None,
            identified_model=analysis.identified_model if analysis else None,
            analyzed_by_ai=bool(analysis and analysis.model_used),
        ),
        comps=CompsInfo(
            estimate_low=comps.estimate_low if comps else 0.0,
            estimate_mid=comps.estimate_mid if comps else 0.0,
            estimate_high=comps.estimate_high if comps else 0.0,
            confidence=comps.confidence if comps else 0.0,
            sample_size=comps.sample_size if comps else 0,
            est_days_to_sell=comps.est_days_to_sell if comps else None,
            method=comps.method if comps else "",
            query_used=comps.query_used if comps else "",
            sources=list(comps.sources) if comps else [],
        ),
        safety=SafetyInfo(**brief.as_dict()),
        reasons=list(deal.reasons or []),
        warnings=list(deal.warnings or []),
        inspection_checklist=checklist,
        image_urls=list(listing.image_urls or []),
        screenshot_url=screenshot,
        price_history=[
            {"price": o.price, "at": o.observed_at.isoformat()} for o in history
        ],
    )


@router.post("/{deal_id}/feedback")
def submit_feedback(
    deal_id: int,
    payload: FeedbackIn,
    session: Session = Depends(get_db),
) -> dict:
    """Record what she actually did.

    This is the loop that makes the tool improve: 'sold' with a real price
    feeds `comps/internal.calibration_factor`, which corrects every future
    estimate in that category. Without it, the same estimate errors repeat
    forever.
    """
    deal = session.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(404, "Deal not found")

    valid = {"saved", "passed", "bought", "sold", "dud"}
    if payload.action not in valid:
        raise HTTPException(400, f"action must be one of {sorted(valid)}")

    session.add(
        Feedback(
            deal_id=deal.id,
            listing_id=deal.listing_id,
            action=payload.action,
            actual_buy_price=payload.actual_buy_price,
            actual_sale_price=payload.actual_sale_price,
            actual_days_to_sell=payload.actual_days_to_sell,
            sold_venue=payload.sold_venue,
            note=payload.note,
        )
    )

    deal.status = {
        "saved": DealStatus.SAVED.value,
        "passed": DealStatus.PASSED.value,
        "bought": DealStatus.BOUGHT.value,
        "sold": DealStatus.SOLD.value,
        "dud": DealStatus.SOLD.value,
    }[payload.action]
    session.add(deal)
    session.commit()

    response = {"ok": True, "deal_id": deal.id, "status": deal.status}

    if payload.actual_sale_price and deal.resale_estimate:
        error_pct = (
            (payload.actual_sale_price - deal.resale_estimate) / deal.resale_estimate * 100
        )
        response["estimate_error_pct"] = round(error_pct, 1)
        response["note"] = (
            f"Estimated ${deal.resale_estimate:,.0f}, actually sold for "
            f"${payload.actual_sale_price:,.0f} ({error_pct:+.0f}%). "
            "Future estimates in this category will be corrected."
        )
    return response


@router.post("/manual")
async def submit_manual(
    payload: ManualListingIn,
    settings: Settings = Depends(settings_dep),
) -> dict:
    """Queue a pasted listing for the next scan.

    Covers the case the scanner can't: standing in front of something at an
    estate sale and wanting to know in thirty seconds whether it's worth
    buying.
    """
    from ..collectors import get_manual_collector, parse_pasted_text

    if not (payload.url or payload.text):
        raise HTTPException(400, "provide a url or some listing text")

    listing = parse_pasted_text(
        payload.text or "", url=payload.url, title=payload.title,
        price=payload.price, location=payload.location,
    )
    get_manual_collector(settings).submit(listing)

    return {
        "ok": True,
        "queued": {
            "title": listing.title,
            "price": listing.price,
            "source": listing.source,
            "location": listing.location_text,
        },
        "note": "Queued. Run a scan (or wait for the next one) to score it.",
    }


@router.post("/expire-old")
def expire_old(
    session: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90),
) -> dict:
    """Retire deals whose listings have gone away."""
    cutoff = utcnow() - timedelta(days=days)
    rows = session.exec(
        select(Deal, Listing)
        .join(Listing, Deal.listing_id == Listing.id)
        .where(Deal.status.in_([DealStatus.NEW.value, DealStatus.NOTIFIED.value]))
        .where(Deal.created_at < cutoff)
    ).all()

    expired = 0
    for deal, listing in rows:
        if not listing.is_active:
            deal.status = DealStatus.EXPIRED.value
            session.add(deal)
            expired += 1

    session.commit()
    return {"expired": expired}
