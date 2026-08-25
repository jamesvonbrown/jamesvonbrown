"""Batching pickups into single drives.

Three $70 flips scattered across the metro are three separate trips and
barely worth doing. The same three clustered in Gresham are one loop and a
genuinely good afternoon. The per-deal radius model already assumes some
batching; this module finds the batches that actually exist right now.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import TripSettings
from ..geo import PORTLAND_PLACES, cluster_points, driving_miles


@dataclass
class PickupRun:
    """A set of pickups worth doing on one drive."""

    center_lat: float
    center_lon: float
    label: str
    deals: list = field(default_factory=list)

    distance_from_home: float = 0.0
    shared_trip_cost: float = 0.0
    total_net_profit: float = 0.0
    profit_after_trip: float = 0.0
    est_hours: float = 0.0

    @property
    def size(self) -> int:
        return len(self.deals)

    def summary(self) -> str:
        return (
            f"{self.size} pickup{'s' if self.size != 1 else ''} near {self.label} — "
            f"${self.profit_after_trip:,.0f} profit for a "
            f"{self.distance_from_home:.0f} mi round trip "
            f"(~{self.est_hours:.1f}h)"
        )


def nearest_place_name(lat: float, lon: float, fallback: str = "the metro") -> str:
    """Closest known neighbourhood, for a human-readable run label."""
    best, best_d = fallback, float("inf")
    for name, (plat, plon) in PORTLAND_PLACES.items():
        d = driving_miles(lat, lon, plat, plon)
        if d < best_d:
            best, best_d = name, d
    return best.title()


def plan_runs(
    deals: list,
    settings: TripSettings,
    home_lat: float,
    home_lon: float,
    cluster_radius_miles: float = 6.0,
    min_run_size: int = 2,
) -> list[PickupRun]:
    """Group deals into drives and recompute the economics per run.

    `deals` need `.lat`, `.lon`, and `.net_profit`. Deals without coordinates
    are skipped rather than dumped at the market centre, where they'd make a
    phantom cluster downtown.

    The run's trip cost is charged once for the whole loop instead of once per
    item, which is the actual saving from batching — so a run can be worth
    driving even when none of its members clear the bar alone.
    """
    points = [
        (d.lat, d.lon, d)
        for d in deals
        if getattr(d, "lat", None) is not None and getattr(d, "lon", None) is not None
    ]
    if not points:
        return []

    runs: list[PickupRun] = []
    for cluster in cluster_points(points, cluster_radius_miles):
        if len(cluster.items) < min_run_size:
            continue

        dist = driving_miles(home_lat, home_lon, cluster.lat, cluster.lon)

        # One loop out and back, plus local hops between the stops in the
        # cluster, plus a few minutes standing in a driveway per pickup.
        intra = cluster_radius_miles * max(0, len(cluster.items) - 1) * 0.6
        driven = 2 * dist + intra
        drive_hours = driven / max(1e-6, settings.average_speed_mph)
        handling_hours = 0.2 * len(cluster.items)
        hours = drive_hours + handling_hours

        shared_cost = driven * settings.cost_per_mile + hours * settings.hourly_time_value
        shared_cost += sum(
            settings.bulk_fixed_cost.get(getattr(d, "bulk_class", "box"), 0.0)
            for d in cluster.items
        )

        # Members were each scored with their own share of a trip cost baked
        # in; add it back before charging the single shared cost, or the trip
        # gets paid for twice.
        gross = sum(
            getattr(d, "net_profit", 0.0) + getattr(d, "trip_cost", 0.0)
            for d in cluster.items
        )

        runs.append(
            PickupRun(
                center_lat=cluster.lat,
                center_lon=cluster.lon,
                label=nearest_place_name(cluster.lat, cluster.lon),
                deals=list(cluster.items),
                distance_from_home=dist,
                shared_trip_cost=shared_cost,
                total_net_profit=gross,
                profit_after_trip=gross - shared_cost,
                est_hours=hours,
            )
        )

    runs.sort(key=lambda r: r.profit_after_trip, reverse=True)
    return runs
