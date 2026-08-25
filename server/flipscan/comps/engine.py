"""Blending several comp sources into one number with an honest error bar.

Providers are tried cheapest-first and the expensive ones are skipped once
the cheap ones have produced a confident answer. That ordering is the whole
cost-control strategy for valuation: eBay and the local history are free, and
web research costs a model call, so research only runs when the free sources
have genuinely failed *and* the listing is worth the spend.

When sources disagree, the disagreement itself is the finding. Two providers
1.6x apart don't average into a good estimate — they average into a confident-
looking wrong one. So a wide spread widens the band and cuts confidence, which
flows through the deal score and usually keeps the listing quiet.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field

from sqlmodel import Session

from ..collectors.base import title_tokens
from ..config import Settings
from .base import CompResult
from .ebay import EbayCompProvider
from .internal import InternalCompProvider, calibration_factor
from .priors import get_prior, prior_estimate
from .research import WebResearchCompProvider

log = logging.getLogger(__name__)

# Above this, the free providers are trusted and research is skipped.
CONFIDENCE_SKIP_RESEARCH = 0.62

# Research costs a model call; only spend it when the item could actually
# clear the profit bar. Below this asking price it isn't worth the money.
RESEARCH_MIN_ASKING = 60.0


@dataclass
class Valuation:
    """The blended answer, with everything needed to explain it."""

    low: float = 0.0
    mid: float = 0.0
    high: float = 0.0
    confidence: float = 0.0
    sample_size: int = 0
    est_days_to_sell: int | None = None
    sell_through_pct: float | None = None

    query_used: str = ""
    method: str = ""
    sources: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    calibration_applied: float = 1.0

    @property
    def ok(self) -> bool:
        return self.mid > 0


def build_comp_query(listing, analysis=None) -> str:
    """The search string most likely to return genuine comparables.

    A model that has seen the photos writes a much better query than the
    title does — it knows the listing titled "office chair, great shape" is
    an Aeron size B — so its suggestion wins whenever it's available.
    """
    if analysis is not None:
        suggested = getattr(analysis, "comp_query", "") or getattr(
            analysis, "suggested_comp_query", ""
        )
        if suggested and len(suggested.strip()) > 4:
            return suggested.strip()

        brand = getattr(analysis, "identified_brand", "") or ""
        model = getattr(analysis, "identified_model", "") or ""
        if brand and model:
            return f"{brand} {model}".strip()

    # Fall back to the identifying words of the title, minus the noise.
    tokens = title_tokens(listing.title, keep=7, price=listing.price)
    return " ".join(tokens) if tokens else listing.title[:60]


def _blend(results: list[CompResult]) -> tuple[float, float, float, float, int]:
    """Weighted combination of provider answers -> (low, mid, high, conf, n)."""
    usable = [r for r in results if r.ok]
    if not usable:
        return 0.0, 0.0, 0.0, 0.0, 0

    weights, mids = [], []
    for result in usable:
        base = result.weight_hint if result.weight_hint is not None else _provider_weight(result.provider)
        # Confidence is part of the weight: a provider that isn't sure of its
        # own answer shouldn't pull the blend toward it.
        weights.append(max(0.05, base * max(0.1, result.confidence)))
        mids.append(result.median)

    total = sum(weights)
    mid = sum(m * w for m, w in zip(mids, weights, strict=True)) / total
    low = sum(r.low * w for r, w in zip(usable, weights, strict=True)) / total
    high = sum(r.high * w for r, w in zip(usable, weights, strict=True)) / total

    confidence = max(r.confidence for r in usable)
    if len(usable) > 1:
        spread = (max(mids) - min(mids)) / max(1e-6, statistics.fmean(mids))
        if spread <= 0.20:
            # Independent sources agreeing is real evidence, not a coincidence.
            confidence = min(1.0, confidence * 1.15)
        elif spread >= 0.45:
            confidence *= 0.65
            low = min(low, min(mids) * 0.9)
            high = max(high, max(mids) * 1.1)

    return (
        round(low, 2),
        round(mid, 2),
        round(high, 2),
        round(min(1.0, confidence), 3),
        sum(r.sample_size for r in usable),
    )


_PROVIDER_WEIGHTS = {
    "ebay_sold": 2.4,     # somebody actually paid this
    "internal": 1.6,      # the local market, small sample
    "ebay_active": 1.0,   # asking prices, discounted
    "web_research": 1.0,
    "prior": 0.35,        # a guess with a category attached
}


def _provider_weight(name: str) -> float:
    return _PROVIDER_WEIGHTS.get(name, 1.0)


async def estimate_value(
    listing,
    settings: Settings,
    *,
    session: Session | None = None,
    analysis=None,
    ebay: EbayCompProvider | None = None,
    research: WebResearchCompProvider | None = None,
    allow_research: bool = True,
) -> Valuation:
    """What will this actually sell for?"""
    query = build_comp_query(listing, analysis)
    category = getattr(listing, "category_hint", None) or getattr(listing, "category", None)

    valuation = Valuation(query_used=query)
    results: list[CompResult] = []

    # ---- free sources first ------------------------------------------------
    if session is not None:
        try:
            internal = await InternalCompProvider(session).lookup(
                query, category=category, hint_price=listing.price
            )
            results.append(internal)
        except Exception as exc:
            log.warning("internal comps failed: %s", exc)

    ebay = ebay or EbayCompProvider(settings)
    if ebay.configured:
        try:
            results.append(await ebay.lookup(query, category=category,
                                             hint_price=listing.price))
        except Exception as exc:
            log.warning("ebay comps failed: %s", exc)
            valuation.warnings.append(f"eBay lookup failed: {exc}")

    best_so_far = max((r.confidence for r in results if r.ok), default=0.0)

    # ---- paid source, only if the free ones weren't enough -----------------
    retail_hint = 0.0
    if (
        allow_research
        and best_so_far < CONFIDENCE_SKIP_RESEARCH
        and listing.price >= RESEARCH_MIN_ASKING
    ):
        research = research or WebResearchCompProvider(settings)
        if research.configured:
            try:
                result = await research.lookup(query, category=category,
                                               hint_price=listing.price)
                results.append(result)
                # A failed research call still often returns a retail anchor.
                if not result.ok and result.high > 0:
                    retail_hint = result.high
            except Exception as exc:
                log.warning("web research failed: %s", exc)

    low, mid, high, confidence, n = _blend(results)

    # ---- prior fallback ----------------------------------------------------
    if mid <= 0:
        if analysis is not None and getattr(analysis, "vision", None):
            retail_hint = retail_hint or getattr(
                analysis.vision, "estimated_retail_new", 0.0
            )
        # The seller's original ask, not the discounted one — see prior_estimate.
        anchor = float(getattr(listing, "first_seen_price", 0.0) or 0.0)
        low, mid, high, method = prior_estimate(
            listing.price, category, retail_hint, anchor_price=anchor
        )
        confidence = 0.22 if retail_hint else 0.12
        n = 0
        valuation.method = method
        valuation.warnings.append(
            "No comparable sales found — this is a category estimate, not a "
            "comp. Verify the price yourself before buying."
        )
        results.append(
            CompResult(provider="prior", query_used=query, low=low, median=mid,
                       high=high, confidence=confidence, note=method)
        )
    else:
        providers = ", ".join(r.provider for r in results if r.ok)
        valuation.method = f"blended from {providers}"

    # ---- calibration against her real outcomes -----------------------------
    if session is not None:
        try:
            factor, samples, explanation = calibration_factor(session, category)
            if factor != 1.0:
                low, mid, high = low * factor, mid * factor, high * factor
                valuation.calibration_applied = factor
                valuation.warnings.append(explanation)
        except Exception as exc:
            log.debug("calibration skipped: %s", exc)

    # ---- velocity ----------------------------------------------------------
    days = [r.est_days_to_sell for r in results if r.est_days_to_sell]
    valuation.est_days_to_sell = (
        int(statistics.median(days)) if days else get_prior(category).days_to_sell
    )

    valuation.low = round(low, 2)
    valuation.mid = round(mid, 2)
    valuation.high = round(high, 2)
    valuation.confidence = round(confidence, 3)
    valuation.sample_size = n
    valuation.sources = [r.as_dict() for r in results]
    return valuation
