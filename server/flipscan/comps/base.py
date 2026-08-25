"""Comparable-sales interface and the statistics that make comps trustworthy.

The single number that decides every buy is "what will this actually sell
for". Getting it wrong in the optimistic direction is how a reseller ends up
with a garage full of things nobody wants, so the statistics here are built
to be conservative:

* the **median**, never the mean — one collector paying $900 for a $300 item
  should not move the estimate
* **relevance filtering** before any arithmetic, because a search for "Aeron
  chair" returns replacement casters and armrest pads
* **explicit confidence** from sample size and spread, so thin evidence can
  be discounted downstream instead of quietly passing as fact
"""

from __future__ import annotations

import abc
import math
import statistics
from dataclasses import dataclass, field

from rapidfuzz import fuzz

# Titles that are a *part of* the item rather than the item.
#
# This list carries real weight: "Herman Miller Aeron armrest pads" shares
# every meaningful word with "Herman Miller Aeron", so pure text similarity
# scores it as a near-perfect match. Left unfiltered, a handful of $30
# accessory sales drag a $780 chair's estimate down far enough to make a
# genuine deal look like a bad one.
ACCESSORY_MARKERS = (
    # generic
    "case", "cover", "screen protector", "cable", "charger only", "manual",
    "sticker", "decal", "replacement part", "parts only", "for parts",
    "bracket", "mount only", "strap", "bag only", "empty box", "box only",
    "adapter", "remote only", "battery only", "stand only", "cartridge",
    "instruction", "user guide", "owners manual",
    # furniture / chair parts
    "casters", "caster set", "armrest", "arm rest", "armpad", "arm pad",
    "seat pan", "cylinder only", "mesh only", "lumbar only", "base only",
    "wheels only", "cushion only", "upholstery",
    # tool parts
    "chuck", "brushes", "blade only", "bit set", "battery pack only",
    "belt only", "carrying case", "hard case",
    # bike parts
    "saddle", "seatpost", "handlebar", "derailleur", "cassette", "rotor",
    "pedals only", "wheelset", "stem only", "fork only", "frame only",
    # electronics parts
    "digitizer", "lcd only", "screen only", "logic board", "keyboard only",
    "power supply only", "faceplate", "shell only", "controller only",
)


@dataclass
class CompSample:
    """One observed comparable."""

    title: str
    price: float
    url: str = ""
    sold: bool = False
    sold_date: str = ""
    condition: str = ""
    relevance: float = 1.0

    def as_dict(self) -> dict:
        return {
            "title": self.title[:120],
            "price": round(self.price, 2),
            "url": self.url,
            "sold": self.sold,
            "sold_date": self.sold_date,
            "condition": self.condition,
            "relevance": round(self.relevance, 2),
        }


@dataclass
class CompResult:
    """One provider's answer."""

    provider: str
    samples: list[CompSample] = field(default_factory=list)
    low: float = 0.0
    median: float = 0.0
    high: float = 0.0
    confidence: float = 0.0
    sample_size: int = 0
    sell_through_pct: float | None = None
    est_days_to_sell: int | None = None
    query_used: str = ""
    note: str = ""
    error: str | None = None

    #: Per-result override of the provider's default blend weight. Lets a
    #: provider say "this particular answer is weaker than my usual" — e.g.
    #: eBay falling back from sold data to active asking prices.
    weight_hint: float | None = None

    @property
    def ok(self) -> bool:
        return self.median > 0 and self.error is None

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "n": self.sample_size,
            "low": round(self.low, 2),
            "median": round(self.median, 2),
            "high": round(self.high, 2),
            "confidence": round(self.confidence, 3),
            "sell_through_pct": self.sell_through_pct,
            "est_days_to_sell": self.est_days_to_sell,
            "query": self.query_used,
            "note": self.note,
            "error": self.error,
            "weight_hint": self.weight_hint,
            # Keep a few so she can click through and check the work herself.
            "examples": [s.as_dict() for s in self.samples[:6]],
        }


# --------------------------------------------------------------------------
# Relevance
# --------------------------------------------------------------------------
def relevance_score(query: str, title: str) -> float:
    """0-1 estimate that `title` is the same product as `query`.

    Token-set ratio rather than plain similarity because comp titles are
    keyword soup — "Herman Miller Aeron Chair Size B Graphite Fully Loaded
    Posturefit 2024" should match "Herman Miller Aeron Size B" strongly, and
    word order and padding shouldn't matter.
    """
    if not query or not title:
        return 0.0

    q, t = query.lower(), title.lower()
    score = fuzz.token_set_ratio(q, t) / 100.0

    # An accessory listing can score high on words alone — "Aeron chair
    # replacement casters" shares every meaningful token with the chair.
    if any(marker in t for marker in ACCESSORY_MARKERS):
        if not any(marker in q for marker in ACCESSORY_MARKERS):
            score *= 0.25

    # Lots and bundles distort a single-item comp in either direction.
    if any(w in t for w in ("lot of", "bundle of", "wholesale", "pallet")):
        if not any(w in q for w in ("lot", "bundle")):
            score *= 0.5

    return round(min(1.0, score), 3)


