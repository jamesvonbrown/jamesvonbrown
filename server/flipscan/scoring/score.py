"""The composite deal score.

A single 0-100 number that answers "should I get in the car?", built from
six signals and then docked for risk. The point of splitting it up is that
the app can show *why* a deal scored what it did, which is the difference
between a tool she trusts and a tool she second-guesses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..config import Settings
from .fees import SellingCosts, estimate_selling_costs, net_from_sale, pick_venue, roi_pct
from .radius import TripEconomics, evaluate_trip

# Signal weights. They sum to 1.0; the risk penalty is applied afterwards
# because risk should be able to kill an otherwise perfect-looking deal.
WEIGHTS = {
    "margin": 0.32,      # how much money, in absolute and percentage terms
    "safety": 0.16,      # how wrong can the comp be before this loses money
    "confidence": 0.15,  # how much do we trust the comp at all
    "condition": 0.15,   # what shape is it in
    "velocity": 0.11,    # how fast does it turn
    "distance": 0.11,    # how comfortably inside the worth-driving radius
}

MAX_RISK_PENALTY = 45.0


@dataclass
class ScoreBreakdown:
    """Per-signal detail, surfaced in the app so the score is auditable."""

    margin: float = 0.0
    safety: float = 0.0
    confidence: float = 0.0
    condition: float = 0.0
    velocity: float = 0.0
    distance: float = 0.0
    risk_penalty: float = 0.0
    momentum_bonus: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "margin": round(self.margin, 3),
            "safety": round(self.safety, 3),
            "confidence": round(self.confidence, 3),
            "condition": round(self.condition, 3),
            "velocity": round(self.velocity, 3),
            "distance": round(self.distance, 3),
            "risk_penalty": round(self.risk_penalty, 2),
            "momentum_bonus": round(self.momentum_bonus, 2),
        }


@dataclass
class ScoredDeal:
    """Everything needed to write a Deal row and render a notification."""

    buy_price: float
    resale_estimate: float
    resale_low: float
    resale_high: float
    venue: str

    gross_spread: float
    platform_fees: float
    shipping_cost: float
    refurb_cost: float
    trip_cost: float
    net_profit: float
    roi_pct: float

    deal_score: float
    risk_score: float
    confidence: float

    distance_miles: float
    max_worth_driving_miles: float
    worth_the_drive: bool
    bulk_class: str

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    passes_filters: bool = False
    reject_reason: str | None = None


# --------------------------------------------------------------------------
# Individual signals — each returns 0.0-1.0
# --------------------------------------------------------------------------
def _margin_signal(net_profit: float, roi: float, settings: Settings) -> float:
    """Full marks at twice the profit bar and twice the ROI bar."""
    p = settings.profit
    profit_part = min(1.0, max(0.0, net_profit / max(1.0, 2 * p.min_net_profit)))
    roi_part = min(1.0, max(0.0, roi / max(1.0, 2 * p.min_roi_pct)))
    return 0.6 * profit_part + 0.4 * roi_part


def _safety_signal(resale_estimate: float, breakeven_sale: float) -> float:
    """How far the comp can fall before the deal stops making money.

    This is deliberately not the same thing as margin. A $400 profit on a
    $2,000 item has a thin cushion — a 20% comp error wipes it out. A $120
    profit on a $200 item survives being badly wrong.
    """
    if resale_estimate <= 0:
        return 0.0
    cushion = (resale_estimate - breakeven_sale) / resale_estimate
    return min(1.0, max(0.0, cushion / 0.40))


def _velocity_signal(est_days_to_sell: int | None) -> float:
    """Fast turns are worth more than slow ones at the same margin."""
    if est_days_to_sell is None:
        return 0.5  # unknown: neither reward nor punish
    return min(1.0, max(0.08, math.exp(-(est_days_to_sell - 7) / 60.0)))


def _condition_signal(condition_score: float, functional_status: str) -> float:
    base = min(1.0, max(0.0, condition_score / 100.0))
    if functional_status == "for_parts":
        base *= 0.35
    elif functional_status == "partial":
        base *= 0.6
    elif functional_status == "untested":
        base *= 0.82
    return base


def _distance_signal(trip: TripEconomics) -> float:
    """Rewards deals comfortably inside the radius, not just barely inside."""
    if trip.max_worth_driving <= 0:
        return 0.0
    ratio = trip.distance_miles / trip.max_worth_driving
    if ratio > 1.0:
        return 0.0
    if ratio <= 0.33:
        return 1.0
    # Linear from 1.0 at a third of the radius down to 0.3 at the limit.
    return 1.0 - (ratio - 0.33) * (0.7 / 0.67)


def _risk_penalty(
    analysis, comp_sample_size: int, location_confident: bool,
    warnings: list[str],
) -> float:
    """Points docked for everything that could make this go wrong."""
    penalty = 0.0

    scam = getattr(analysis, "scam_risk", 0.0) or 0.0
    if scam > 0:
        penalty += (scam / 100.0) * 25.0
        if scam >= 50:
            warnings.append(f"Scam risk {scam:.0f}/100 — verify carefully before travelling.")

    if getattr(analysis, "authenticity_concern", False):
        penalty += 8.0
        warnings.append("Possible counterfeit — authenticate before paying.")

    if getattr(analysis, "uses_stock_photos", False):
        penalty += 6.0
        warnings.append("Listing uses stock photos — you can't see the real item's condition.")

    status = getattr(analysis, "functional_status", "unknown")
    if status == "for_parts":
        penalty += 10.0
        warnings.append("Sold for parts / not working.")
    elif status == "partial":
        penalty += 6.0
        warnings.append("Partially working — confirm exactly what's broken.")
    elif status == "untested":
        penalty += 3.0
        warnings.append("Seller says untested — test it before handing over cash.")

    flags = list(getattr(analysis, "description_red_flags", []) or [])
    if flags:
        penalty += min(10.0, 2.0 * len(flags))
        warnings.extend(f"Listing says: {f}" for f in flags[:4])

    missing = list(getattr(analysis, "missing_parts", []) or [])
    if missing:
        penalty += min(6.0, 2.0 * len(missing))
        warnings.append("Missing: " + ", ".join(missing[:3]))

    if comp_sample_size < 3:
        penalty += 5.0
        warnings.append(
            f"Only {comp_sample_size} comparable sale(s) found — the resale "
            "estimate is a guess, not a number."
        )

    if not location_confident:
        penalty += 3.0
        warnings.append("Couldn't pin the seller's location — distance is approximate.")

    return min(MAX_RISK_PENALTY, penalty)


def _momentum_bonus(price: float, first_seen_price: float, warnings: list[str],
                    reasons: list[str]) -> float:
    """A seller who keeps cutting the price is a seller who wants it gone."""
    if not first_seen_price or first_seen_price <= price:
        return 0.0
    drop_pct = (first_seen_price - price) / first_seen_price * 100.0
    if drop_pct < 5:
        return 0.0
    reasons.append(
        f"Price cut {drop_pct:.0f}% (${first_seen_price:,.0f} → ${price:,.0f}) — "
        "seller is motivated."
    )
    return min(5.0, drop_pct / 8.0)


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------
def score_listing(
    *,
    buy_price: float,
    resale_low: float,
    resale_mid: float,
    resale_high: float,
    comp_confidence: float,
    comp_sample_size: int,
    est_days_to_sell: int | None,
    distance_miles: float,
    bulk_class: str,
    analysis,
    settings: Settings,
    first_seen_price: float | None = None,
    location_confident: bool = True,
    preferred_venue: str | None = None,
) -> ScoredDeal:
    """Score one listing end to end.

    `analysis` is duck-typed — anything exposing the Analysis model's fields
    works, including a neutral stand-in when photo analysis hasn't run yet,
    so the pipeline can score on price alone and enrich later.
    """
    reasons: list[str] = []
    warnings: list[str] = []

    condition_grade = getattr(analysis, "condition_grade", "C") or "C"
    condition_score = getattr(analysis, "condition_score", 50.0)
    functional_status = getattr(analysis, "functional_status", "unknown")
    cond_multiplier = getattr(analysis, "resale_condition_multiplier", 1.0) or 1.0

    # Condition moves what it sells for, not what it's worth in the abstract.
    adj_mid = resale_mid * cond_multiplier
    adj_low = resale_low * cond_multiplier
    adj_high = resale_high * cond_multiplier

    venue = pick_venue(bulk_class, adj_mid, settings.fees, preferred_venue)
    costs: SellingCosts = estimate_selling_costs(
        sale_price=adj_mid,
        venue=venue,
        bulk_class=bulk_class,
        condition_grade=condition_grade,
        settings=settings.fees,
    )

    # Trip cost depends on profit, and profit depends on trip cost. Resolve it
    # by computing the pre-trip profit first, using that to size the radius,
    # then charging the real distance.
    profit_before_trip = adj_mid - buy_price - costs.total
    trip = evaluate_trip(distance_miles, profit_before_trip, bulk_class, settings.trip)

    net = net_from_sale(adj_mid, buy_price, costs, trip.trip_cost)
    roi = roi_pct(net, buy_price, costs, trip.trip_cost)
    breakeven_sale = buy_price + costs.total + trip.trip_cost

    bd = ScoreBreakdown(
        margin=_margin_signal(net, roi, settings),
        safety=_safety_signal(adj_mid, breakeven_sale),
        confidence=min(1.0, max(0.0, comp_confidence)),
        condition=_condition_signal(condition_score, functional_status),
        velocity=_velocity_signal(est_days_to_sell),
        distance=_distance_signal(trip),
    )
    bd.risk_penalty = _risk_penalty(analysis, comp_sample_size, location_confident, warnings)
    bd.momentum_bonus = _momentum_bonus(buy_price, first_seen_price or 0.0, warnings, reasons)

    raw = sum(getattr(bd, k) * w for k, w in WEIGHTS.items()) * 100.0
    score = max(0.0, min(100.0, raw - bd.risk_penalty + bd.momentum_bonus))

    # ---- Human-readable justification -------------------------------------
    reasons.insert(
        0,
        f"Buy ${buy_price:,.0f} → sells for about ${adj_mid:,.0f} "
        f"(${adj_low:,.0f}–${adj_high:,.0f})",
    )
    reasons.append(
        f"Net ${net:,.0f} after ${costs.total:,.0f} of selling costs and "
        f"${trip.trip_cost:,.0f} of driving — {roi:.0f}% ROI"
    )
    reasons.append(trip.explain())
    if condition_grade in ("A", "B"):
        reasons.append(f"Condition looks like a {condition_grade} — {getattr(analysis, 'condition_summary', '') or 'clean example'}")
    if est_days_to_sell is not None and est_days_to_sell <= 14:
        reasons.append(f"Typically moves in about {est_days_to_sell} days.")
    if comp_confidence >= 0.7 and comp_sample_size >= 5:
        reasons.append(f"Estimate backed by {comp_sample_size} comparable sales.")

    # ---- Hard filters ------------------------------------------------------
    p = settings.profit
    passes, reject = True, None

    scam = getattr(analysis, "scam_risk", 0.0) or 0.0
    if scam >= p.max_scam_risk:
        # Checked before the money filters on purpose: no margin justifies
        # driving to meet someone the listing itself says is a problem.
        passes, reject = False, f"scam risk {scam:.0f}/100 is at or over the {p.max_scam_risk:.0f} block"
    elif buy_price > p.max_buy_price:
        passes, reject = False, f"asking ${buy_price:,.0f} is over the ${p.max_buy_price:,.0f} cap"
    elif buy_price < p.min_buy_price and buy_price > 0:
        passes, reject = False, f"asking ${buy_price:,.0f} is below the ${p.min_buy_price:,.0f} floor"
    elif net < p.min_net_profit:
        passes, reject = False, f"${net:,.0f} net is under the ${p.min_net_profit:,.0f} bar"
    elif not trip.worth_it:
        passes, reject = False, (
            f"{distance_miles:.0f} mi exceeds the {trip.max_worth_driving:.0f} mi "
            "this profit justifies"
        )
    else:
        # High-value deals get a relaxed ROI bar: a $900 profit at 30% is a
        # very good day even though it fails the default percentage test.
        required_roi = (
            p.high_value_min_roi_pct if net >= p.high_value_profit_override
            else p.min_roi_pct
        )
        if roi < required_roi:
            passes, reject = False, f"{roi:.0f}% ROI is under the {required_roi:.0f}% bar"
        elif score < p.min_deal_score:
            passes, reject = False, f"score {score:.0f} is under the {p.min_deal_score:.0f} bar"

    return ScoredDeal(
        buy_price=buy_price,
        resale_estimate=adj_mid,
        resale_low=adj_low,
        resale_high=adj_high,
        venue=venue,
        gross_spread=adj_mid - buy_price,
        platform_fees=costs.platform_fee,
        shipping_cost=costs.shipping + costs.supplies,
        refurb_cost=costs.refurb,
        trip_cost=trip.trip_cost,
        net_profit=net,
        roi_pct=roi,
        deal_score=score,
        risk_score=bd.risk_penalty / MAX_RISK_PENALTY * 100.0,
        confidence=comp_confidence,
        distance_miles=distance_miles,
        max_worth_driving_miles=trip.max_worth_driving,
        worth_the_drive=trip.worth_it,
        bulk_class=bulk_class,
        reasons=reasons,
        warnings=warnings,
        breakdown=bd,
        passes_filters=passes,
        reject_reason=reject,
    )
