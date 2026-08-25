"""Photo-based condition grading via Claude.

This is the part of the brief that a price screen genuinely cannot do: look
at what's actually pictured and judge whether it's worth buying. A listing
titled "Aeron chair $180" is either the flip of the week or a knockoff with
a collapsed cylinder, and the only thing that separates those two is the
photographs.

What the model is asked to do, specifically:

* identify the item more precisely than the title does (the title says
  "office chair"; the photo says "Aeron, size B, posture-fit lumbar")
* grade condition from visible evidence and say what it saw
* flag damage and missing parts the seller didn't mention
* spot stock photos, which mean you can't see the real item at all
* reconcile the photos against the description, because the gap between what
  a seller writes and what they photograph is where the money is
* produce the search string that will find real comparable sales
* write an inspection checklist for this specific item

Everything degrades gracefully: no API key, no budget left, or a failed call
all fall back to the rule-based read from `description.py` rather than
blocking the scan.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..config import Settings
from .description import (
    DescriptionFindings,
    analyze_description,
    condition_grade_from_penalty,
    condition_multiplier,
)
from .images import ImageBundle, fetch_images

log = logging.getLogger(__name__)

# USD per million tokens. Used for the daily budget cap, not billing.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-fable-5": (10.00, 50.00),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = MODEL_PRICING.get(model, (5.00, 25.00))
    return (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate


# --------------------------------------------------------------------------
# Structured output schema
# --------------------------------------------------------------------------
# Deliberately no Optional fields: strict JSON schema handles required
# non-nullable fields most reliably, so "unknown" is expressed as an empty
# string or an explicit enum member instead of null.
class ItemVisionAnalysis(BaseModel):
    """What the model concluded from the photos and the listing text."""

    identified_brand: str = Field(
        default="", description="Brand if identifiable from the photos, else empty."
    )
    identified_model: str = Field(
        default="",
        description="Specific model/variant, e.g. 'Aeron Size B Posture Fit' or "
        "'20V MAX XR DCD996'. Empty if not determinable.",
    )
    identified_year: str = Field(
        default="", description="Model year or generation if visible, else empty."
    )
    identification_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="0-1 confidence that the identification above is correct.",
    )

    condition_grade: Literal["A", "B", "C", "D", "F"] = Field(
        description=(
            "A = looks new/unused. B = light normal wear, nothing that affects "
            "value. C = clearly used, visible cosmetic issues. D = heavy wear or "
            "damage affecting function or resale. F = broken, parts only, or the "
            "photos are too poor to tell."
        )
    )
    condition_score: float = Field(
        ge=0.0, le=100.0, description="0-100, consistent with the grade."
    )
    condition_summary: str = Field(
        description="One or two sentences on what the photos actually show. "
        "Cite visible evidence, not assumptions."
    )

    damage_flags: list[str] = Field(
        default_factory=list,
        description="Specific visible damage. Each item short and concrete, e.g. "
        "'crack across bottom-left of screen', 'rust on the deck underside'.",
    )
    missing_parts: list[str] = Field(
        default_factory=list,
        description="Parts/accessories that should be present and visibly are not, "
        "e.g. 'no charger pictured', 'one caster missing'.",
    )
    positive_signals: list[str] = Field(
        default_factory=list,
        description="Visible evidence of value: original box, unworn pads, clean "
        "ports, matching serials, low hours on a display.",
    )

    functional_status: Literal["working", "untested", "partial", "for_parts", "unknown"] = (
        Field(description="Best read of whether it works, from photos AND text.")
    )

    uses_stock_photos: bool = Field(
        description="True if any photo is a manufacturer/marketing image rather "
        "than a photo of the actual item being sold."
    )
    photo_quality: Literal["good", "poor", "misleading", "unknown"] = Field(
        description="'misleading' means the photos appear to deliberately hide "
        "the item's condition — every shot at a distance, or only partial views."
    )
    photo_caveats: list[str] = Field(
        default_factory=list,
        description="What the photos fail to show that a buyer would need, e.g. "
        "'no photo of the screen powered on', 'underside never shown'.",
    )

    description_mismatch: list[str] = Field(
        default_factory=list,
        description="Places the photos contradict the description. This is the "
        "highest-value output in the whole schema — say so plainly when the text "
        "claims 'excellent condition' and the photos show a torn cushion.",
    )
    authenticity_concern: bool = Field(
        description="True if this may be counterfeit — wrong logo, wrong "
        "proportions, wrong materials for the claimed brand."
    )
    additional_scam_signals: list[str] = Field(
        default_factory=list,
        description="Scam indicators visible in the images: a screenshot of "
        "another listing, a watermark from a different site, a photo of a photo.",
    )

    suggested_comp_query: str = Field(
        description="The search string most likely to return genuinely "
        "comparable SOLD listings. Include brand, model, and the specifics that "
        "move price (size, capacity, generation). Omit condition adjectives."
    )
    estimated_retail_new: float = Field(
        default=0.0,
        description="Approximate current new price in USD if known, else 0.",
    )

    inspection_checklist: list[str] = Field(
        default_factory=list,
        description="3-6 things to physically check before handing over cash, "
        "specific to THIS item. Not generic advice.",
    )


SYSTEM_PROMPT = """\
You grade secondhand items for a reseller in Portland, Oregon. She buys off \
Facebook Marketplace and resells locally or on eBay. Your judgement decides \
whether she spends an hour driving and her own money.

