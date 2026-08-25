"""The money maths. These are the tests that matter most — an error here
sends someone across town to lose money."""

from __future__ import annotations

import pytest
from flipscan.config import TripSettings
from flipscan.scoring import classify_bulk, evaluate_trip, max_worth_driving_miles
from flipscan.scoring.fees import estimate_selling_costs, pick_venue, roi_pct


class TestDriveRadius:
    """The brief: a $2,000 spread earns a longer drive than a $40 flip."""

    def test_big_spread_earns_the_full_radius(self):
        trip = TripSettings()
        assert max_worth_driving_miles(2000, "truck", trip) == trip.max_radius_miles

    def test_small_flip_stays_local(self):
        trip = TripSettings()
        assert max_worth_driving_miles(40, "box", trip) < 15

    def test_radius_increases_monotonically_with_profit(self):
        trip = TripSettings()
        radii = [max_worth_driving_miles(p, "box", trip) for p in (50, 100, 200, 400, 800)]
        assert radii == sorted(radii), radii

    def test_batchable_items_justify_further_travel(self):
        """Small items get collected several per trip, so the trip cost divides."""
        trip = TripSettings()
        pocket = max_worth_driving_miles(80, "pocket", trip)
        two_person = max_worth_driving_miles(80, "two_person", trip)
        assert pocket > two_person

    def test_bulky_low_margin_item_is_worth_no_drive_at_all(self):
        """A couch whose fixed truck cost exceeds the travel budget."""
        trip = TripSettings()
        assert max_worth_driving_miles(60, "truck", trip) == 0.0

    def test_radius_never_exceeds_the_hard_ceiling(self):
        trip = TripSettings()
        assert max_worth_driving_miles(1_000_000, "pocket", trip) == trip.max_radius_miles

    def test_trip_cost_rises_with_distance(self):
        trip = TripSettings()
        near = evaluate_trip(5, 500, "box", trip)
        far = evaluate_trip(45, 500, "box", trip)
        assert far.trip_cost > near.trip_cost

    def test_explanation_is_written_for_a_human(self):
        trip = TripSettings()
        text = evaluate_trip(12, 600, "box", trip).explain()
        assert "mi" in text and "$" in text


class TestBulkClassification:
    @pytest.mark.parametrize("title,expected", [
        ("Sectional couch - must go", "truck"),
        ("Kenmore washer and dryer set", "truck"),
        ("Herman Miller Aeron chair", "two_person"),
        ("Trek road bike 56cm", "two_person"),
        ("iPhone 14 Pro 256gb", "pocket"),
        ("Canon 5D Mark IV body", "box"),
        ("DeWalt drill set 20v", "box"),
    ])
    def test_classifies_by_title(self, title, expected):
        assert classify_bulk(title) == expected

    def test_unknown_falls_back_to_box(self):
        assert classify_bulk("mystery item") == "box"


class TestFees:
    def test_local_cash_sale_has_no_platform_fee(self, settings):
        costs = estimate_selling_costs(800, "facebook_local", "two_person", "B", settings.fees)
        assert costs.platform_fee == 0

    def test_ebay_takes_its_cut(self, settings):
        costs = estimate_selling_costs(800, "ebay", "pocket", "B", settings.fees)
        assert costs.platform_fee == pytest.approx(800 * 0.1325 + 0.40)

    def test_worse_condition_costs_more_to_prepare(self, settings):
        clean = estimate_selling_costs(500, "facebook_local", "box", "A", settings.fees)
        rough = estimate_selling_costs(500, "facebook_local", "box", "D", settings.fees)
        assert rough.refurb > clean.refurb

    def test_bulky_items_are_never_routed_to_a_shipping_venue(self, settings):
        assert pick_venue("truck", 900, settings.fees, preferred="ebay") == "facebook_local"

    def test_small_valuable_items_prefer_the_national_market(self, settings):
        assert pick_venue("pocket", 900, settings.fees) == "ebay"

    def test_roi_is_denominated_on_cash_at_risk(self, settings):
        costs = estimate_selling_costs(300, "facebook_local", "box", "B", settings.fees)
        # $100 profit on $100 spent is 100%, not some other denominator.
        assert roi_pct(100, 100 - costs.refurb, costs, 0) == pytest.approx(100.0)

    def test_free_item_does_not_divide_by_zero(self, settings):
        costs = estimate_selling_costs(100, "facebook_local", "box", "A", settings.fees)
        assert roi_pct(100, 0.0, costs, 0.0) > 0