def filter_relevant(
    query: str, samples: list[CompSample], min_relevance: float = 0.62
) -> list[CompSample]:
    """Keep only plausible matches, scored and sorted."""
    kept = []
    for s in samples:
        s.relevance = relevance_score(query, s.title)
        if s.relevance >= min_relevance and s.price > 0:
            kept.append(s)
    kept.sort(key=lambda s: s.relevance, reverse=True)
    return kept


# --------------------------------------------------------------------------
# Robust statistics
# --------------------------------------------------------------------------
def reject_outliers(prices: list[float], k: float = 1.5) -> list[float]:
    """Drop prices outside the IQR fences.

    eBay results routinely contain a $12 accessory and a $2,000 "lot of 6"
    listed under the same keywords. The median resists them, but the low/high
    band doesn't, and that band is what tells her how wrong the estimate
    might be.
    """
    if len(prices) < 4:
        return sorted(prices)

    ordered = sorted(prices)
    q1 = statistics.quantiles(ordered, n=4)[0]
    q3 = statistics.quantiles(ordered, n=4)[2]
    iqr = q3 - q1
    if iqr <= 0:
        return ordered

    lo, hi = q1 - k * iqr, q3 + k * iqr
    trimmed = [p for p in ordered if lo <= p <= hi]
    return trimmed or ordered


def confidence_from(samples: list[CompSample], prices: list[float]) -> float:
    """How much to trust this estimate, 0-1.

    Three things move it: how many comps there are, how tightly they agree,
    and how well their titles matched. Ten listings that all say $300 is a
    number; three that say $120, $300, and $700 is a guess wearing a number's
    clothes.
    """
    n = len(prices)
    if n == 0:
        return 0.0

    # Sample size: saturating, since the 20th comp adds little over the 10th.
    size_factor = min(1.0, math.log10(n + 1) / math.log10(13))

    # Dispersion: coefficient of variation, inverted.
    if n >= 2:
        mean = statistics.fmean(prices)
        cv = (statistics.pstdev(prices) / mean) if mean > 0 else 1.0
        spread_factor = max(0.0, 1.0 - min(1.0, cv / 0.55))
    else:
        spread_factor = 0.3

    relevance_factor = (
        statistics.fmean([s.relevance for s in samples]) if samples else 0.5
    )

    score = 0.42 * size_factor + 0.36 * spread_factor + 0.22 * relevance_factor
    return round(min(1.0, max(0.0, score)), 3)


def summarize(
    provider: str,
    query: str,
    samples: list[CompSample],
    *,
    min_relevance: float = 0.62,
    asking_to_sold: float = 1.0,
    note: str = "",
) -> CompResult:
    """Filter, trim, and summarise one provider's samples into an estimate.

    `asking_to_sold` converts asking prices into expected sale prices. Active
    listings are what a seller *hopes* for; the ratio is the haircut that
    turns hope into a number worth acting on. Pass 1.0 for genuine sold data.
    """
    result = CompResult(provider=provider, query_used=query, note=note)

    relevant = filter_relevant(query, samples, min_relevance)
    if not relevant:
        result.error = "no relevant comparables"
        result.sample_size = 0
        return result

    prices = reject_outliers([s.price for s in relevant])
    if not prices:
        result.error = "all comparables rejected as outliers"
        return result

    result.samples = relevant
    result.sample_size = len(prices)
    result.median = statistics.median(prices) * asking_to_sold

    # A percentile band rather than min/max: the extremes are usually the
    # weirdest listings, and she needs a realistic range, not the record.
    if len(prices) >= 4:
        result.low = statistics.quantiles(prices, n=4)[0] * asking_to_sold
        result.high = statistics.quantiles(prices, n=4)[2] * asking_to_sold
    else:
        result.low = min(prices) * asking_to_sold
        result.high = max(prices) * asking_to_sold

    result.confidence = confidence_from(relevant, prices)
    return result


class CompProvider(abc.ABC):
    """A source of comparable sales."""

    name: str = "base"
    #: Relative trust when blending providers. Real sold data outranks asks.
    weight: float = 1.0

    @abc.abstractmethod
    async def lookup(self, query: str, *, category: str | None = None,
                     hint_price: float = 0.0) -> CompResult:
        """Find comparables for `query`."""

    async def close(self) -> None:
        return None
