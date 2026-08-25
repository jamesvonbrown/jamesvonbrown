"""Parsing and deduplication — the layer most likely to break silently when
Facebook reshapes its markup."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from flipscan.collectors import DemoCollector, parse_pasted_text
from flipscan.collectors.base import (
    make_fingerprint,
    normalize_location,
    parse_price,
    price_bucket,
    title_tokens,
)
from flipscan.collectors.facebook import (
    build_search_url,
    extract_item_ids,
    looks_like_login_wall,
    parse_detail_payload,
)
from flipscan.collectors.manual import identify_source

FIXTURES = Path(__file__).parent / "fixtures"


class TestPriceParsing:
    @pytest.mark.parametrize("raw,expected", [
        ("$1,200", 1200.0), ("FREE", 0.0), ("$45.50", 45.5),
        ("1200 USD", 1200.0), ("", 0.0), (None, 0.0), (850, 850.0),
        ("Free to good home", 0.0), ("$0", 0.0),
    ])
    def test_parses(self, raw, expected):
        assert parse_price(raw) == expected


class TestFingerprint:
    def test_haggling_does_not_create_a_duplicate(self):
        a = make_fingerprint("Herman Miller Aeron Chair - Size B $550 OBO", 550, "Beaverton, OR")
        b = make_fingerprint("herman miller aeron chair size b", 545, "Beaverton OR")
        assert a == b

    def test_cross_posted_listing_matches(self):
        a = make_fingerprint("DeWalt 20V Drill Set 250$", 250, "Gresham")
        b = make_fingerprint("Dewalt 20v drill set - $250 firm", 250, "Gresham, OR")
        assert a == b

    def test_facebook_distance_suffix_is_ignored(self):
        a = make_fingerprint("Trek Domane 56cm", 900, "Portland, OR · 4 miles away")
        b = make_fingerprint("Trek Domane 56cm", 900, "Portland")
        assert a == b

    def test_different_cities_are_different_items(self):
        a = make_fingerprint("Aeron Chair Size B", 550, "Beaverton, OR")
        b = make_fingerprint("Aeron Chair Size B", 550, "Salem, OR")
        assert a != b

    def test_size_designator_is_preserved(self):
        """Size B and Size A are different chairs at different prices."""
        a = make_fingerprint("Herman Miller Aeron Size A", 550, "Beaverton")
        b = make_fingerprint("Herman Miller Aeron Size B", 550, "Beaverton")
        assert a != b

    def test_model_numbers_stay_distinct(self):
        a = make_fingerprint("Canon 5D Mark IV body", 900, "Portland")
        b = make_fingerprint("Canon 5D Mark III body", 900, "Portland")
        assert a != b

    def test_order_of_magnitude_separates(self):
        a = make_fingerprint("Aeron Chair Size B", 550, "Beaverton")
        b = make_fingerprint("Aeron Chair Size B", 55, "Beaverton")
        assert a != b

    def test_price_bucket_is_stable_across_a_haggle(self):
        assert price_bucket(545) == price_bucket(550)

    def test_embedded_price_is_stripped_from_tokens(self):
        assert "550" not in title_tokens("Aeron Chair $550 OBO", price=550)

    def test_marketplace_filler_is_dropped(self):
        tokens = title_tokens("BEAUTIFUL vintage rare mid century teak credenza", keep=7)
        assert "beautiful" not in tokens and "vintage" not in tokens
        assert "teak" in tokens and "credenza" in tokens


class TestLocationNormalization:
    @pytest.mark.parametrize("raw,expected", [
        ("Gresham", "gresham"),
        ("Gresham, OR", "gresham"),
        ("Gresham, OR 97030", "gresham"),
        ("Beaverton, OR · 8 miles away", "beaverton"),
        ("Portland, OR 97202 - 3.2 mi away", "portland"),
        ("Lake Oswego", "lake oswego"),
        (None, ""),
    ])
    def test_normalizes(self, raw, expected):
        assert normalize_location(raw) == expected


class TestFacebookParser:
    def test_extracts_ids_and_dedupes(self):
        ids = extract_item_ids(FIXTURES.joinpath("fb_search.html").read_text())
        assert ids == ["111111", "222222", "333333"]

    def test_detects_a_login_wall(self):
        assert looks_like_login_wall(FIXTURES.joinpath("fb_login_wall.html").read_text())
        assert not looks_like_login_wall(FIXTURES.joinpath("fb_item.html").read_text())

    def test_login_wall_returns_none_not_garbage(self):
        html = FIXTURES.joinpath("fb_login_wall.html").read_text()
        assert parse_detail_payload(html, "url", "1") is None

    def test_parses_the_embedded_json(self):
        listing = parse_detail_payload(
            FIXTURES.joinpath("fb_item.html").read_text(),
            "https://www.facebook.com/marketplace/item/1234567890/", "1234567890")
        assert listing.price == 550.0
        assert listing.location_text == "Beaverton, OR"
        assert listing.seller_name == "Dana R."
        assert listing.posted_at is not None
        assert len([u for u in listing.image_urls if "photo" in u]) == 3
        assert "Aeron" in listing.title

    def test_falls_back_to_meta_tags(self):
        """When the JSON can't be parsed, OpenGraph still yields a usable listing."""
        listing = parse_detail_payload(
            FIXTURES.joinpath("fb_item_meta_only.html").read_text(),
            "https://www.facebook.com/marketplace/item/555/", "555")
        assert listing.title == "DeWalt 20V Impact Driver"
        assert listing.price == 85.0

    def test_price_prefix_is_stripped_from_the_title(self):
        listing = parse_detail_payload(
            FIXTURES.joinpath("fb_item_meta_only.html").read_text(),
            "u", "555")
        assert "$" not in listing.title

    def test_search_url_carries_the_filters(self):
        url = build_search_url("aeron chair", lat=45.5152, lon=-122.6784,
                               radius_miles=40, min_price=80, max_price=1200)
        assert "minPrice=80" in url and "maxPrice=1200" in url
        assert "radius=40" in url and "sortBy=creation_time_descend" in url