Grade what you can actually see. If a photo doesn't show something, say so in \
photo_caveats rather than assuming the best or the worst — "the underside is \
never pictured" is useful; a guess about the underside is not.

Weigh these heavily:

- Damage the seller didn't mention. A torn mesh panel in photo 3 of a listing \
that says "great condition" is the single most valuable thing you can find.
- Stock photos. On a used-goods listing they mean the buyer cannot see the \
real item, which is a material risk regardless of price.
- Counterfeits. Check logo placement, proportions, materials, and stitching \
against what the genuine article looks like.
- Completeness. A tool kit missing its battery, a console missing its cables, \
a chair missing a caster — each is a real deduction from resale value.

Be concrete and brief. "Scuffing along the front-left leg, roughly 2 inches" \
beats "some wear". Never pad a list to look thorough: an empty damage_flags \
list on a genuinely clean item is the correct answer.

Grade against what the item should look like at its age and type. A five-year-old \
work tool with scuffed cases and clean chucks is a B, not a C — expected \
cosmetic wear on a tool is not damage. Grade a chair by its mesh, cylinder, and \
casters, not by dust."""


@dataclass
class AnalysisResult:
    """Merged output of the rule-based pass and the model pass."""

    vision: ItemVisionAnalysis | None
    findings: DescriptionFindings
    images: ImageBundle
    model_used: str = ""
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None
    used_ai: bool = False

    # -- merged fields, as the rest of the app consumes them ----------------
    @property
    def condition_grade(self) -> str:
        return self.vision.condition_grade if self.vision else self._fallback_grade()[0]

    @property
    def condition_score(self) -> float:
        return self.vision.condition_score if self.vision else self._fallback_grade()[1]

    @property
    def functional_status(self) -> str:
        if self.vision and self.vision.functional_status != "unknown":
            return self.vision.functional_status
        return self.findings.functional_status

    @property
    def scam_risk(self) -> float:
        """Text signals plus anything the images gave away."""
        risk = self.findings.scam_risk
        if self.vision:
            risk += 12.0 * len(self.vision.additional_scam_signals)
            if self.vision.uses_stock_photos:
                risk += 10.0
            if self.vision.photo_quality == "misleading":
                risk += 12.0
            if self.vision.authenticity_concern:
                risk += 15.0
        return min(100.0, risk)

    @property
    def resale_condition_multiplier(self) -> float:
        base = condition_multiplier(self.condition_grade, self.functional_status)
        if self.vision:
            # Undisclosed damage costs more than the same damage disclosed —
            # it means the rest of the listing is unreliable too.
            base *= max(0.7, 1.0 - 0.08 * len(self.vision.description_mismatch))
            if self.vision.missing_parts:
                base *= max(0.7, 1.0 - 0.06 * len(self.vision.missing_parts))
        return round(min(1.15, base), 3)

    @property
    def red_flags(self) -> list[str]:
        out = list(self.findings.red_flags) + list(self.findings.scam_signals)
        if self.vision:
            out += self.vision.damage_flags
            out += self.vision.description_mismatch
            out += self.vision.additional_scam_signals
        # De-dupe, keep order.
        seen, ordered = set(), []
        for f in out:
            if f.lower() not in seen:
                seen.add(f.lower())
                ordered.append(f)
        return ordered

    @property
    def comp_query(self) -> str:
        if self.vision and self.vision.suggested_comp_query.strip():
            return self.vision.suggested_comp_query.strip()
        return ""

    def _fallback_grade(self) -> tuple[str, float]:
        return condition_grade_from_penalty(self.findings.condition_penalty)

    def to_model_kwargs(self, listing_id: int) -> dict:
        """Fields for constructing an `Analysis` row."""
        v = self.vision
        return dict(
            listing_id=listing_id,
            identified_brand=(v.identified_brand if v else "") or None,
            identified_model=(v.identified_model if v else "") or None,
            identified_year=(v.identified_year if v else "") or None,
            identification_confidence=v.identification_confidence if v else 0.0,
            condition_grade=self.condition_grade,
            condition_score=self.condition_score,
            condition_summary=(v.condition_summary if v else
                               "Graded from the listing text only — no photo analysis."),
            damage_flags=list(v.damage_flags) if v else list(self.findings.red_flags),
            missing_parts=list(v.missing_parts) if v else [],
            positive_signals=(list(v.positive_signals) if v
                              else list(self.findings.green_flags)),
            functional_status=self.functional_status,
            uses_stock_photos=bool(v and v.uses_stock_photos),
            photo_quality=(v.photo_quality if v else "unknown"),
            photo_caveats=list(v.photo_caveats) if v else [],
            description_red_flags=self.red_flags,
            description_green_flags=list(self.findings.green_flags),
            scam_risk=self.scam_risk,
            authenticity_concern=bool(v and v.authenticity_concern),
            suggested_comp_query=self.comp_query or None,
            resale_condition_multiplier=self.resale_condition_multiplier,
            model_used=self.model_used,
            cost_usd=self.cost_usd,
            raw_response=(v.model_dump() if v else {}),
        )


def _build_user_content(
    listing, findings: DescriptionFindings, images: ImageBundle
) -> list[dict]:
    """Images first, then the text. The model reads the pictures before it
    reads the seller's claims about them, which is the order that surfaces
    contradictions instead of anchoring on the description."""
    content: list[dict] = list(images.content_blocks())

    already_found = ""
    if findings.red_flags or findings.scam_signals:
        bullets = "\n".join(
            f"  - {f}" for f in (findings.red_flags + findings.scam_signals)[:10]
        )
        already_found = (
            "\n\nA keyword pass over the text already caught the following, so "
            "don't just restate them — focus on what the PHOTOS add or "
            "contradict:\n" + bullets
        )

    photo_note = (
        f"\n\n{len(images.usable)} photo(s) attached."
        if images.usable
        else "\n\nNO PHOTOS were available. Grade from the text alone, set "
             "photo_quality to 'unknown', and say so in condition_summary."
    )

    content.append(
        {
            "type": "text",
            "text": (
                f"LISTING\n"
                f"Title: {listing.title}\n"
                f"Asking price: ${listing.price:,.2f}\n"
                f"Location: {listing.location_text or 'unknown'}\n"
                f"Category: {listing.category_hint or 'unknown'}\n\n"
                f"Seller's description:\n{listing.description or '(none provided)'}"
                f"{already_found}{photo_note}"
            ),
        }
    )
    return content


async def analyze_listing(
    listing,
    settings: Settings,
    *,
    client=None,
    budget_remaining: float | None = None,
    use_model: str | None = None,
) -> AnalysisResult:
    """Full analysis of one listing.

    Always returns a usable result. The rule-based pass runs first and stands
    alone if the model pass can't run, so a missing API key degrades the
    quality of the answer without stopping the scan.
    """
    findings = analyze_description(
        listing.title, listing.description, listing.price, listing.category_hint
    )
    result = AnalysisResult(vision=None, findings=findings, images=ImageBundle())

    if not settings.anthropic_api_key:
        result.error = "no ANTHROPIC_API_KEY — text-only analysis"
        return result

    if budget_remaining is not None and budget_remaining <= 0:
        result.error = "daily AI budget exhausted — text-only analysis"
        return result

    # Fetch photos before spending a call, so a listing whose images all fail
    # still gets analysed on its text rather than being skipped.
    try:
        result.images = await fetch_images(
            listing.image_urls,
            max_images=settings.ai.max_images_per_listing,
            max_edge=settings.ai.image_max_edge_px,
            cache_dir=f"{settings.media_dir}/images",
        )
    except Exception as exc:
        log.warning("image fetch failed for %s: %s", listing.title[:40], exc)

    model = use_model or settings.ai.model

    try:
        if client is None:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        response = await client.messages.parse(
            model=model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"effort": settings.ai.effort},
            output_format=ItemVisionAnalysis,
            messages=[{"role": "user",
                       "content": _build_user_content(listing, findings, result.images)}],
        )

        result.vision = response.parsed_output
        result.used_ai = True
        result.model_used = model
        usage = getattr(response, "usage", None)
        if usage:
            result.input_tokens = getattr(usage, "input_tokens", 0) or 0
            result.output_tokens = getattr(usage, "output_tokens", 0) or 0
            result.cost_usd = estimate_cost(
                model, result.input_tokens, result.output_tokens
            )

    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        log.warning("vision analysis failed for %r: %s", listing.title[:50], exc)

    return result


def neutral_analysis():
    """A stand-in with no opinion, for scoring a listing before enrichment."""

    @dataclass
    class _Neutral:
        condition_grade: str = "B"
        condition_score: float = 70.0
        condition_summary: str = "Not yet analysed."
        functional_status: str = "unknown"
        resale_condition_multiplier: float = 1.0
        scam_risk: float = 0.0
        authenticity_concern: bool = False
        uses_stock_photos: bool = False
        description_red_flags: tuple = ()
        missing_parts: tuple = ()

    return _Neutral()


def utcnow() -> datetime:
    return datetime.now(UTC)
