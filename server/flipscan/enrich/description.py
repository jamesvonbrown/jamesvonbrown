"""Rule-based description mining.

This runs on every listing before any money is spent on the API. It's free,
instant, and catches the overwhelming majority of what matters, because
Marketplace sellers describe problems in a small and remarkably consistent
vocabulary. "Worked when removed" means it doesn't work. "Need a deposit to
hold it" means it's a scam. You don't need a language model for that.

The model pass in `vision.py` runs afterwards and sees these findings, so it
spends its attention on what the photos show rather than re-reading the text
for the phrases already caught here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Pattern tables
# --------------------------------------------------------------------------
# (compiled pattern, human-readable finding, weight)
# Weight is scam-risk points for scam patterns, condition points for defects.

SCAM_PATTERNS: list[tuple[str, str, float]] = [
    (r"\b(zelle|cash\s?app|venmo|wire transfer|western union|money ?gram)\b",
     "asks for Zelle / Cash App / wire payment", 30),
    (r"\bgift ?card", "asks for gift cards", 40),
    (r"\bdeposit\b.{0,40}\b(hold|reserve|secure)\b|\b(hold|reserve)\b.{0,30}\bdeposit\b",
     "wants a deposit to hold the item", 35),
    (r"\b(verification|google voice|six.?digit)\b.{0,20}\bcode\b|\bcode\b.{0,20}\bverif",
     "asks for a verification code — this is account theft, not a sale", 55),
    (r"\b(can'?t|cannot|unable to)\s+meet\b|\bno\s+(?:in.?person|meet)",
     "refuses to meet in person", 25),
    (r"\bship(?:ping)?\s+only\b|\bmust\s+ship\b|\bwill\s+ship\s+(?:it\s+)?(?:to\s+you|same\s?day)\b",
     "shipping only on a local pickup marketplace", 25),
    (r"\b(agent|broker|third.?party)\b.{0,30}\b(deliver|handle|arrange)",
     "involves a third-party 'agent' or 'shipper'", 25),
    (r"\btext me at\b|\bwhats\s?app\b|\btelegram\b",
     "pushes the conversation off-platform", 15),
    (r"\bpay(?:pal)?\s+(?:friends?\s+and\s+family|f&f)\b",
     "wants PayPal friends-and-family (no buyer protection)", 25),
]

CONDITION_RED_FLAGS: list[tuple[str, str, float]] = [
    (r"\bfor parts\b|\bparts only\b|\bnot working\b|\bdoes ?n[o']?t work\b|\bbroken\b",
     "sold for parts / not working", 40),
    (r"\bworked when (?:removed|last used|i (?:took|pulled) it)\b",
     "'worked when removed' — treat as untested at best", 25),
    (r"\bas.?is\b", "sold as-is", 12),
    (r"\bneeds? (?:repair|work|fixing|a new|to be fixed)\b",
     "seller says it needs repair", 25),
    (r"\bwon'?t (?:turn on|start|power)\b|\bno power\b",
     "won't power on", 40),
    (r"\bcrack(?:ed|s|ing)?\b|\bshatter(?:ed)?\b|\bsplit\b",
     "cracked", 18),
    (r"\bchip(?:ped|s)?\b|\bpaint (?:chip|loss)\b",
     "chipped paint / cosmetic chip", 6),
    (r"\b(?:torn|rip(?:ped)?|tear)\b", "torn / ripped", 15),
    (r"\bstain(?:ed|s|ing)?\b|\bdiscolo(?:u)?r", "staining or discolouration", 12),
    (r"\bwater damage\b|\bflood(?:ed)?\b|\bgot wet\b", "water damage", 35),
    (r"\brust(?:ed|y)?\b|\bcorro(?:ded|sion)\b", "rust / corrosion", 18),
    (r"\bmissing\b|\bno (?:charger|battery|remote|key|cord|power supply|manual|lid)\b",
     "missing parts or accessories", 20),
    (r"\bsmoke\b(?!\s?free)|\bsmoker\b", "smoking household", 12),
    (r"\bmold(?:y)?\b|\bmildew\b", "mold / mildew", 30),
    (r"\bpets?\b(?!\s?.?free)|\bcats?\b|\bdogs?\b|\bpet hair\b",
     "pets in the home", 6),
    (r"\bno returns?\b|\ball sales? final\b", "no returns", 8),
    (r"\bsalvage\b|\bflood title\b|\brebuilt title\b", "salvage / rebuilt title", 40),
    (r"\bstick drift\b|\bdrift(?:ing)?\b", "controller stick drift", 10),
    (r"\bbattery (?:is )?(?:bad|dead|weak|shot|needs replac)",
     "battery is bad or dead", 25),
    (r"\bscratch(?:es|ed)?\b|\bding(?:s|ed)?\b|\bdent(?:s|ed)?\b|\bscuff",
     "cosmetic scratches or dents", 7),
    (r"\bunteste?d\b|\bnot tested\b|\bcan'?t test\b",
     "untested", 15),
    (r"\bproject\b|\bhandyman\b|\bfixer\b|\bhas issues\b",
     "described as a project", 22),
]

GREEN_FLAGS: list[tuple[str, str]] = [
    (r"\breceipt\b|\bproof of purchase\b", "has the receipt"),
    (r"\b(?:still )?under warranty\b|\bwarranty (?:until|through)\b", "still under warranty"),
    (r"\boriginal box\b|\bwith box\b|\bbox and (?:papers|manual)", "original box included"),
    (r"\bbarely used\b|\bhardly used\b|\bused (?:a )?(?:few|couple) times\b", "barely used"),
    (r"\bsmoke.?free\b|\bnon.?smoking\b", "smoke-free home"),
    (r"\bpet.?free\b|\bno pets\b", "pet-free home"),
    (r"\bjust serviced\b|\bnewly serviced\b|\bnew (?:belt|battery|chain|tires?|blade)\b",
     "recently serviced or has new parts"),
    (r"\bkept (?:indoors|inside)\b|\bstored (?:indoors|inside)\b", "stored indoors"),
    (r"\btested\b|\bworks (?:perfectly|great|fine|as it should)\b", "seller says tested and working"),
    (r"\ball (?:parts|pieces|accessories) included\b|\bcomplete set\b", "complete with accessories"),
]

# Motivation signals — these don't affect condition, but they predict how much
# room there is to negotiate, which is the single most useful thing to know
# walking into a pickup.
# Phrases that are damning next to another scam signal and completely
# innocent on their own. "Moving out of state next week" is the single most
# common honest reason a good deal exists; "I'm out of state, need a deposit"
# is a scam. The words are identical, so weight them by what surrounds them
# rather than trying to separate them with a cleverer regex.
SCAM_AMPLIFIERS: list[tuple[str, str, float]] = [
    (r"\b(?:out of (?:town|state|country)|deployed|overseas|stationed)\b",
     "seller says they're away and can't meet", 20),
    (r"\bmy (?:assistant|agent|shipper|nephew|son)\b.{0,40}\b(?:handle|deliver|pick)",
     "someone else will 'handle' the handover", 20),
    (r"\btrust me\b|\b100% (?:legit|genuine|real)\b",
     "unprompted reassurance about legitimacy", 10),
]

MOTIVATION_PATTERNS: list[tuple[str, str, float]] = [
    (r"\bmoving\b|\brelocat|\bmust be (?:gone|out)\b", "seller is moving", 0.8),
    (r"\bestate\b|\bdownsizing\b|\bcleaning out\b|\bdeclutter", "estate / downsizing", 0.7),
    (r"\bmust go\b|\bneed(?:s)? (?:it )?gone\b|\btoday\b|\bthis weekend\b|\basap\b",
     "hard deadline", 0.9),
    (r"\bmake (?:me )?an offer\b|\bobo\b|\bor best offer\b|\bnegotiable\b",
     "open to offers", 0.6),
    (r"\bprice ?drop\b|\breduced\b|\blowered\b", "already reduced the price", 0.7),
    (r"\bfirst come\b|\bfirst to (?:come|respond)\b", "first-come-first-served", 0.5),
]

_FUNCTIONAL_RULES: list[tuple[str, str]] = [
    (r"\bfor parts\b|\bparts only\b|\bnot working\b|\bdoes ?n[o']?t work\b|"
     r"\bwon'?t (?:turn on|start|power)\b|\bbroken\b", "for_parts"),
    (r"\bworked when (?:removed|last used)\b|\bunteste?d\b|\bnot tested\b|"
     r"\bcan'?t test\b|\bno way to test\b", "untested"),
    (r"\bneeds? (?:repair|work|a new)\b|\bhas issues\b|\bmostly works\b|"
     r"\bexcept\b.{0,30}\b(?:work|function)", "partial"),
    (r"\btested\b|\bworks (?:perfectly|great|fine|well)\b|\bfully functional\b|"
     r"\bin working (?:order|condition)\b", "working"),
]


@dataclass
class DescriptionFindings:
    """Everything the text alone tells us."""

    red_flags: list[str] = field(default_factory=list)
    green_flags: list[str] = field(default_factory=list)
    scam_signals: list[str] = field(default_factory=list)
    motivation_signals: list[str] = field(default_factory=list)

    scam_risk: float = 0.0             # 0-100
    condition_penalty: float = 0.0     # 0-100, subtracted from a condition score
    motivation_score: float = 0.0      # 0-1, how negotiable the seller looks
    functional_status: str = "unknown"

    def as_dict(self) -> dict:
        return {
            "red_flags": self.red_flags,
            "green_flags": self.green_flags,
            "scam_signals": self.scam_signals,
            "motivation_signals": self.motivation_signals,
            "scam_risk": round(self.scam_risk, 1),
            "condition_penalty": round(self.condition_penalty, 1),
            "motivation_score": round(self.motivation_score, 2),
            "functional_status": self.functional_status,
        }


def _scan(text: str, table: list[tuple[str, str, float]]) -> tuple[list[str], float]:
    hits, total = [], 0.0
    for pattern, label, weight in table:
        if re.search(pattern, text, re.I):
            hits.append(label)
            total += weight
    return hits, total


def analyze_description(
    title: str,
    description: str,
    price: float = 0.0,
    category: str | None = None,
) -> DescriptionFindings:
    """Mine the listing text. No network, no cost, no model."""
    text = f"{title}\n{description}"
    findings = DescriptionFindings()

    findings.scam_signals, scam_points = _scan(text, SCAM_PATTERNS)
    findings.red_flags, condition_points = _scan(text, CONDITION_RED_FLAGS)

    findings.green_flags = [
        label for pattern, label in GREEN_FLAGS if re.search(pattern, text, re.I)
    ]

    motivation_hits, motivation_total = [], 0.0
    for pattern, label, weight in MOTIVATION_PATTERNS:
        if re.search(pattern, text, re.I):
            motivation_hits.append(label)
            motivation_total += weight
    findings.motivation_signals = motivation_hits
    findings.motivation_score = min(1.0, motivation_total / 2.5)

    # "Brand new sealed" at a small fraction of plausible retail is the single
    # most reliable scam tell on Marketplace. Neither half is suspicious alone.
    if re.search(r"\b(brand ?new|sealed|unopened|never (?:used|opened))\b", text, re.I):
        if price and price < 500 and re.search(
            r"\b(macbook|iphone|ipad|playstation|xbox|rtx|4090|3080|rolex|louis vuitton|"
            r"gucci|canon|sony a7|nikon z)\b", text, re.I
        ):
            findings.scam_signals.append(
                "'brand new sealed' high-end item at an implausible price"
            )
            scam_points += 35

    # Amplifiers are conditional by design: on their own these phrases are
    # normal seller talk, so they only count once something else is wrong.
    if scam_points > 0:
        amp_hits, amp_points = _scan(text, SCAM_AMPLIFIERS)
        findings.scam_signals.extend(amp_hits)
        scam_points += amp_points

    findings.scam_risk = min(100.0, scam_points)
    findings.condition_penalty = min(100.0, condition_points)

    # First matching rule wins; the table is ordered worst-first so that a
    # listing saying both "for parts" and "works great" resolves pessimistically.
    for pattern, status in _FUNCTIONAL_RULES:
        if re.search(pattern, text, re.I):
            findings.functional_status = status
            break

    return findings


def condition_grade_from_penalty(penalty: float) -> tuple[str, float]:
    """Fallback grade when photo analysis is unavailable.

    Deliberately pessimistic: with no photos, an unremarkable description
    lands at B-minus rather than A, because sellers omit flaws far more often
    than they invent them.
    """
    score = max(0.0, 82.0 - penalty)
    if score >= 88:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 50:
        grade = "C"
    elif score >= 28:
        grade = "D"
    else:
        grade = "F"
    return grade, score


def condition_multiplier(grade: str, functional_status: str = "working") -> float:
    """What condition does to resale value.

    Comps are mostly drawn from working, presentable examples, so anything
    below that needs discounting before the comp means anything.
    """
    base = {"A": 1.10, "B": 1.00, "C": 0.82, "D": 0.58, "F": 0.30}.get(grade.upper(), 0.85)
    if functional_status == "for_parts":
        base = min(base, 0.28)
    elif functional_status == "partial":
        base = min(base, 0.52)
    elif functional_status == "untested":
        base *= 0.80
    return round(base, 3)