class TestManualEntry:
    def test_parses_a_pasted_listing(self):
        listing = parse_pasted_text(
            "Vintage Teak Credenza\nAsking 275 obo\nLocation: Sellwood\nDanish modern.",
            url="https://www.facebook.com/marketplace/item/998877665544/")
        assert listing.source == "facebook"
        assert listing.external_id == "998877665544"
        assert listing.price == 275.0
        assert listing.location_text == "Sellwood"

    def test_explicit_values_beat_scraped_ones(self):
        listing = parse_pasted_text("Asking 275", price=300.0, title="Override")
        assert listing.price == 300.0 and listing.title == "Override"

    @pytest.mark.parametrize("url,source", [
        ("https://www.facebook.com/marketplace/item/123/", "facebook"),
        ("https://portland.craigslist.org/mlt/tls/7712345678.html", "craigslist"),
        ("https://offerup.com/item/detail/abc-123", "offerup"),
        ("https://shop.example.com/x", "manual"),
    ])
    def test_identifies_the_source(self, url, source):
        assert identify_source(url)[0] == source


class TestDemoCollector:
    def test_returns_usable_listings(self, settings):
        result = asyncio.run(DemoCollector(settings).collect([], {}))
        assert len(result.listings) == 8
        assert all(listing.is_usable() for listing in result.listings)

    def test_covers_the_cases_that_matter(self, settings):
        """The fixtures must include a scam and a free item, or the pipeline
        tests only ever exercise the happy path."""
        result = asyncio.run(DemoCollector(settings).collect([], {}))
        text = " ".join(listing.description.lower() for listing in result.listings)
        assert "zelle" in text
        assert any(listing.price == 0 for listing in result.listings)
