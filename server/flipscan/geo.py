"""Distance, bounding boxes, and clustering pickups into a single drive."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def driving_miles(lat1: float, lon1: float, lat2: float, lon2: float,
                  detour_factor: float = 1.28) -> float:
    """Straight-line distance inflated to approximate real roads.

    A routing API would be exact, but it's another key and another rate limit
    for a number we only need to two significant figures. 1.28 is a decent
    metro-average detour factor; Portland's river crossings push it a little
    higher than a grid city, which the default already accounts for.
    """
    return haversine_miles(lat1, lon1, lat2, lon2) * detour_factor


def bounding_box(lat: float, lon: float, radius_miles: float) -> tuple[float, float, float, float]:
    """(min_lat, min_lon, max_lat, max_lon) covering a radius. For DB prefilters."""
    dlat = radius_miles / 69.0
    # Degrees of longitude shrink as you move away from the equator.
    dlon = radius_miles / max(1e-6, 69.0 * math.cos(math.radians(lat)))
    return (lat - dlat, lon - dlon, lat + dlat, lon + dlon)


# --------------------------------------------------------------------------
# Portland metro neighbourhood centroids
# --------------------------------------------------------------------------
# Facebook usually gives a city/neighbourhood string rather than coordinates.
# Rather than pay for a geocoder on every listing, we resolve the common
# Portland-area place names locally and only fall back to the market centre
# for places we don't recognise. Anything unrecognised is flagged so the
# distance estimate can be treated as low-confidence.
PORTLAND_PLACES: dict[str, tuple[float, float]] = {
    # Portland proper
    "portland": (45.5152, -122.6784),
    "downtown portland": (45.5202, -122.6742),
    "pearl district": (45.5289, -122.6835),
    "northwest portland": (45.5340, -122.6980),
    "northeast portland": (45.5590, -122.6400),
    "southeast portland": (45.4990, -122.6200),
    "southwest portland": (45.4720, -122.7060),
    "north portland": (45.5860, -122.7060),
    "st johns": (45.5906, -122.7565),
    "sellwood": (45.4664, -122.6580),
    "hollywood district": (45.5410, -122.6210),
    "hawthorne": (45.5122, -122.6220),
    "alberta": (45.5590, -122.6470),
    "mississippi": (45.5540, -122.6750),
    "montavilla": (45.5170, -122.5680),
    "lents": (45.4720, -122.5710),
    "multnomah village": (45.4700, -122.7150),
    "laurelhurst": (45.5270, -122.6250),
    "irvington": (45.5450, -122.6540),
    "kenton": (45.5940, -122.6900),
    # Westside suburbs
    "beaverton": (45.4871, -122.8037),
    "hillsboro": (45.5229, -122.9898),
    "tigard": (45.4312, -122.7715),
    "tualatin": (45.3840, -122.7635),
    "sherwood": (45.3573, -122.8401),
    "lake oswego": (45.4207, -122.6706),
    "west linn": (45.3654, -122.6126),
    "wilsonville": (45.3021, -122.7737),
    "forest grove": (45.5198, -123.1104),
    "cornelius": (45.5195, -123.0598),
    "aloha": (45.4923, -122.8670),
    "king city": (45.4009, -122.8026),
    "durham": (45.4021, -122.7551),
    # Eastside suburbs
    "gresham": (45.5001, -122.4302),
    "troutdale": (45.5392, -122.3873),
    "fairview": (45.5387, -122.4370),
    "wood village": (45.5343, -122.4187),
    "happy valley": (45.4468, -122.5140),
    "clackamas": (45.4109, -122.5709),
    "milwaukie": (45.4457, -122.6392),
    "gladstone": (45.3793, -122.5943),
    "oregon city": (45.3573, -122.6068),
    "canby": (45.2632, -122.6923),
    "estacada": (45.2893, -122.3337),
    "sandy": (45.3973, -122.2626),
    "boring": (45.4315, -122.3748),
    "damascus": (45.4165, -122.4423),
    # North / Washington side
    "vancouver": (45.6387, -122.6615),
    "vancouver wa": (45.6387, -122.6615),
    "camas": (45.5871, -122.3995),
    "washougal": (45.5826, -122.3534),
    "battle ground": (45.7807, -122.5334),
    "ridgefield": (45.8162, -122.7423),
    "la center": (45.8618, -122.6706),
    "hazel dell": (45.6740, -122.6640),
    "salmon creek": (45.7160, -122.6570),
    "orchards": (45.6690, -122.5590),
    # Outer ring — usually only worth it for a big spread
    "salem": (44.9429, -123.0351),
    "keizer": (44.9901, -123.0262),
    "woodburn": (45.1437, -122.8554),
    "mcminnville": (45.2101, -123.1976),
    "newberg": (45.3001, -122.9734),
    "hood river": (45.7054, -121.5215),
    "st helens": (45.8646, -122.8062),
    "scappoose": (45.7546, -122.8776),
    "longview": (46.1382, -122.9382),
    "kelso": (46.1468, -122.9084),
    "astoria": (46.1879, -123.8313),
    "tillamook": (45.4562, -123.8443),
    "the dalles": (45.5946, -121.1787),
    "corvallis": (44.5646, -123.2620),
    "albany": (44.6365, -123.1059),
    "eugene": (44.0521, -123.0868),
    "bend": (44.0582, -121.3153),
}

_STATE_SUFFIX = re.compile(r",?\s*(or|ore|oregon|wa|wash|washington)\b\.?$", re.I)


def resolve_place(
    text: str | None,
    fallback: tuple[float, float],
) -> tuple[float, float, bool]:
    """Best-effort place name -> (lat, lon, is_confident).

    Returns the fallback with `is_confident=False` when the place is unknown,
    so callers can down-weight a distance they can't actually trust.
    """
    if not text:
        return (*fallback, False)

    key = _STATE_SUFFIX.sub("", text.strip().lower()).strip(" ,.")
    if key in PORTLAND_PLACES:
        return (*PORTLAND_PLACES[key], True)

    # "Beaverton, OR 97005" or "SE Portland" style strings.
    for name, coords in PORTLAND_PLACES.items():
        if name in key:
            return (*coords, True)

    return (*fallback, False)


# --------------------------------------------------------------------------
# Trip batching
# --------------------------------------------------------------------------
@dataclass
class Cluster:
    """A group of pickups close enough to do in one loop."""

    lat: float
    lon: float
    items: list = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.items)


def cluster_points(
    points: list[tuple[float, float, object]],
    radius_miles: float = 6.0,
) -> list[Cluster]:
    """Greedy single-link clustering of pickup locations.

    Not k-means, deliberately: we don't know k, and what matters to a reseller
    is only "are these close enough to grab on one loop", which a fixed
    distance threshold answers directly. Points are seeded from the densest
    remaining neighbourhood so the big runs form first.
    """
    remaining = list(points)
    clusters: list[Cluster] = []

    while remaining:
        # Seed with whichever point has the most neighbours within the radius.
        best_idx, best_neighbours = 0, -1
        for i, (lat, lon, _) in enumerate(remaining):
            n = sum(
                1 for (la, lo, _) in remaining
                if haversine_miles(lat, lon, la, lo) <= radius_miles
            )
            if n > best_neighbours:
                best_idx, best_neighbours = i, n

        seed_lat, seed_lon, _ = remaining[best_idx]
        grabbed, leftover = [], []
        for pt in remaining:
            if haversine_miles(seed_lat, seed_lon, pt[0], pt[1]) <= radius_miles:
                grabbed.append(pt)
            else:
                leftover.append(pt)

        # Recentre on the members so the cluster centroid is meaningful.
        clat = sum(p[0] for p in grabbed) / len(grabbed)
        clon = sum(p[1] for p in grabbed) / len(grabbed)
        clusters.append(Cluster(lat=clat, lon=clon, items=[p[2] for p in grabbed]))
        remaining = leftover

    clusters.sort(key=lambda c: c.size, reverse=True)
    return clusters
