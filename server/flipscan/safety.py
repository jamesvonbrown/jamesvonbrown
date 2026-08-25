"""Meetup safety.

This tool's whole job is to send someone to a stranger's address with cash.
That deserves to be a first-class feature rather than a footnote, so every
deal carries a safety brief sized to what's actually at stake: a $40 pickup
in a grocery-store lot is a different situation from counting out $1,800 in
somebody's garage.

The advice here is deliberately conservative and generic. It never invents a
street address — a wrong address sends her to the wrong place, which is worse
than no address at all. Add verified local spots to `VERIFIED_EXCHANGE_ZONES`
(or via the API) once you've actually confirmed them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Fill these in yourself once confirmed — most Portland-metro agencies run an
# exchange zone, but hours and exact locations change and are worth a phone
# call before you rely on one. Left empty rather than guessed.
VERIFIED_EXCHANGE_ZONES: list[dict[str, str]] = []

# Agencies in the metro known to operate or host safe-exchange areas. Call or
# check the agency's site for the current location and hours.
AGENCIES_WITH_EXCHANGE_ZONES = [
    "Portland Police Bureau — Central, East, and North Precincts",
    "Beaverton Police Department",
    "Hillsboro Police Department",
    "Gresham Police Department",
    "Tigard Police Department",
    "Lake Oswego Police Department",
    "Clackamas County Sheriff's Office",
    "Washington County Sheriff's Office",
    "Vancouver (WA) Police Department",
]


@dataclass
class SafetyBrief:
    """Advice attached to a specific deal."""

    level: str                                   # routine | elevated | high
    headline: str
    rules: list[str] = field(default_factory=list)
    payment_note: str = ""

    def as_dict(self) -> dict:
        return {
            "level": self.level,
            "headline": self.headline,
            "rules": self.rules,
            "payment_note": self.payment_note,
        }


BASE_RULES = [
    "Meet in a busy, well-lit public place with cameras — a staffed store lot beats a quiet street.",
    "Daylight only. If the seller can only do late evening, reschedule rather than adapt.",
    "Tell someone where you're going, who you're meeting, and when you expect to be back. Share your location.",
    "Test the item before any money changes hands. Once you've paid, you've bought it.",
]

HOME_VISIT_RULES = [
    "Furniture and appliances usually mean going to a house. Bring someone with you — always, not just when it feels off.",
    "Stay out of garages, basements, and back yards. Ask them to bring it to the driveway.",
    "Park on the street facing out, not in the driveway.",
]

HIGH_VALUE_RULES = [
    "Bring a second person. This is enough cash to be worth taking.",
    "Use a police-department exchange zone if the item is portable enough to bring to one.",
    "Don't display the full amount. Count out the agreed price, leave the rest out of sight.",
    "Split the trip if you can: verify the item first, get cash second.",
]

SCAM_RULES = [
    "This listing already showed warning signs — re-read them before you go.",
    "Never send a deposit, gift card, or app payment to hold an item. That is the scam, every time.",
    "If they push to ship instead of meeting, walk away. Local pickup is the whole point.",
    "Refuse any request to move the conversation to a different app or a 'verification code'. Code requests are account theft.",
]


def build_brief(
    *,
    price: float,
    bulk_class: str,
    scam_risk: float = 0.0,
    scam_signals: list[str] | None = None,
    red_flags: list[str] | None = None,
) -> SafetyBrief:
    """Advice scaled to the actual situation.

    `scam_signals` and `red_flags` are kept separate on purpose. A chipped
    armrest is a condition note; it is not a reason to warn somebody about
    gift-card fraud. Escalating on any blemish would put the scam warnings on
    nearly every listing, and warnings that appear everywhere stop being read
    anywhere — which is precisely when the real one gets missed.
    """
    red_flags = red_flags or []
    scam_signals = scam_signals or []
    rules = list(BASE_RULES)

    # Big items can't come to a parking lot, so the meet is at their place.
    home_visit = bulk_class in ("two_person", "truck")
    if home_visit:
        rules = HOME_VISIT_RULES + rules

    high_value = price >= 500
    if high_value:
        rules = HIGH_VALUE_RULES + rules

    risky = scam_risk >= 35 or bool(scam_signals)
    if risky:
        rules = SCAM_RULES + rules

    if risky:
        level = "high"
        headline = "This listing has warning signs — verify hard, or skip it."
    elif high_value and home_visit:
        level = "high"
        headline = f"${price:,.0f} in cash at a private address. Bring someone."
    elif high_value or home_visit:
        level = "elevated"
        headline = (
            f"${price:,.0f} cash pickup — meet somewhere public."
            if high_value
            else "Large item, so likely a home pickup. Bring a second person."
        )
    else:
        level = "routine"
        headline = "Standard pickup. Public place, daylight, test before you pay."

    if price >= 800:
        payment = (
            "Cash is still safest for local pickup, but at this amount consider "
            "meeting at her bank and withdrawing right before the handoff rather "
            "than carrying it around all day."
        )
    elif price <= 0:
        payment = "Free item — no money involved, but the meetup rules still apply."
    else:
        payment = "Cash, counted out at the meet. No deposits, no apps, no gift cards, ever."

    # De-dupe while preserving the priority order the rules were assembled in.
    seen, ordered = set(), []
    for r in rules:
        if r not in seen:
            seen.add(r)
            ordered.append(r)

    return SafetyBrief(level=level, headline=headline, rules=ordered, payment_note=payment)
