"""Collector interface and the normalised listing shape.

Everything downstream — valuation, photo analysis, scoring — works on
`RawListing`. Adding OfferUp or Craigslist later means writing one more
collector, not touching the pipeline.
"""

from __future__ import annotations

import abc
import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

# Words that carry no identifying information but wreck a naive fingerprint,
# because half of Marketplace titles contain at least one of them.
_NOISE_WORDS = {
    "obo", "firm", "new", "used", "great", "good", "excellent", "condition",
    "like", "brand", "must", "go", "sale", "selling", "sell", "price", "cheap",
    "free", "delivery", "available", "pickup", "pick", "up", "only", "today",
    "asap", "cash", "the", "a", "an", "and", "or", "for", "with", "in", "on",
    "of", "to", "my", "your", "no", "not", "very", "nice", "perfect", "clean",
    "barely", "hardly", "still", "works", "working",
    # Marketplace filler. These crowd out real identifying words in a
    # fixed-length token list, which then produces a comp query that finds
    # nothing.
    "home", "weekend", "week", "gone", "need", "needs", "haul", "hauling",
    "porch", "curb", "please", "text", "message", "serious", "buyers",
    "lowball", "lowballers", "offers", "offer", "best", "amazing",
    "beautiful", "vintage", "retro", "rare", "awesome",
}

#: Words after which a single character is meaningful rather than noise.
#: "Size B" and "Mark II" are the most price-relevant tokens an Aeron or a
#: camera title has, and dropping them silently produces a comp query for the
#: wrong product.
_DESIGNATOR_WORDS = {
    "size", "model", "mark", "type", "series", "gen", "generation", "rev",
    "version", "class", "grade", "mk", "no", "number", "part", "style",
}

_PRICE_RE = re.compile(r"[-+]?[\d,]*\.?\d+")


