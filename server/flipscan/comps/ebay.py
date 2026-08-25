"""eBay comps.

eBay is the best public source of resale truth there is, because completed
listings record what somebody actually paid rather than what a seller hoped
for. Two endpoints, in descending order of usefulness:

* **Marketplace Insights** — real sold prices from the last 90 days. This is
  the gold standard, and access requires a separate application to eBay
  beyond the standard developer keys.
* **Browse** — currently active listings. Free with any developer account,
  but these are asking prices, so they get a haircut before they're used.

Both are optional. With no eBay keys at all the engine falls back to internal
history and category priors, at correspondingly lower confidence.
"""

from __future__ import annotations

import base64
import logging
import time

import httpx

from ..config import Settings
from .base import CompProvider, CompResult, CompSample, summarize

log = logging.getLogger(__name__)

OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
INSIGHTS_URL = "https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search"

SCOPE = "https://api.ebay.com/oauth/api_scope"

# Active asking prices run well above final sale prices: sellers list high,
# accept offers, and the listings that never sell stay visible forever while
# the ones that sold vanish. This haircut converts "asking" to "realistic".
ASKING_TO_SOLD = 0.78


class EbayCompProvider(CompProvider):
    name = "ebay"
    weight = 2.0  # real sold data outranks everything else

    def __init__(self, settings: Settings):
        self.settings = settings
        self._token: str | None = None
        self._token_expires: float = 0.0
        self._client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.sources.ebay_client_id
            and self.settings.sources.ebay_client_secret
        )

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=20.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get_token(self) -> str | None:
        """Client-credentials token, cached until shortly before expiry."""
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        if not self.configured:
            return None

        creds = base64.b64encode(
            f"{self.settings.sources.ebay_client_id}:"
            f"{self.settings.sources.ebay_client_secret}".encode()
        ).decode()

        try:
            client = await self._http()
            response = await client.post(
                OAUTH_URL,
                headers={
                    "Authorization": f"Basic {creds}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials", "scope": SCOPE},
            )
            response.raise_for_status()
            payload = response.json()
            self._token = payload["access_token"]
            self._token_expires = time.time() + float(payload.get("expires_in", 7200))
            return self._token
        except Exception as exc:
            log.warning("eBay auth failed: %s", exc)
            return None

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.settings.sources.ebay_marketplace,
            "Content-Type": "application/json",
        }

    async def lookup(self, query: str, *, category: str | None = None,
                     hint_price: float = 0.0) -> CompResult:
        """Sold comps when we have Insights access, active asks otherwise."""
        if not self.configured:
            return CompResult(provider=self.name, query_used=query,
                              error="eBay API keys not configured")

        token = await self._get_token()
        if not token:
            return CompResult(provider=self.name, query_used=query,
                              error="eBay auth failed")

        if self.settings.sources.ebay_has_insights_access:
            result = await self._lookup_sold(query, token)
            if result.ok:
                return result
            log.info("Insights returned nothing for %r, falling back to active", query)

        return await self._lookup_active(query, token)

    async def _lookup_sold(self, query: str, token: str) -> CompResult:
        try:
            client = await self._http()
            response = await client.get(
                INSIGHTS_URL,
                headers=self._headers(token),
                params={"q": query, "limit": 50,
                        "filter": "lastSoldDate:[2024-01-01T00:00:00Z..]"},
            )
            if response.status_code == 403:
                return CompResult(
                    provider="ebay_sold", query_used=query,
                    error="no Marketplace Insights access — apply at "
                          "developer.ebay.com, or leave "
                          "FLIPSCAN_SOURCES__EBAY_HAS_INSIGHTS_ACCESS=false",
                )
            response.raise_for_status()
            items = response.json().get("itemSales", [])
        except Exception as exc:
            return CompResult(provider="ebay_sold", query_used=query, error=str(exc))

        samples = [
            CompSample(
                title=item.get("title", ""),
                price=float(item.get("lastSoldPrice", {}).get("value", 0) or 0),
                url=item.get("itemWebUrl", ""),
                sold=True,
                sold_date=item.get("lastSoldDate", ""),
                condition=item.get("condition", ""),
            )
            for item in items
        ]

        result = summarize(
            "ebay_sold", query, samples,
            note=f"{len(samples)} sold on eBay in the last 90 days",
        )
        # Sold data carries its own velocity signal, which is worth as much as
        # the price: a category with 40 sales in 90 days moves.
        if result.ok and len(samples) >= 5:
            result.est_days_to_sell = max(3, int(90 / max(1, len(samples)) * 2))
        return result

    async def _lookup_active(self, query: str, token: str) -> CompResult:
        try:
            client = await self._http()
            response = await client.get(
                BROWSE_URL,
                headers=self._headers(token),
                params={
                    "q": query,
                    "limit": 50,
                    # Used goods only — a new-in-box listing is not a comp for
                    # a secondhand item and would inflate the estimate badly.
                    "filter": "conditionIds:{3000|4000|5000|6000}",
                    "sort": "price",
                },
            )
            response.raise_for_status()
            items = response.json().get("itemSummaries", []) or []
        except Exception as exc:
            return CompResult(provider="ebay_active", query_used=query, error=str(exc))

        samples = [
            CompSample(
                title=item.get("title", ""),
                price=float(item.get("price", {}).get("value", 0) or 0),
                url=item.get("itemWebUrl", ""),
                sold=False,
                condition=item.get("condition", ""),
            )
            for item in items
        ]

        result = summarize(
            "ebay_active", query, samples,
            asking_to_sold=ASKING_TO_SOLD,
            note=f"{len(samples)} active eBay listings, discounted "
                 f"{(1 - ASKING_TO_SOLD):.0%} from asking",
        )
        # Asking prices are genuinely weaker evidence; say so numerically.
        result.confidence *= 0.75
        result.weight_hint = 1.0
        return result
