"""How far is this actually worth driving?

The brief was: a $2,000 spread on a $4,000 item earns a longer drive than a
$40 flip you're buying in bulk. A tier table would express that, but it jumps
at the boundaries and says nothing useful about the item that lands between
two tiers.

So instead of asking "how far will I drive for this price band", we ask the
question a business actually asks: *does this trip pay for itself?* A round
trip burns gas, wears the car, and eats an hour. We compute the furthest
distance at which that cost stays under a set fraction of the expected
profit. The tiered behaviour falls out for free, and it stays sensible at
every dollar figure in between.

Two things make it match how reselling really works:

* **Batching.** Small items get bought several at a time, so one loop covers
  several pickups and the trip cost divides across them. That's why a $40
  phone flip can still justify a real drive while a $40 couch cannot.
* **Bulk surcharges.** A couch needs a truck and a friend. That's a fixed
  cost that comes off the top before any distance is affordable.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import TripSettings

DEFAULT_BULK = "box"


@dataclass
class TripEconomics:
    """The full explanation behind one radius number, so the app can show its
    work rather than asserting a distance."""

    distance_miles: float
    trip_cost: float
    max_worth_driving: float
    worth_it: bool
    budget: float
    fixed_cost: float
    batch_size: float
    cost_per_mile_effective: float

    def explain(self) -> str:
        if not self.worth_it and self.max_worth_driving <= 0:
            return (
                f"Not worth the trip: a {self.batch_size:.0f}-item run of this size "
                f"carries ${self.fixed_cost:.0f} of fixed cost, which already "
                f"exceeds the ${self.budget:.0f} travel budget this profit supports."
            )
        if not self.worth_it:
            return (
                f"{self.distance_miles:.0f} mi away, but the math only supports "
                f"{self.max_worth_driving:.0f} mi at this profit."
            )
        return (
            f"{self.distance_miles:.0f} mi away; worth driving up to "
            f"{self.max_worth_driving:.0f} mi. Round trip costs about "
            f"${self.trip_cost:.0f}."
        )


def _per_mile_cost(settings: TripSettings, batch_size: float) -> float:
    """Marginal cost of one extra mile of *distance* (i.e. two miles driven),
    after dividing across the items you'd collect on the same loop."""
    fuel = 2.0 * settings.cost_per_mile
    time = (2.0 / max(1e-6, settings.average_speed_mph)) * settings.hourly_time_value
    return (fuel + time) / max(1e-6, batch_size)


def trip_cost(
    distance_miles: float,
    bulk_class: str,
    settings: TripSettings,
) -> float:
    """Real cost of collecting one item that's `distance_miles` away."""
    bulk = bulk_class if bulk_class in settings.expected_batch_size else DEFAULT_BULK
    batch = settings.expected_batch_size[bulk]
    fixed = settings.bulk_fixed_cost.get(bulk, 0.0)
    return _per_mile_cost(settings, batch) * max(0.0, distance_miles) + fixed


def max_worth_driving_miles(
    expected_profit_before_trip: float,
    bulk_class: str,
    settings: TripSettings,
) -> float:
    """Furthest distance where the trip still clears the cost-fraction bar.

    Returns 0.0 when the fixed cost alone eats the budget — that item is not
    worth collecting at any distance, which is a genuinely useful answer for
    a low-margin couch.
    """
    bulk = bulk_class if bulk_class in settings.expected_batch_size else DEFAULT_BULK
    batch = settings.expected_batch_size[bulk]
    fixed = settings.bulk_fixed_cost.get(bulk, 0.0)

    budget = max(0.0, expected_profit_before_trip) * settings.max_trip_cost_fraction
    travel_budget = budget - fixed
    if travel_budget <= 0:
        return 0.0

    miles = travel_budget / _per_mile_cost(settings, batch)
    # Floor: if it's practically next door, just go. Ceiling: a day trip to
    # Bend is not a flip, however good the spread looks on paper.
    return min(max(miles, settings.min_radius_miles), settings.max_radius_miles)


def evaluate_trip(
    distance_miles: float,
    expected_profit_before_trip: float,
    bulk_class: str,
    settings: TripSettings,
) -> TripEconomics:
    """Everything about the drive, in one object."""
    bulk = bulk_class if bulk_class in settings.expected_batch_size else DEFAULT_BULK
    batch = settings.expected_batch_size[bulk]
    fixed = settings.bulk_fixed_cost.get(bulk, 0.0)

    max_miles = max_worth_driving_miles(expected_profit_before_trip, bulk, settings)
    cost = trip_cost(distance_miles, bulk, settings)

    return TripEconomics(
        distance_miles=distance_miles,
        trip_cost=cost,
        max_worth_driving=max_miles,
        worth_it=distance_miles <= max_miles,
        budget=max(0.0, expected_profit_before_trip) * settings.max_trip_cost_fraction,
        fixed_cost=fixed,
        batch_size=batch,
        cost_per_mile_effective=_per_mile_cost(settings, batch),
    )


# --------------------------------------------------------------------------
# Bulk classification
# --------------------------------------------------------------------------
# The collector rarely knows an item's dimensions, but the title is a strong
# signal and getting this roughly right matters more than getting it exactly
# right — it only shifts the radius, it never decides the deal on its own.
_BULK_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("truck", (
        "couch", "sofa", "sectional", "loveseat", "recliner", "armoire",
        "refrigerator", "fridge", "freezer", "washer", "dryer", "stove",
        "range", "dishwasher", "hot tub", "shed", "piano", "mattress",
        "bed frame", "wardrobe", "china cabinet", "hutch", "pool table",
        "riding mower", "treadmill", "table saw", "kayak", "canoe",
        "dining table", "entertainment center", "safe", "workbench",
    )),
    ("two_person", (
        "dresser", "desk", "bookshelf", "bookcase", "nightstand", "chair",
        "cabinet", "credenza", "sideboard", "bike", "bicycle", "e-bike",
        "ebike", "mower", "generator", "air compressor", "snowboard", "skis",
        "stroller", "crib", "grill", "bbq", "tv", "television", "monitor",
        "amplifier", "speaker", "drum", "guitar amp", "miter saw", "ladder",
        "tool chest", "filing cabinet", "ottoman", "rug",
    )),
    ("pocket", (
        "iphone", "phone", "ipad", "tablet", "macbook", "laptop", "watch",
        "airpods", "camera", "lens", "console", "playstation", "xbox",
        "switch", "nintendo", "gpu", "graphics card", "jewelry", "ring",
        "necklace", "kindle", "drone", "gopro", "headphones", "sunglasses",
        "wallet", "handbag", "purse", "cpu", "ssd",
    )),
]


def classify_bulk(title: str, description: str = "", default: str = DEFAULT_BULK) -> str:
    """Guess how hard an item is to move from its title.

    Checked largest-first: "tool chest" should read as two_person even though
    "tool" alone suggests a box, and a "TV stand" is furniture rather than
    electronics.
    """
    text = f"{title} {description}".lower()
    for bulk, words in _BULK_KEYWORDS:
        if any(w in text for w in words):
            return bulk
    return default
