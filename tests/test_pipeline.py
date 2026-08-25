"""End-to-end behaviour: staged filtering, dedupe, price tracking, and the
cost control that keeps this affordable."""

from __future__ import annotations

import asyncio
from datetime import UTC

import pytest
from flipscan.collectors import DemoCollector
from flipscan.db import session_scope
from flipscan.models import CompSet, Deal, Listing, PriceObservation
from flipscan.notify.base import DealAlert, in_quiet_hours
from flipscan.pipeline import quick_screen, run_scan
from flipscan.safety import build_brief
from sqlmodel import select


def scan(settings, collector=None, **kwargs):
    return asyncio.run(run_scan(
        settings, trigger="test",
        collectors=[collector or DemoCollector(settings)],
        notify=False, **kwargs))


class TestStagedFiltering:
    def test_a_full_scan_finds_deals(self, settings):
        run = scan(settings)
        assert run.listings_seen == 8
        assert run.new_listings == 8
        assert run.deals_found > 0
        assert run.ok

    def test_the_scam_listing_is_rejected_before_any_spend(self, settings):
        """The whole point of the staged design: obvious rejects cost $0."""
        scan(settings)
        with session_scope() as session:
            scam = session.exec(
                select(Listing).where(Listing.title.like("%MacBook%"))).first()
            assert scam is not None, "the listing should still be recorded"
            # Never reached the comps stage, so no valuation was ever computed.
            comps = session.exec(
                select(CompSet).where(CompSet.listing_id == scam.id)).all()
            assert comps == []
            deals = session.exec(
                select(Deal).where(Deal.listing_id == scam.id)).all()
            assert deals == []

    def test_no_ai_spend_without_a_key(self, settings):
        run = scan(settings)
        assert run.ai_cost_usd == 0.0

    def test_screen_rejects_what_cannot_possibly_work(self, settings):
        from flipscan.enrich.description import analyze_description

        class Fake:
            title = "Cheap thing"
            description = "nothing special"
            price = 20.0
            category_hint = "electronics"

        findings = analyze_description(Fake.title, Fake.description, Fake.price)
        keep, reason = quick_screen(Fake, findings, settings, 5.0, "box")
        assert not keep and "best case" in reason

    def test_screen_keeps_a_plausible_listing(self, settings):
        from flipscan.enrich.description import analyze_description

        class Fake:
            title = "Herman Miller Aeron"
            description = "clean"
            price = 180.0
            category_hint = "furniture"

        findings = analyze_description(Fake.title, Fake.description, Fake.price)
        keep, _ = quick_screen(Fake, findings, settings, 8.0, "two_person")
        assert keep

    def test_screen_blocks_a_scam_outright(self, settings):
        from flipscan.enrich.description import analyze_description

        class Fake:
            title = "MacBook Pro sealed"
            description = "Zelle deposit to hold, cannot meet, will ship."
            price = 400.0
            category_hint = "electronics"

        findings = analyze_description(Fake.title, Fake.description, Fake.price)
        keep, reason = quick_screen(Fake, findings, settings, 5.0, "pocket")
        assert not keep and "scam" in reason


class TestDeduplication:
    def test_a_second_scan_creates_no_duplicates(self, settings):
        scan(settings)
        run = scan(settings, DemoCollector(settings, jitter=False))
        assert run.new_listings == 0
        assert run.deals_found == 0
        with session_scope() as session:
            assert len(session.exec(select(Listing)).all()) == 8

    def test_a_price_drop_triggers_a_rescore(self, settings):
        scan(settings)
        scan(settings, DemoCollector(settings, jitter=False))

        class Dropper(DemoCollector):
            async def collect(self, watchlists, limits):
                result = await super().collect(watchlists, limits)
                for listing in result.listings:
                    if "Aeron" in listing.title:
                        listing.price = 120.0
                return result

        run = scan(settings, Dropper(settings, jitter=False))
        assert run.price_changes >= 1
        assert run.deals_found >= 1

    def test_a_price_cut_increases_profit(self, settings):
        """Regression: the estimate used to be derived from the current ask, so
        cutting the price cut the estimated resale value with it."""
        scan(settings)
        with session_scope() as session:
            before = session.exec(
                select(Deal).join(Listing).where(Listing.title.like("%Aeron%"))).first()
            baseline_profit = before.net_profit
            baseline_estimate = before.resale_estimate

        class Dropper(DemoCollector):
            async def collect(self, watchlists, limits):
                result = await super().collect(watchlists, limits)
                for listing in result.listings:
                    if "Aeron" in listing.title:
                        listing.price = 120.0
                return result

        scan(settings, Dropper(settings, jitter=False))
        with session_scope() as session:
            after = session.exec(
                select(Deal).join(Listing).where(Listing.title.like("%Aeron%"))
                .order_by(Deal.created_at.desc())).first()
            assert after.resale_estimate >= baseline_estimate * 0.99
            assert after.net_profit > baseline_profit

    def test_price_history_is_recorded(self, settings):
        scan(settings)
        with session_scope() as session:
            assert len(session.exec(select(PriceObservation)).all()) == 8


