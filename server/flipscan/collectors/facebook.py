"""Facebook Marketplace collector.

READ docs/LEGAL.md BEFORE RUNNING THIS. Short version: Marketplace has no
public API, and automating a logged-in session is against Meta's Terms of
Service. This module is written for one person shopping her own local market
at a human pace, and it enforces that with hard per-scan ceilings and real
delays. It is not, and must not become, a bulk harvester. Use a secondary
Facebook account, not the one the business sells from.

The parsing is deliberately split from the browser driving:

* `parse_detail_payload` and friends are pure functions over strings. They're
  unit-tested against fixtures and can be fixed without a browser.
* `FacebookMarketplaceCollector` handles navigation, pacing, and screenshots.

That split matters because Facebook reshapes its markup regularly. When this
breaks — and it will — the failure is almost always in the pure layer, where
you can reproduce it from a saved HTML file in seconds.
"""

from __future__ import annotations

import asyncio
import html as html_lib
import json
import logging
import random
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from ..config import Settings
from .base import Collector, CollectResult, RawListing, parse_price

log = logging.getLogger(__name__)

BASE = "https://www.facebook.com"
ITEM_URL_RE = re.compile(r"/marketplace/item/(\d+)")

# Facebook embeds its data in these. `data-sjs` is the current marker; the
# plain `application/json` form is kept as a fallback because both have been
# in play at different times.
SCRIPT_JSON_RE = re.compile(
    r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
    re.DOTALL,
)
META_RE = re.compile(
    r'<meta[^>]+property="(og:[^"]+)"[^>]+content="([^"]*)"', re.I
)

# Signals that we're looking at a login wall rather than a listing.
LOGIN_WALL_MARKERS = (
    "You must log in to continue",
    "login_form",
    "Log in to Facebook",
    'name="email"',
)


# --------------------------------------------------------------------------
# Pure helpers — no browser required, unit-testable
# --------------------------------------------------------------------------
def build_search_url(
    query: str,
    *,
    location_id: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_miles: int = 40,
    min_price: float | None = None,
    max_price: float | None = None,
    days_since_listed: int | None = 1,
    sort_newest: bool = True,
) -> str:
    """Marketplace search URL.

    `days_since_listed=1` is the default because the whole point of running
    hourly is catching listings in their first hours, before someone else
    does. Widen it for the first run when the database is empty.
    """
    path = f"{BASE}/marketplace/{location_id}/search" if location_id else f"{BASE}/marketplace/search"

    params: dict[str, Any] = {"query": query}
    if radius_miles:
        params["radius"] = radius_miles
    if lat is not None and lon is not None and not location_id:
        params["latitude"] = f"{lat:.4f}"
        params["longitude"] = f"{lon:.4f}"
    if min_price is not None:
        params["minPrice"] = int(min_price)
    if max_price is not None:
        params["maxPrice"] = int(max_price)
    if days_since_listed:
        params["daysSinceListed"] = days_since_listed
    if sort_newest:
        params["sortBy"] = "creation_time_descend"
    params["exact"] = "false"

    return f"{path}?{urlencode(params)}"


def extract_item_ids(html: str) -> list[str]:
    """Listing IDs from a search results page, first-seen order preserved."""
    seen, out = set(), []
    for match in ITEM_URL_RE.finditer(html or ""):
        item_id = match.group(1)
        if item_id not in seen:
            seen.add(item_id)
            out.append(item_id)
    return out


def looks_like_login_wall(html: str) -> bool:
    if not html:
        return False
    head = html[:20000]
    return sum(marker in head for marker in LOGIN_WALL_MARKERS) >= 2


def iter_json_blobs(html: str) -> list[Any]:
    """Every embedded JSON payload we can parse out of the page."""
    blobs: list[Any] = []
    for raw in SCRIPT_JSON_RE.findall(html or ""):
        raw = raw.strip()
        if not raw or raw[0] not in "{[":
            continue
        try:
            blobs.append(json.loads(raw))
        except (json.JSONDecodeError, ValueError):
            continue
    return blobs


