"""Manual collector — paste a URL or the listing text and get it scored.

Two jobs. First, it's the fallback for when the browser collector breaks,
which it eventually will: she can still run any listing through the full
valuation and photo analysis by pasting it in. Second, it covers the case
the scanner can't — she's standing in front of something at an estate sale
and wants to know in thirty seconds whether it's worth buying.

Nothing here needs a browser or a logged-in session.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .base import Collector, CollectResult, RawListing, parse_price

FB_ITEM_RE = re.compile(r"facebook\.com/marketplace/item/(\d+)")
CRAIGSLIST_RE = re.compile(r"craigslist\.org/[^/]+/[^/]+/(\d+)\.html")
OFFERUP_RE = re.compile(r"offerup\.com/item/detail/([\w-]+)")

# "$450" / "450 dollars" / "asking 450"
PRICE_LINE_RE = re.compile(
    r"(?:\$\s*([\d,]+(?:\.\d{1,2})?))|(?:\b(?:asking|price|obo)\D{0,6}([\d,]+))",
    re.I,
)
LOCATION_LINE_RE = re.compile(
    r"^\s*(?:location|city|in|near)\s*[:\-]\s*(.+)$", re.I | re.M
)


def identify_source(url: str) -> tuple[str, str]:
    """(source, external_id) for a pasted marketplace URL."""
    if m := FB_ITEM_RE.search(url):
        return "facebook", m.group(1)
    if m := CRAIGSLIST_RE.search(url):
        return "craigslist", m.group(1)
    if m := OFFERUP_RE.search(url):
        return "offerup", m.group(1)
    # Unknown site: derive a stable id from the URL so re-pasting the same
    # link updates the existing row rather than creating a duplicate.
    slug = re.sub(r"\W+", "-", url.strip().lower())[-48:].strip("-")
    return "manual", slug or "unknown"


def parse_pasted_text(
    text: str,
    url: str | None = None,
    title: str | None = None,
    price: float | None = None,
    location: str | None = None,
) -> RawListing:
    """Turn a pasted blob into a scoreable listing.

    Explicit arguments always win over anything scraped out of the text —
    if she took the trouble to type the price, don't second-guess it.
    """
    text = (text or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    resolved_title = title or (lines[0] if lines else "Untitled item")

    if price is None:
        match = PRICE_LINE_RE.search(text)
        price = parse_price(match.group(1) or match.group(2)) if match else 0.0

    if location is None:
        match = LOCATION_LINE_RE.search(text)
        location = match.group(1).strip() if match else None

    source, external_id = identify_source(url or resolved_title)

    return RawListing(
        source=source,
        external_id=external_id,
        url=url or "",
        title=resolved_title[:200],
        price=float(price or 0.0),
        description=text,
        location_text=location,
        posted_at=datetime.now(UTC),
        raw={"entry": "manual"},
    )


class ManualCollector(Collector):
    """Holds listings submitted through the API until the next scan picks
    them up. Not schedulable — there's nothing to poll."""

    name = "manual"
    schedulable = False

    def __init__(self, settings=None):
        self.settings = settings
        self._queue: list[RawListing] = []

    def submit(self, listing: RawListing) -> None:
        self._queue.append(listing)

    async def collect(self, watchlists: list, limits: dict) -> CollectResult:
        queued, self._queue = self._queue, []
        return CollectResult(
            listings=queued,
            notes=[f"{len(queued)} manually submitted listing(s)"] if queued else [],
        )
