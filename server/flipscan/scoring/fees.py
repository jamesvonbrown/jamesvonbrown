"""What it actually costs to sell the thing.

The number that matters to a reseller is never the spread between the asking
price and the comp — it's what lands in her pocket after the platform takes
its cut, after she buys a can of degreaser, and after she pays for the box.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import FeeSettings

# Rough retail shipping, already padded for dimensional weight. Only pocket-
# and box-sized items are worth shipping at all; a dresser is a local sale.
SHIP_COST_BY_BULK: dict[str, float] = {
    "pocket": 12.00,
    "box": 19.50,
    "two_person": 0.0,
    "truck": 0.0,
}

SHIPPABLE = {"pocket", "box"}

LOCAL_ONLY_VENUES = {"facebook_local", "craigslist"}


def is_shippable(bulk_class: str) -> bool:
    return bulk_class in SHIPPABLE


@dataclass
class SellingCosts:
    """Every dollar between the sale price and the money she keeps."""

    platform_fee: float = 0.0
    shipping: float = 0.0
    supplies: float = 0.0
    refurb: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return self.platform_fee + self.shipping + self.supplies + self.refurb


def pick_venue(
    bulk_class: str,
    resale_estimate: float,
    settings: FeeSettings,
    preferred: str | None = None,
) -> str:
    """Choose where to resell.

    Local cash sale is fee-free and is almost always right for anything big.
    For small, valuable items it's usually worth eating eBay's ~13% to reach a
    national audience, because the local price ceiling on a niche item in one
    metro is a lot lower than the national one.
    """
    venue = preferred or settings.default_venue

    if not is_shippable(bulk_class):
        # Can't ship it, so a shipping venue is not an option regardless.
        return "facebook_local" if venue not in LOCAL_ONLY_VENUES else venue

    if venue in LOCAL_ONLY_VENUES and resale_estimate >= 250 and bulk_class == "pocket":
        # Small + valuable: the national market usually more than covers the fee.
        return "ebay"

    return venue


def estimate_selling_costs(
    sale_price: float,
    venue: str,
    bulk_class: str,
    condition_grade: str,
    settings: FeeSettings,
    seller_pays_shipping: bool = True,
) -> SellingCosts:
    """Full cost stack for one sale."""
    costs = SellingCosts()

    schedule = settings.venues.get(venue) or settings.venues[settings.default_venue]
    costs.platform_fee = sale_price * (schedule["pct"] / 100.0) + schedule["flat"]
    if schedule["pct"] == 0 and schedule["flat"] == 0:
        costs.notes.append("No platform fee — local cash sale.")
    else:
        costs.notes.append(f"{venue} fee: {schedule['pct']:.2f}% + ${schedule['flat']:.2f}")

    ships = venue not in LOCAL_ONLY_VENUES
    if ships and seller_pays_shipping:
        if not is_shippable(bulk_class):
            # Shouldn't happen if pick_venue ran, but a manual venue override can.
            costs.notes.append("WARNING: this item is too big to ship economically.")
        else:
            costs.shipping = SHIP_COST_BY_BULK.get(bulk_class, 0.0)
            costs.supplies = settings.shipping_supplies_cost
            costs.notes.append(
                f"Shipping ~${costs.shipping:.2f} + ${costs.supplies:.2f} supplies"
            )

    costs.refurb = settings.refurb_cost_by_grade.get(condition_grade.upper(), 15.0)
    if costs.refurb:
        costs.notes.append(f"~${costs.refurb:.2f} to clean it up (grade {condition_grade})")

    return costs


def net_from_sale(
    sale_price: float,
    buy_price: float,
    costs: SellingCosts,
    trip_cost_usd: float = 0.0,
) -> float:
    """Money in her pocket."""
    return sale_price - buy_price - costs.total - trip_cost_usd


def roi_pct(net_profit: float, buy_price: float, costs: SellingCosts,
            trip_cost_usd: float = 0.0) -> float:
    """Return on cash actually put at risk.

    Denominated on total cash out — purchase plus the money spent getting and
    refurbishing it — not just the sticker price, because that's the capital
    genuinely tied up until it sells.
    """
    invested = buy_price + costs.refurb + costs.supplies + trip_cost_usd
    if invested <= 0:
        # A free item with no costs: the return is unbounded, so report a large
        # finite number rather than dividing by zero.
        return 999.0 if net_profit > 0 else 0.0
    return (net_profit / invested) * 100.0