def deep_find(node: Any, key: str, _depth: int = 0) -> Any:
    """First value for `key` anywhere in a nested structure.

    Facebook's Relay payloads are deeply nested and the path to any given
    field changes between deploys, but the field *names* are stable. Searching
    by name survives reshuffles that would break a hardcoded path.
    """
    if _depth > 30:
        return None
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = deep_find(value, key, _depth + 1)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = deep_find(item, key, _depth + 1)
            if found is not None:
                return found
    return None


def deep_find_all(node: Any, key: str, _depth: int = 0, _acc: list | None = None) -> list:
    """Every value for `key`, for repeated fields like photo URIs."""
    acc = _acc if _acc is not None else []
    if _depth > 30:
        return acc
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                acc.append(v)
            deep_find_all(v, key, _depth + 1, acc)
    elif isinstance(node, list):
        for item in node:
            deep_find_all(item, key, _depth + 1, acc)
    return acc


def _first_str(*candidates: Any) -> str | None:
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
        if isinstance(c, dict):
            for key in ("text", "uri", "name", "formatted_amount"):
                v = c.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    return None


def parse_meta_tags(html: str) -> dict[str, str]:
    """OpenGraph tags, HTML-entity decoded.

    Facebook emits entities here (`&middot;`, `&amp;`, `&#039;`), so the raw
    attribute text is not what a human sees. Decoding matters: the price
    separator in `og:title` arrives as `&middot;`, and a price prefix that
    doesn't get stripped ends up polluting both the comp query and the
    dedupe fingerprint.
    """
    return {k: html_lib.unescape(v) for k, v in META_RE.findall(html or "")}


def parse_detail_payload(html: str, url: str, item_id: str) -> RawListing | None:
    """Build a RawListing from a Marketplace item page.

    Tries embedded JSON first (richest and most stable), then falls back to
    OpenGraph meta tags, which are thinner but survive almost anything.
    """
    if looks_like_login_wall(html):
        return None

    blobs = iter_json_blobs(html)
    meta = parse_meta_tags(html)

    title = None
    description = ""
    price = 0.0
    currency = "USD"
    location_text = None
    seller_name = None
    seller_id = None
    posted_at = None
    images: list[str] = []

    for blob in blobs:
        title = title or _first_str(
            deep_find(blob, "marketplace_listing_title"),
            deep_find(blob, "custom_title"),
        )

        if not description:
            description = _first_str(
                deep_find(blob, "redacted_description"),
                deep_find(blob, "listing_description"),
                deep_find(blob, "description"),
            ) or ""

        if not price:
            price_node = deep_find(blob, "listing_price") or deep_find(blob, "price")
            if isinstance(price_node, dict):
                amount = price_node.get("amount") or price_node.get("amount_with_offset")
                offset = price_node.get("offset")
                if amount is not None:
                    try:
                        value = float(amount)
                        # `amount_with_offset` is in minor units (cents).
                        if offset:
                            value /= 10 ** int(offset)
                        elif "amount_with_offset" in price_node and "amount" not in price_node:
                            value /= 100.0
                        price = value
                    except (TypeError, ValueError):
                        price = parse_price(price_node.get("formatted_amount"))
                else:
                    price = parse_price(price_node.get("formatted_amount"))
                currency = price_node.get("currency") or currency
            elif price_node is not None:
                price = parse_price(price_node)

        if not location_text:
            loc = deep_find(blob, "reverse_geocode") or deep_find(blob, "location_text")
            if isinstance(loc, dict):
                city = _first_str(loc.get("city"), loc.get("city_page"))
                state = _first_str(loc.get("state"))
                location_text = ", ".join(p for p in (city, state) if p) or None
            else:
                location_text = _first_str(loc)

        if not seller_name:
            seller = deep_find(blob, "marketplace_listing_seller") or deep_find(blob, "seller")
            if isinstance(seller, dict):
                seller_name = _first_str(seller.get("name"))
                seller_id = seller.get("id")

        if posted_at is None:
            ts = deep_find(blob, "creation_time") or deep_find(blob, "created_time")
            if isinstance(ts, (int, float)) and ts > 1_000_000_000:
                posted_at = datetime.fromtimestamp(float(ts), tz=UTC)

        for uri in deep_find_all(blob, "uri"):
            if isinstance(uri, str) and "scontent" in uri and uri not in images:
                images.append(uri)

    # ---- OpenGraph fallback -----------------------------------------------
    if not title:
        title = meta.get("og:title")
    if not description:
        description = meta.get("og:description", "")
    description = html_lib.unescape(description or "")
    if not images and meta.get("og:image"):
        images = [meta["og:image"]]
    if not price:
        # Marketplace often puts the price in the og:title: "$550 · Aeron Chair"
        price = parse_price(title or "")

    if not title:
        return None

    # og:title carries the price prefix; strip it so it doesn't pollute the
    # title tokens used for fingerprinting and comp queries.
    title = html_lib.unescape(title)
    title = re.sub(r"^\s*\$[\d,.]+\s*[·•|\u2013\u2014-]\s*", "", title).strip()

    return RawListing(
        source="facebook",
        external_id=item_id,
        url=url,
        title=title,
        price=price,
        currency=currency,
        description=description,
        location_text=location_text,
        posted_at=posted_at,
        seller_name=seller_name,
        seller_url=f"{BASE}/{seller_id}" if seller_id else None,
        image_urls=images[:12],
        raw={
            "meta": meta,
            "json_blob_count": len(blobs),
            "image_count": len(images),
        },
    )