def normalize_text(text: str) -> str:
    """Lowercase, strip accents and punctuation, collapse whitespace."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


#: Prices embedded in the title — "$550", "550$", "550 obo". Extremely common
#: on Marketplace and pure noise for identification, since the same item gets
#: relisted at a different number.
_EMBEDDED_PRICE_RE = re.compile(r"\$\s*[\d,]+(?:\.\d{1,2})?|\b[\d,]+(?:\.\d{1,2})?\s*(?:\$|obo\b|firm\b)")


def title_tokens(title: str, keep: int = 6, price: float | None = None) -> list[str]:
    """Identifying words from a title, in order, noise removed.

    Embedded prices are stripped first. Model numbers are deliberately kept —
    "iPhone 14", "5D Mark IV", and "56cm" are the most identifying tokens a
    title has, so this can't just drop everything numeric.
    """
    cleaned = _EMBEDDED_PRICE_RE.sub(" ", title or "")
    raw_words = normalize_text(cleaned).split()

    words = []
    for i, w in enumerate(raw_words):
        if w in _NOISE_WORDS:
            continue
        if len(w) > 1 or w.isdigit():
            words.append(w)
        elif i > 0 and raw_words[i - 1] in _DESIGNATOR_WORDS:
            # "size b" -> keep the b; it's the difference between a $780
            # chair and a $500 one.
            words.append(w)

    # A bare number matching the asking price is the price, not a model number.
    if price:
        as_int = f"{int(price)}"
        words = [w for w in words if w != as_int]

    return words[:keep]


def parse_price(text: str | float | int | None) -> float:
    """Pull a number out of whatever the page gave us.

    Handles '$1,200', 'FREE', '1200 USD', and already-numeric input. Returns
    0.0 for free items, which is a real and interesting price.
    """
    if text is None:
        return 0.0
    if isinstance(text, (int, float)):
        return float(text)

    cleaned = str(text).strip()
    if not cleaned:
        return 0.0
    if re.search(r"\bfree\b", cleaned, re.I):
        return 0.0

    match = _PRICE_RE.search(cleaned.replace(",", ""))
    return float(match.group()) if match else 0.0


def price_bucket(price: float) -> int:
    """Coarse, log-scaled price band.

    Fixed-width buckets break exactly where they shouldn't: $545 and $550 are
    obviously the same chair, but a $25-wide bucket splits them. A log scale
    keeps a haggle inside one band while still separating a $50 item from a
    $5,000 one, which is all the fingerprint needs price for.
    """
    if price <= 0:
        return 0
    return round(math.log10(max(price, 1.0)) * 2)


#: Trailing state, ZIP, and the "· 12 miles away" suffix Marketplace appends.
_LOCATION_NOISE_RE = re.compile(
    r"(,?\s*\b(?:or|ore|oregon|wa|wash|washington|usa|us)\b\.?"
    r"|\s*\d{5}(?:-\d{4})?"
    r"|\s*[·|-]\s*[\d.]+\s*mi(?:les?)?(?:\s*away)?)+\s*$",
    re.I,
)


def normalize_location(location: str | None) -> str:
    """Canonical city name for comparison.

    Marketplace is wildly inconsistent about the same place: 'Gresham',
    'Gresham, OR', and 'Gresham, OR 97030 · 14 miles away' are all the same
    city, and a fingerprint that treats them as three cities never dedupes
    anything.
    """
    if not location:
        return ""
    text = location.strip()
    # Applied repeatedly because the suffixes stack in any order.
    for _ in range(3):
        stripped = _LOCATION_NOISE_RE.sub("", text).strip(" ,·|-")
        if stripped == text:
            break
        text = stripped
    return normalize_text(text)[:24]


def make_fingerprint(title: str, price: float, location: str | None) -> str:
    """Stable key for 'this is the same item as that'.

    Built from the identifying words, a coarse price band, and the city.
    Location matters: two identical titles in Portland and Salem really are
    different items, and one of them is not worth the drive.
    """
    tokens = "-".join(title_tokens(title, price=price))
    loc = normalize_location(location)
    return hashlib.sha256(
        f"{tokens}|{price_bucket(price)}|{loc}".encode()
    ).hexdigest()[:24]


@dataclass
class RawListing:
    """One listing as observed, before any analysis."""

    source: str
    external_id: str
    url: str
    title: str

    price: float = 0.0
    currency: str = "USD"
    description: str = ""
    location_text: str | None = None
    posted_at: datetime | None = None

    seller_name: str | None = None
    seller_url: str | None = None
    seller_joined_year: int | None = None

    image_urls: list[str] = field(default_factory=list)

    # Full-page screenshot of the listing, saved locally. Doubles as evidence:
    # sellers edit and delete listings, and this is what it said when we saw it.
    screenshot_path: str | None = None

    category_hint: str | None = None
    watchlist_id: int | None = None

    # Everything the collector saw. When a site changes its markup and the
    # parser starts emitting nonsense, this is what makes it debuggable.
    raw: dict = field(default_factory=dict)

    def fingerprint(self) -> str:
        return make_fingerprint(self.title, self.price, self.location_text)

    def is_usable(self) -> bool:
        """Enough signal to be worth spending money analysing."""
        return bool(self.title and self.url and self.external_id) and len(self.title) > 3


@dataclass
class CollectResult:
    listings: list[RawListing] = field(default_factory=list)
    searches_run: int = 0
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class Collector(abc.ABC):
    """A source of listings."""

    name: str = "base"
    #: Set False for sources that can't be polled automatically (e.g. manual).
    schedulable: bool = True

    @abc.abstractmethod
    async def collect(self, watchlists: list, limits: dict) -> CollectResult:
        """Fetch current listings for the given watchlists.

        `limits` carries the per-scan ceilings from ScanSettings. Collectors
        must respect them — they're what keeps this a personal shopping tool
        rather than a bulk harvester.
        """

    async def close(self) -> None:
        """Release browsers, sessions, etc."""
        return None
