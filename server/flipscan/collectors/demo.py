"""Demo collector — realistic fixture listings, no network, no Facebook.

Exists so the whole pipeline can be exercised end to end before anyone logs
into anything: scoring, notifications, the phone app, and the API all work
against this. It's also what the tests run on.

The listings below are written to cover the cases that actually matter — a
clean high-margin flip, a scam, a bulky item that fails the drive test, an
item whose photos contradict its description — rather than being a uniform
set of easy wins.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from .base import Collector, CollectResult, RawListing

# A stable placeholder image so the vision path has something to fetch in
# demo mode without hotlinking anyone's photos.
_PLACEHOLDER = "https://placehold.co/800x600/e2e8f0/475569/png?text=Demo+Item"


def _ago(hours: float) -> datetime:
    return datetime.now(UTC) - timedelta(hours=hours)


DEMO_LISTINGS: list[dict] = [
    dict(
        external_id="demo-aeron",
        title="Herman Miller Aeron Chair Size B - fully loaded",
        price=180.0,
        location_text="Beaverton, OR",
        description=(
            "Fully loaded Aeron, size B. Posture fit lumbar, fully adjustable arms, "
            "tilt limiter. No rips or tears in the mesh, cylinder holds height fine. "
            "Smoke free home. Moving out of state next week so it needs to go. "
            "Cash, pickup in Beaverton."
        ),
        seller_name="Dana R.",
        category_hint="furniture",
        hours_old=3,
    ),
    dict(
        external_id="demo-dewalt",
        title="DeWalt 20V MAX combo kit - 5 tools, 2 batteries, charger, bag",
        price=210.0,
        location_text="Gresham, OR",
        description=(
            "DeWalt 20v combo: hammer drill, impact driver, circular saw, recip saw, "
            "work light. Two 5.0Ah batteries and the fast charger. All tested and "
            "working. Some paint on the cases, tools themselves are solid. "
            "Was 300, dropping to 210 to move it."
        ),
        seller_name="Mike T.",
        category_hint="tools",
        hours_old=1,
        first_seen_price=300.0,
    ),
    dict(
        external_id="demo-macbook-scam",
        title="MacBook Pro 16 M3 Max 1TB - like new sealed",
        price=400.0,
        location_text="Portland, OR",
        description=(
            "Brand new sealed in box. Cannot meet in person, I am out of town for "
            "work but can ship same day. Need a $100 Zelle deposit to hold it, "
            "balance on delivery. Serious buyers only, no lowballs."
        ),
        seller_name="John Smith",
        category_hint="electronics",
        hours_old=2,
    ),
    dict(
        external_id="demo-couch",
        title="Large sectional couch - free to good home, must go this weekend",
        price=0.0,
        location_text="Hillsboro, OR",
        description=(
            "Big sectional, grey fabric. Some staining on one cushion and a small "
            "tear on the arm. Pet household. Free if you can haul it, needs to be "
            "gone by Sunday."
        ),
        seller_name="Amanda K.",
        category_hint="furniture",
        hours_old=5,
    ),
    dict(
        external_id="demo-trek",
        title="Trek Domane SL5 56cm carbon road bike",
        price=650.0,
        location_text="Lake Oswego, OR",
        description=(
            "Trek Domane SL5, 56cm, Shimano 105 groupset. Carbon frame and fork. "
            "Ridden maybe 800 miles, kept indoors. New chain and bar tape this "
            "spring. Small chip in the paint on the chainstay, photo 4. "
            "Selling because I upgraded."
        ),
        seller_name="Chris P.",
        category_hint="bikes",
        hours_old=6,
    ),
    dict(
        external_id="demo-washer",
        title="Washer and dryer set - worked when removed",
        price=150.0,
        location_text="Salem, OR",
        description=(
            "Whirlpool washer and dryer, white. Worked when we took them out but "
            "they have been sitting in the garage for about two years. Sold as is, "
            "no returns. You haul."
        ),
        seller_name="Robert L.",
        category_hint="appliances",
        hours_old=30,
    ),
    dict(
        external_id="demo-snowpeak",
        title="Camping bundle - Snow Peak titanium, MSR stove, 2 sleeping bags",
        price=95.0,
        location_text="Southeast Portland",
        description=(
            "Clearing out the garage. Snow Peak titanium cookset and mugs, MSR "
            "Pocket Rocket stove, two REI Igneo 25 degree down bags, both cleaned "
            "and stored uncompressed. Everything works. Downsizing, first come."
        ),
        seller_name="Elena V.",
        category_hint="outdoor",
        hours_old=1,
    ),
    dict(
        external_id="demo-ps5",
        title="PS5 disc edition + 2 controllers + 4 games",
        price=280.0,
        location_text="Vancouver, WA",
        description=(
            "PlayStation 5 disc version, works perfectly. Two DualSense "
            "controllers, one has slight stick drift. Games: Spider-Man 2, Elden "
            "Ring, GT7, Hogwarts Legacy. Original box. Kid moved on to PC."
        ),
        seller_name="Tanya B.",
        category_hint="electronics",
        hours_old=4,
    ),
]


class DemoCollector(Collector):
    """Serves the fixture set. Prices jitter slightly between scans so price-
    drop detection and re-scoring have something real to react to."""

    name = "demo"

    def __init__(self, settings=None, jitter: bool = True):
        self.settings = settings
        self.jitter = jitter
        self._scan_count = 0

    async def collect(self, watchlists: list, limits: dict) -> CollectResult:
        self._scan_count += 1
        listings = []

        for spec in DEMO_LISTINGS:
            price = spec["price"]
            # After the first pass, let a couple of sellers get impatient.
            if self.jitter and self._scan_count > 1 and price > 0 and random.random() < 0.3:
                price = round(price * random.uniform(0.85, 0.98), 2)

            listings.append(
                RawListing(
                    source="demo",
                    external_id=spec["external_id"],
                    url=f"https://example.invalid/marketplace/item/{spec['external_id']}",
                    title=spec["title"],
                    price=price,
                    description=spec["description"],
                    location_text=spec["location_text"],
                    posted_at=_ago(spec.get("hours_old", 2)),
                    seller_name=spec.get("seller_name"),
                    image_urls=[f"{_PLACEHOLDER}+{spec['external_id']}"],
                    category_hint=spec.get("category_hint"),
                    raw={"demo": True, "scan": self._scan_count,
                         "first_seen_price": spec.get("first_seen_price")},
                )
            )

        return CollectResult(
            listings=listings,
            searches_run=1,
            notes=[f"demo collector: {len(listings)} fixture listings"],
        )
