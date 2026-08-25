"""Collector registry.

Adding a source means writing one Collector subclass and registering it here;
nothing in the pipeline changes.
"""

from __future__ import annotations

import logging

from ..config import Settings
from .base import (
    Collector,
    CollectResult,
    RawListing,
    make_fingerprint,
    normalize_location,
    normalize_text,
    parse_price,
    price_bucket,
    title_tokens,
)
from .demo import DemoCollector
from .manual import ManualCollector, identify_source, parse_pasted_text

log = logging.getLogger(__name__)

#: Name -> factory. Facebook is imported lazily because it pulls in Playwright,
#: which is a heavy optional dependency the demo and manual paths don't need.
_REGISTRY: dict[str, callable] = {
    "demo": DemoCollector,
    "manual": ManualCollector,
}

# One shared manual collector, so an API submission and the scan that picks
# it up are talking to the same queue.
_manual_singleton: ManualCollector | None = None


def get_manual_collector(settings: Settings) -> ManualCollector:
    global _manual_singleton
    if _manual_singleton is None:
        _manual_singleton = ManualCollector(settings)
    return _manual_singleton


def build_collector(name: str, settings: Settings) -> Collector | None:
    """Instantiate one collector by name, or None if unavailable."""
    if name == "manual":
        return get_manual_collector(settings)

    if name == "facebook":
        try:
            from .facebook import FacebookMarketplaceCollector
        except ImportError as exc:
            log.error("facebook collector unavailable: %s", exc)
            return None
        return FacebookMarketplaceCollector(settings)

    factory = _REGISTRY.get(name)
    if factory is None:
        log.warning("unknown collector %r — check FLIPSCAN_SOURCES__COLLECTORS", name)
        return None
    return factory(settings)


def build_collectors(settings: Settings) -> list[Collector]:
    """Every configured collector, plus manual (always on, costs nothing)."""
    names = list(settings.sources.collectors)
    if "manual" not in names:
        names.append("manual")

    built = [c for c in (build_collector(n, settings) for n in names) if c is not None]
    if not built:
        log.error("no collectors could be built from %r", names)
    return built


__all__ = [
    "Collector",
    "CollectResult",
    "RawListing",
    "DemoCollector",
    "ManualCollector",
    "build_collector",
    "build_collectors",
    "get_manual_collector",
    "identify_source",
    "parse_pasted_text",
    "make_fingerprint",
    "normalize_location",
    "normalize_text",
    "parse_price",
    "price_bucket",
    "title_tokens",
]
