"""Comps from our own data — and the feedback loop that makes it improve.

Two sources nobody else has:

* **Local sale outcomes.** Every Marketplace listing we've watched that
  disappeared without a price cut probably sold at its asking price. That is
  a direct read on what the *Portland* market pays, which is the market she
  actually sells into — not eBay's national average.
* **Her own results.** When she records what she paid and what it sold for,
  that's ground truth. Nothing else comes close.

The calibration function at the bottom is the part that compounds. If the
estimates for furniture have been running 15% high across her last dozen
sales, every future furniture estimate gets corrected by that factor. A tool
that doesn't do this repeats the same errors forever.
"""

from __future__ import annotations

import logging
import statistics
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from ..models import Deal, Feedback, Listing
from .base import CompProvider, CompResult, CompSample, relevance_score, summarize

log = logging.getLogger(__name__)

# A watched listing that vanishes this fast almost certainly sold rather than
# being withdrawn — nobody lists a couch and pulls it in under a day.
MIN_HOURS_BEFORE_ASSUMED_SOLD = 18


class InternalCompProvider(CompProvider):
    """Comps from listings we've already watched and sales she's recorded."""

    name = "internal"
    weight = 1.6  # local truth, weighted below eBay sold only for sample size

    def __init__(self, session: Session, lookback_days: int = 120):
        self.session = session
        self.lookback_days = lookback_days

    async def lookup(self, query: str, *, category: str | None = None,
                     hint_price: float = 0.0) -> CompResult:
        cutoff = datetime.now(UTC) - timedelta(days=self.lookback_days)

        # Listings that went away — our proxy for "sold locally".
        statement = (
            select(Listing)
            .where(Listing.is_active == False)  # noqa: E712 — SQL, not Python
            .where(Listing.delisted_at != None)  # noqa: E711
            .where(Listing.first_seen_at >= cutoff)
        )
        if category:
            statement = statement.where(Listing.category == category)

        samples: list[CompSample] = []
        for listing in self.session.exec(statement.limit(400)).all():
            if not listing.delisted_at or not listing.price:
                continue
            alive = listing.delisted_at - listing.first_seen_at
            if alive < timedelta(hours=MIN_HOURS_BEFORE_ASSUMED_SOLD):
                continue
            samples.append(
                CompSample(
                    title=listing.title,
                    price=listing.price,
                    url=listing.url,
                    sold=True,
                    sold_date=listing.delisted_at.date().isoformat(),
                    condition="local marketplace",
                )
            )

        # Her actual sales outrank everything; add them twice so the median
        # leans toward reality rather than toward inferred outcomes.
        for feedback, listing in self.session.exec(
            select(Feedback, Listing)
            .join(Listing, Feedback.listing_id == Listing.id)
            .where(Feedback.actual_sale_price != None)  # noqa: E711
            .where(Feedback.created_at >= cutoff)
            .limit(200)
        ).all():
            sample = CompSample(
                title=listing.title,
                price=float(feedback.actual_sale_price or 0),
                url=listing.url,
                sold=True,
                sold_date=feedback.created_at.date().isoformat(),
                condition="YOUR actual sale",
            )
            samples.extend([sample, sample])

        if not samples:
            return CompResult(provider=self.name, query_used=query,
                              error="no local history yet")

        result = summarize(
            self.name, query, samples,
            min_relevance=0.68,  # stricter: the local pool is small and noisy
            note=f"{len(samples)} local outcome(s) in the last {self.lookback_days} days",
        )

        # Time-to-sell straight from how long these actually sat.
        if result.ok:
            durations = []
            for sample in result.samples:
                listing = self.session.exec(
                    select(Listing).where(Listing.url == sample.url)
                ).first()
                if listing and listing.delisted_at:
                    durations.append((listing.delisted_at - listing.first_seen_at).days)
            if durations:
                result.est_days_to_sell = max(1, int(statistics.median(durations)))

        return result


# --------------------------------------------------------------------------
# Calibration
# --------------------------------------------------------------------------
def calibration_factor(
    session: Session,
    category: str | None = None,
    min_samples: int = 4,
) -> tuple[float, int, str]:
    """How wrong have our estimates been lately? (factor, n, explanation)

    Compares the resale estimate on each deal against what it actually sold
    for, and returns the correction. A factor of 0.85 means estimates have
    been running 15% high and future ones should be pulled down.

    Returns 1.0 until there's enough evidence — a single unlucky sale should
    not reshape the model.
    """
    statement = (
        select(Feedback, Deal)
        .join(Deal, Feedback.deal_id == Deal.id)
        .where(Feedback.actual_sale_price != None)  # noqa: E711
        .where(Feedback.action.in_(["sold", "dud"]))
    )
    rows = session.exec(statement.limit(300)).all()

    ratios: list[float] = []
    for feedback, deal in rows:
        if category:
            listing = session.get(Listing, feedback.listing_id)
            if not listing or listing.category != category:
                continue
        if deal.resale_estimate and feedback.actual_sale_price:
            ratios.append(float(feedback.actual_sale_price) / float(deal.resale_estimate))

    if len(ratios) < min_samples:
        return 1.0, len(ratios), (
            f"not enough sales yet to calibrate ({len(ratios)}/{min_samples})"
        )

    # Median, then clamped: even with real data, a correction beyond ±35%
    # is more likely a change in what she's buying than a systematic bias.
    factor = max(0.65, min(1.35, statistics.median(ratios)))
    direction = "high" if factor < 1 else "low"
    scope = category or "all categories"
    return factor, len(ratios), (
        f"{scope}: estimates running {abs(1 - factor):.0%} {direction} "
        f"across {len(ratios)} recorded sales — correcting by {factor:.2f}x"
    )


def dedupe_against_history(
    session: Session, title: str, price: float, days: int = 30
) -> Listing | None:
    """Have we already seen essentially this listing recently?

    Catches relists: a seller who takes a listing down and reposts it at the
    same price gets a new external id, and without this she'd be notified
    about the same couch every week.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    candidates = session.exec(
        select(Listing)
        .where(Listing.first_seen_at >= cutoff)
        .where(Listing.price >= price * 0.85)
        .where(Listing.price <= price * 1.15)
        .limit(300)
    ).all()

    for candidate in candidates:
        if relevance_score(title, candidate.title) >= 0.90:
            return candidate
    return None