class TestScanRun:
    def test_the_run_record_reflects_reality(self, settings):
        """Regression: session.refresh() used to discard the tallies, so every
        scan reported zeroes."""
        run = scan(settings)
        assert run.listings_seen > 0
        assert run.finished_at is not None
        assert run.trigger == "test"

    def test_a_broken_collector_does_not_kill_the_scan(self, settings):
        class Broken(DemoCollector):
            async def collect(self, watchlists, limits):
                raise RuntimeError("site changed")

        run = scan(settings, Broken(settings))
        assert run.listings_seen == 0
        assert not run.ok
        assert any("site changed" in error for error in run.errors)


class TestQuietHours:
    @pytest.mark.parametrize("hour_utc,expected", [
        (9, True),    # 02:00 PDT
        (13, True),   # 06:00 PDT
        (20, False),  # 13:00 PDT
        (5, True),    # 22:00 PDT
    ])
    def test_overnight_window_wraps_correctly(self, hour_utc, expected):
        from datetime import datetime

        now = datetime(2026, 8, 25, hour_utc, 0, tzinfo=UTC)
        assert in_quiet_hours(22, 7, "America/Los_Angeles", now) is expected

    def test_equal_bounds_disable_quiet_hours(self):
        assert not in_quiet_hours(0, 0, "America/Los_Angeles")


class TestAlerts:
    def test_headline_leads_with_profit(self):
        alert = DealAlert(deal_id=1, title="Aeron Chair", buy_price=180, net_profit=570,
                          roi_pct=248, resale_estimate=800, distance_miles=12,
                          deal_score=94, confidence=0.85)
        assert alert.headline().startswith("$570")

    def test_priority_scales_with_the_find(self):
        def alert(profit, score):
            return DealAlert(deal_id=1, title="x", buy_price=100, net_profit=profit,
                             roi_pct=50, resale_estimate=500, distance_miles=10,
                             deal_score=score, confidence=0.8)
        assert alert(900, 85).priority() > alert(80, 60).priority()

    def test_low_confidence_is_stated_in_the_body(self):
        alert = DealAlert(deal_id=1, title="x", buy_price=100, net_profit=200,
                          roi_pct=50, resale_estimate=400, distance_miles=10,
                          deal_score=70, confidence=0.2)
        assert "confidence" in alert.body().lower()


class TestSafetyBrief:
    def test_high_cash_at_a_home_escalates(self):
        brief = build_brief(price=1800, bulk_class="two_person")
        assert brief.level == "high"
        assert any("second person" in rule for rule in brief.rules)

    def test_a_cosmetic_flaw_does_not_trigger_fraud_warnings(self):
        """Regression: any red flag used to escalate to the scam ruleset, which
        put gift-card warnings on a bike with a paint chip."""
        brief = build_brief(price=80, bulk_class="pocket",
                            red_flags=["chipped paint / cosmetic chip"])
        assert brief.level == "routine"
        assert not any("gift card" in rule for rule in brief.rules)

    def test_real_scam_signals_do_escalate(self):
        brief = build_brief(price=400, bulk_class="pocket", scam_risk=85,
                            scam_signals=["wants a deposit to hold the item"])
        assert brief.level == "high"
        assert any("gift card" in rule for rule in brief.rules)

    def test_every_brief_has_actionable_rules(self):
        for price, bulk in [(0, "truck"), (50, "pocket"), (3000, "truck")]:
            brief = build_brief(price=price, bulk_class=bulk)
            assert brief.rules and brief.headline and brief.payment_note