def is_stale(posted_at: datetime | None, max_age_days: int = 45) -> bool:
    """Old listings that never sold are usually overpriced, not opportunities."""
    if posted_at is None:
        return False
    return posted_at < datetime.now(UTC) - timedelta(days=max_age_days)


# --------------------------------------------------------------------------
# Browser-driven collector
# --------------------------------------------------------------------------
class FacebookMarketplaceCollector(Collector):
    """Drives a persistent logged-in Chromium profile.

    She logs in once with `flipscan login`; the session cookie lives in the
    profile directory from then on. Nothing about credentials is stored by
    this code — it just reuses the browser profile, the same way leaving a tab
    open would.
    """

    name = "facebook"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._playwright = None
        self._context = None

    # -- browser lifecycle --------------------------------------------------
    async def _ensure_browser(self):
        if self._context is not None:
            return self._context

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - depends on extras
            raise RuntimeError(
                "Playwright isn't installed. Run:\n"
                "  pip install 'flipscan[browser]' && playwright install chromium"
            ) from exc

        profile_dir = Path(self.settings.sources.browser_profile_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=self.settings.sources.browser_headless,
            viewport={"width": 1366, "height": 900},
            locale="en-US",
            timezone_id=self.settings.scan.timezone,
            args=["--disable-blink-features=AutomationControlled"],
        )
        return self._context

    async def close(self) -> None:
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def _pause(self) -> None:
        low, high = self.settings.scan.delay_between_actions
        await asyncio.sleep(random.uniform(low, high))

    # -- collection ---------------------------------------------------------
    async def collect(self, watchlists: list, limits: dict) -> CollectResult:
        result = CollectResult()
        max_searches = limits.get("max_searches", self.settings.scan.max_searches_per_scan)
        max_listings = limits.get("max_listings", self.settings.scan.max_listings_per_scan)
        max_details = limits.get("max_details", self.settings.scan.max_detail_fetches_per_scan)
        known_ids: set[str] = set(limits.get("known_external_ids") or ())
        days_since = limits.get("days_since_listed", 1)

        try:
            context = await self._ensure_browser()
        except RuntimeError as exc:
            result.errors.append(str(exc))
            return result

        page = await context.new_page()
        # Block heavy assets we never read. Cuts bandwidth and page load time
        # substantially, which also means fewer requests hitting Facebook.
        await page.route(
            re.compile(r"\.(mp4|webm|woff2?|ttf)(\?|$)"),
            lambda route: route.abort(),
        )

        # Highest-priority watchlists first, so the ceiling truncates the ones
        # that matter least rather than whatever happened to sort last.
        ordered = sorted(
            (w for w in watchlists if getattr(w, "enabled", True)),
            key=lambda w: getattr(w, "priority", 5),
        )[:max_searches]

        candidates: list[tuple[str, Any]] = []
        try:
            for watchlist in ordered:
                if len(candidates) >= max_listings:
                    break
                try:
                    ids = await self._run_search(page, watchlist, days_since)
                    result.searches_run += 1
                    fresh = [i for i in ids if i not in known_ids]
                    for item_id in fresh:
                        known_ids.add(item_id)
                        candidates.append((item_id, watchlist))
                    result.notes.append(
                        f"{watchlist.name}: {len(ids)} results, {len(fresh)} new"
                    )
                except Exception as exc:  # one bad search shouldn't kill the scan
                    log.warning("search failed for %s: %s", watchlist.name, exc)
                    result.errors.append(f"search '{watchlist.name}': {exc}")
                await self._pause()

            for item_id, watchlist in candidates[:max_details]:
                try:
                    listing = await self._fetch_detail(page, item_id)
                    if listing and listing.is_usable():
                        listing.category_hint = getattr(watchlist, "category", None)
                        listing.watchlist_id = getattr(watchlist, "id", None)
                        result.listings.append(listing)
                except Exception as exc:
                    log.warning("detail fetch failed for %s: %s", item_id, exc)
                    result.errors.append(f"item {item_id}: {exc}")
                await self._pause()
        finally:
            await page.close()

        if result.searches_run and not result.listings:
            result.errors.append(
                "Searches ran but produced zero listings. Usually this means the "
                "session logged out — run `flipscan login` — or Facebook changed "
                "its markup, in which case check the saved HTML in data/debug/."
            )
        return result

    async def _run_search(self, page, watchlist, days_since: int) -> list[str]:
        market = self.settings.market
        url = build_search_url(
            watchlist.query,
            location_id=market.fb_location_id,
            lat=market.center_lat,
            lon=market.center_lon,
            radius_miles=market.search_radius_miles,
            min_price=watchlist.min_price,
            max_price=watchlist.max_price,
            days_since_listed=days_since,
        )
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        await asyncio.sleep(random.uniform(2.0, 3.5))

        html = await page.content()
        if looks_like_login_wall(html):
            raise RuntimeError("not logged in — run `flipscan login`")

        # One scroll picks up the second screen of results without turning this
        # into an infinite crawler.
        await page.mouse.wheel(0, 2400)
        await asyncio.sleep(random.uniform(1.2, 2.2))
        html = await page.content()

        return extract_item_ids(html)

    async def _fetch_detail(self, page, item_id: str) -> RawListing | None:
        url = f"{BASE}/marketplace/item/{item_id}/"
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        await asyncio.sleep(random.uniform(1.5, 2.8))

        html = await page.content()
        listing = parse_detail_payload(html, url, item_id)
        if listing is None:
            self._save_debug_html(item_id, html)
            return None

        # Full-page screenshot: this is what the listing actually said, at the
        # moment we saw it. Sellers edit and delete listings constantly, and
        # having the original is worth the few hundred KB.
        try:
            shots = Path(self.settings.media_dir) / "screenshots"
            shots.mkdir(parents=True, exist_ok=True)
            path = shots / f"fb-{item_id}.png"
            await page.screenshot(path=str(path), full_page=True)
            listing.screenshot_path = str(path)
        except Exception as exc:
            log.debug("screenshot failed for %s: %s", item_id, exc)

        return listing

    def _save_debug_html(self, item_id: str, html: str) -> None:
        """Keep unparseable pages so the pure parser can be fixed offline."""
        try:
            debug = Path(self.settings.media_dir).parent / "debug"
            debug.mkdir(parents=True, exist_ok=True)
            (debug / f"unparsed-{item_id}.html").write_text(html[:500_000], encoding="utf-8")
        except Exception:
            pass
