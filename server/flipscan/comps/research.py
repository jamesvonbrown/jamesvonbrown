"""Web research fallback — Claude with search, for items the APIs can't price.

Structured comp sources handle mainstream goods well and fall over on
everything else: a discontinued Snow Peak cookset, a regional furniture
maker, a tool model that was renamed three times. eBay returns nothing, the
local history is empty, and a category prior is barely better than a shrug.

This provider is the last resort for exactly those cases. It's the slowest
and most expensive path, so the engine only reaches for it when the cheaper
providers have already failed and the listing looks like it might be worth
real money.
"""

from __future__ import annotations

import json
import logging

from ..config import Settings
from .base import CompProvider, CompResult, CompSample

log = logging.getLogger(__name__)

# Opus 5 / Sonnet 5 / Opus 4.6+ support the dynamic-filtering search tool.
WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 5,
    "user_location": {
        "type": "approximate",
        "city": "Portland",
        "region": "Oregon",
        "country": "US",
    },
}

RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "found_comparables": {
            "type": "boolean",
            "description": "True only if you found actual prices for this item "
                           "or a genuinely equivalent one.",
        },
        "resale_low": {"type": "number", "description": "Conservative resale, USD."},
        "resale_mid": {"type": "number", "description": "Most likely resale, USD."},
        "resale_high": {"type": "number", "description": "Optimistic resale, USD."},
        "retail_new": {"type": "number", "description": "Current new price, 0 if unknown."},
        "confidence": {
            "type": "number",
            "description": "0-1. Be strict: 0.3 or below if you're extrapolating "
                           "from a similar-but-different product.",
        },
        "est_days_to_sell": {
            "type": "integer",
            "description": "Typical days to sell locally at the mid price.",
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "price": {"type": "number"},
                    "url": {"type": "string"},
                    "source": {"type": "string"},
                    "sold": {"type": "boolean"},
                },
                "required": ["title", "price", "url", "source", "sold"],
                "additionalProperties": False,
            },
            "description": "The specific listings or sales you based this on. "
                           "Empty if you found nothing — do not invent entries.",
        },
        "reasoning": {"type": "string", "description": "Two sentences maximum."},
        "demand_notes": {
            "type": "string",
            "description": "Anything about demand that affects the flip: "
                           "seasonality, a recall, a discontinued model, a "
                           "newer version that just launched.",
        },
    },
    "required": [
        "found_comparables", "resale_low", "resale_mid", "resale_high",
        "retail_new", "confidence", "est_days_to_sell", "evidence",
        "reasoning", "demand_notes",
    ],
    "additionalProperties": False,
}

SYSTEM = """\
You research secondhand resale values for a reseller in Portland, Oregon.

Search for what this item ACTUALLY SELLS FOR used, not its retail price. \
Completed eBay sales, current Marketplace and Craigslist listings, and \
enthusiast forums are all better evidence than a manufacturer's page.

Be conservative and be honest about uncertainty. Setting found_comparables \
to false costs her nothing — the system falls back to a category estimate \
and marks the deal as unverified. Inventing a number she then drives across \
town on costs her real money. If you can only find the new price, say so, \
return found_comparables false, and put the retail figure in retail_new.

Never fabricate an evidence entry. An empty evidence array with \
found_comparables false is a good answer when the searches came up dry."""


class WebResearchCompProvider(CompProvider):
    name = "web_research"
    weight = 1.0

    def __init__(self, settings: Settings, client=None):
        self.settings = settings
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.anthropic_api_key and self.settings.ai.enable_web_research
        )

    async def lookup(self, query: str, *, category: str | None = None,
                     hint_price: float = 0.0) -> CompResult:
        result = CompResult(provider=self.name, query_used=query)

        if not self.configured:
            result.error = "web research disabled or no API key"
            return result

        try:
            client = self._client
            if client is None:
                import anthropic

                client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)

            prompt = (
                f"What does this sell for used in the Portland, Oregon area?\n\n"
                f"Item: {query}\n"
                f"Category: {category or 'unknown'}\n"
                f"Seller is asking: ${hint_price:,.2f}\n\n"
                f"Find real comparable sales and give a resale range."
            )

            messages: list[dict] = [{"role": "user", "content": prompt}]
            response = None

            # Server-tool turns can stop with `pause_turn` partway through.
            # Resuming means sending the partial turn back and letting it
            # continue; without this the answer is silently truncated.
            for _ in range(4):
                response = await client.messages.create(
                    model=self.settings.ai.model,
                    max_tokens=8000,
                    system=SYSTEM,
                    thinking={"type": "adaptive"},
                    tools=[WEB_SEARCH_TOOL],
                    output_config={
                        "effort": self.settings.ai.effort,
                        "format": {"type": "json_schema", "schema": RESEARCH_SCHEMA},
                    },
                    messages=messages,
                )
                if response.stop_reason != "pause_turn":
                    break
                messages.append({"role": "assistant", "content": response.content})

            if response is None:
                result.error = "no response"
                return result

            if response.stop_reason == "refusal":
                result.error = "model declined the request"
                return result

            text = next(
                (b.text for b in response.content if getattr(b, "type", "") == "text"),
                None,
            )
            if not text:
                result.error = "no structured output in response"
                return result

            data = json.loads(text)

        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            log.warning("web research failed for %r: %s", query, exc)
            return result

        if not data.get("found_comparables"):
            result.error = "no comparables found online"
            result.note = data.get("reasoning", "")
            # Even a failed lookup can hand back a retail anchor, which the
            # category prior turns into a much better estimate than the ask.
            result.high = float(data.get("retail_new") or 0.0)
            return result

        result.median = float(data.get("resale_mid") or 0.0)
        result.low = float(data.get("resale_low") or result.median * 0.75)
        result.high = float(data.get("resale_high") or result.median * 1.25)
        result.confidence = min(1.0, max(0.0, float(data.get("confidence") or 0.0)))
        result.est_days_to_sell = int(data.get("est_days_to_sell") or 0) or None

        result.samples = [
            CompSample(
                title=str(e.get("title", ""))[:160],
                price=float(e.get("price") or 0),
                url=str(e.get("url", "")),
                sold=bool(e.get("sold")),
                condition=str(e.get("source", "")),
                relevance=0.85,
            )
            for e in (data.get("evidence") or [])
            if float(e.get("price") or 0) > 0
        ]
        result.sample_size = len(result.samples)

        # A confident-sounding answer with nothing behind it is the failure
        # mode that matters here, so cap confidence by the evidence count.
        if result.sample_size == 0:
            result.confidence = min(result.confidence, 0.25)
        elif result.sample_size < 3:
            result.confidence = min(result.confidence, 0.5)

        notes = [data.get("reasoning", ""), data.get("demand_notes", "")]
        result.note = " ".join(n for n in notes if n).strip()[:400]
        return result