class TestDealScore:
    def test_a_good_deal_passes(self, score):
        deal = score()
        assert deal.passes_filters
        assert deal.deal_score > 70
        assert deal.net_profit > 400

    def test_thin_margin_is_rejected(self, score):
        deal = score(buy_price=60, resale_low=95, resale_mid=110, resale_high=125,
                     bulk_class="box")
        assert not deal.passes_filters
        assert "bar" in (deal.reject_reason or "")

    def test_high_scam_risk_is_blocked_regardless_of_profit(self, score, analysis):
        deal = score(buy_price=400, resale_low=850, resale_mid=950, resale_high=1050,
                     bulk_class="pocket", analysis=analysis(scam_risk=85))
        assert not deal.passes_filters
        assert "scam" in (deal.reject_reason or "").lower()

    def test_scam_block_beats_an_enormous_margin(self, score, analysis):
        """No profit figure should be able to buy its way past the scam gate."""
        deal = score(buy_price=100, resale_low=4000, resale_mid=5000, resale_high=6000,
                     bulk_class="pocket", analysis=analysis(scam_risk=95))
        assert not deal.passes_filters

    def test_too_far_is_rejected(self, score):
        deal = score(distance_miles=59, buy_price=100, resale_low=180,
                     resale_mid=200, resale_high=220, bulk_class="truck")
        assert not deal.passes_filters

    def test_over_the_spending_cap_is_rejected(self, score, settings):
        deal = score(buy_price=settings.profit.max_buy_price + 1,
                     resale_low=9000, resale_mid=10000, resale_high=11000)
        assert not deal.passes_filters
        assert "cap" in (deal.reject_reason or "")

    def test_condition_multiplier_reduces_the_estimate(self, score, analysis):
        clean = score()
        rough = score(analysis=analysis(condition_grade="D", condition_score=30,
                                        functional_status="for_parts",
                                        resale_condition_multiplier=0.4))
        assert rough.resale_estimate < clean.resale_estimate
        assert rough.net_profit < clean.net_profit

    def test_low_comp_confidence_lowers_the_score(self, score):
        confident = score(comp_confidence=0.9, comp_sample_size=20)
        unsure = score(comp_confidence=0.15, comp_sample_size=1)
        assert unsure.deal_score < confident.deal_score

    def test_thin_evidence_produces_an_explicit_warning(self, score):
        deal = score(comp_confidence=0.2, comp_sample_size=1)
        assert any("comparable" in w for w in deal.warnings)

    def test_a_price_cut_is_surfaced_as_motivation(self, score):
        deal = score(first_seen_price=300)
        assert any("cut" in r.lower() for r in deal.reasons)

    def test_reasons_always_explain_the_money(self, score):
        deal = score()
        assert any("$" in r for r in deal.reasons)
        assert len(deal.reasons) >= 3

    def test_faster_selling_items_score_higher(self, score):
        quick = score(est_days_to_sell=5)
        slow = score(est_days_to_sell=120)
        assert quick.deal_score > slow.deal_score

    def test_score_is_bounded(self, score, analysis):
        awful = score(buy_price=500, resale_low=10, resale_mid=20, resale_high=30,
                      analysis=analysis(condition_grade="F", condition_score=0,
                                        functional_status="for_parts",
                                        resale_condition_multiplier=0.2))
        assert 0.0 <= awful.deal_score <= 100.0

    def test_high_value_deals_get_a_relaxed_roi_bar(self, settings, score):
        """$900 profit at 30% ROI is a good day even though it fails the
        default percentage test."""
        # Chosen so the profit clears the high-value threshold while the
        # percentage return genuinely falls below the normal bar — otherwise
        # the test passes without ever exercising the override.
        deal = score(buy_price=2000, resale_low=2450, resale_mid=2600,
                     resale_high=2750, bulk_class="two_person", distance_miles=10)
        assert deal.net_profit >= settings.profit.high_value_profit_override
        assert deal.roi_pct < settings.profit.min_roi_pct
        assert deal.passes_filters

    def test_costs_are_fully_itemised(self, score):
        deal = score(bulk_class="pocket", buy_price=400, resale_low=850,
                     resale_mid=950, resale_high=1050)
        recomputed = (deal.resale_estimate - deal.buy_price - deal.platform_fees
                      - deal.shipping_cost - deal.refurb_cost - deal.trip_cost)
        assert deal.net_profit == pytest.approx(recomputed, abs=0.02)
