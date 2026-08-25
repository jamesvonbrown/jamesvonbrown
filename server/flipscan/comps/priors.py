"""Category priors — the fallback when real comps come up empty.

A prior is not a comp and is never treated as one: anything valued this way
carries deliberately low confidence, which flows straight through to the deal
score. The point is to keep a genuinely unusual item from being silently
dropped just because eBay had nothing, while making sure it can't sail
through on an unverified guess either.

Two numbers per category:

* `retention` — what a good used example fetches as a fraction of new retail.
* `days_to_sell` — how long a fairly priced one typically sits locally.

Both are calibrated against real outcomes over time by `internal.py`, so
these starting values matter less the longer the tool runs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryPrior:
    retention: float          # used value / new retail
    days_to_sell: int         # typical local time-to-sale
    markup_over_ask: float    # what a well-listed resale gets vs a rushed FB ask
    note: str = ""


# Retention figures reflect what secondhand goods actually do, not sticker
# depreciation. Power tools barely move; televisions fall off a cliff.
CATEGORY_PRIORS: dict[str, CategoryPrior] = {
    "tools": CategoryPrior(0.62, 10, 1.75,
        "Brand-name cordless tools hold value better than almost anything "
        "else. Batteries carry a large share of it."),
    "furniture": CategoryPrior(0.42, 21, 2.10,
        "Solid wood and known designers hold; particleboard is worthless. "
        "The spread comes from sellers who need the space back."),
    "bikes": CategoryPrior(0.45, 18, 1.85,
        "Frame size drives price more than components. Seasonal: strong "
        "March-September in Portland."),
    "electronics": CategoryPrior(0.50, 7, 1.55,
        "Fast turns, thin margins, high fraud risk. Verify serials and "
        "activation locks in person."),
    "appliances": CategoryPrior(0.35, 25, 2.20,
        "Big spreads, but only if it runs. Never buy one you haven't seen "
        "power on."),
    "outdoor": CategoryPrior(0.52, 16, 1.90,
        "Premium brands hold hard. Ships well, which opens the national "
        "market."),
    "baby": CategoryPrior(0.48, 12, 1.80,
        "Constant churn and motivated sellers. Never resell car seats."),
    "lawn": CategoryPrior(0.44, 20, 1.95,
        "Sharply seasonal. Small engines need to be started before buying."),
    "sporting": CategoryPrior(0.45, 20, 1.85),
    "musical": CategoryPrior(0.58, 30, 1.70,
        "Holds value well but sells slowly. Brand is everything."),
    "jewelry": CategoryPrior(0.35, 40, 2.00,
        "Authentication risk is high and the buyer pool is small."),
    "clothing": CategoryPrior(0.25, 35, 2.50,
        "Only worth it for premium brands. Slow, and it's a volume game."),
    "mixed": CategoryPrior(0.45, 21, 1.90),
}

DEFAULT_PRIOR = CategoryPrior(0.45, 21, 1.85)


def get_prior(category: str | None) -> CategoryPrior:
    return CATEGORY_PRIORS.get((category or "").lower(), DEFAULT_PRIOR)


def prior_estimate(
    asking_price: float,
    category: str | None,
    retail_new: float = 0.0,
    anchor_price: float = 0.0,
) -> tuple[float, float, float, str]:
    """(low, mid, high, method) with no comps available.

    Prefers a known new-retail price, which anchors on what the item is
    actually worth. Falls back to reasoning from the asking price, which is
    much weaker — an underpriced listing and a fairly priced one look
    identical from the ask alone, so the band is left wide on purpose.

    `anchor_price` is the highest price the seller has asked. It matters more
    than it looks: with no comps, the estimate is a multiple of the ask, so a
    seller cutting $180 to $120 would drag the *estimated resale value* down
    with it and make a better deal score worse. A price cut is the seller
    conceding, not the item depreciating, so the original ask is the honest
    anchor for what the item is worth.
    """
    prior = get_prior(category)
    anchor = max(asking_price, anchor_price or 0.0)

    if retail_new > 0:
        mid = retail_new * prior.retention
        method = f"prior: {prior.retention:.0%} of ${retail_new:,.0f} new retail"
        spread = 0.30
    else:
        mid = anchor * prior.markup_over_ask
        if anchor > asking_price:
            method = (
                f"prior: {prior.markup_over_ask:.2f}x the original ${anchor:,.0f} "
                f"asking price, before the seller's price cut "
                f"({category or 'general'} category)"
            )
        else:
            method = (
                f"prior: {prior.markup_over_ask:.2f}x the asking price "
                f"({category or 'general'} category)"
            )
        # Wider band: this is the weakest evidence the system produces.
        spread = 0.42

    return (
        round(mid * (1 - spread), 2),
        round(mid, 2),
        round(mid * (1 + spread), 2),
        method,
    )
