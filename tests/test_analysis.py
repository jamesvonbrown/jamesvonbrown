"""Description mining and comp statistics."""

from __future__ import annotations

import pytest
from flipscan.comps.base import CompResult, CompSample, reject_outliers, relevance_score, summarize
from flipscan.comps.engine import _blend
from flipscan.comps.priors import get_prior, prior_estimate
from flipscan.enrich.description import (
    analyze_description,
    condition_grade_from_penalty,
    condition_multiplier,
)


class TestScamDetection:
    def test_catches_the_deposit_scam(self):
        findings = analyze_description(
            "MacBook Pro sealed",
            "Cannot meet, I'm out of town. Need a $100 Zelle deposit to hold it.",
            400)
        assert findings.scam_risk >= 70

    def test_moving_out_of_state_is_not_a_scam(self):
        """The single most common honest reason a good deal exists."""
        findings = analyze_description(
            "Herman Miller Aeron",
            "Moving out of state next week so it needs to go. Cash, pickup in Beaverton.",
            180)
        assert findings.scam_risk == 0

    def test_gift_cards_are_always_a_scam(self):
        findings = analyze_description("iPhone", "Payment by gift card only.", 300)
        assert findings.scam_risk >= 40

    def test_verification_code_request_scores_highest(self):
        findings = analyze_description(
            "Couch", "Send me the six digit code to verify you're real.", 100)
        assert findings.scam_risk >= 55

    def test_too_good_to_be_true_needs_both_halves(self):
        cheap_generic = analyze_description("Desk", "Brand new sealed in box.", 60)
        cheap_premium = analyze_description("MacBook Pro M3", "Brand new sealed in box.", 300)
        assert cheap_premium.scam_risk > cheap_generic.scam_risk


class TestConditionFromText:
    def test_worked_when_removed_means_untested(self):
        findings = analyze_description("Washer", "Worked when removed. Sold as is.", 150)
        assert findings.functional_status == "untested"

    def test_for_parts_is_recognised(self):
        findings = analyze_description("Mower", "For parts only, does not run.", 40)
        assert findings.functional_status == "for_parts"

    def test_pessimistic_when_the_listing_contradicts_itself(self):
        """'Works great, selling for parts' resolves to the worse reading."""
        findings = analyze_description("Console", "Works great! Selling for parts.", 50)
        assert findings.functional_status == "for_parts"

    def test_a_paint_chip_is_not_a_crack(self):
        chip = analyze_description("Bike", "Small chip in the paint on the chainstay.", 650)
        crack = analyze_description("Phone", "Screen is cracked but works.", 200)
        assert chip.condition_penalty < crack.condition_penalty

    def test_staining_is_detected(self):
        findings = analyze_description("Couch", "Some staining on one cushion.", 0)
        assert any("stain" in flag.lower() for flag in findings.red_flags)

    def test_a_hair_dryer_is_not_a_pet(self):
        findings = analyze_description("Dyson hair dryer", "Works great, original box.", 150)
        assert not any("pet" in flag.lower() for flag in findings.red_flags)

    def test_green_flags_are_picked_up(self):
        findings = analyze_description(
            "Aeron", "Smoke free home, original box, still under warranty.", 400)
        assert len(findings.green_flags) >= 3

    def test_motivation_is_scored(self):
        urgent = analyze_description("Couch", "Moving Sunday, must go today!", 0)
        calm = analyze_description("Couch", "Nice couch.", 200)
        assert urgent.motivation_score > calm.motivation_score

    def test_grade_tracks_penalty(self):
        clean, _ = condition_grade_from_penalty(0)
        rough, _ = condition_grade_from_penalty(60)
        assert clean == "B" and rough in ("D", "F")

    def test_for_parts_crushes_the_multiplier(self):
        assert condition_multiplier("B", "for_parts") <= 0.3

    def test_grade_a_beats_grade_d(self):
        assert condition_multiplier("A", "working") > condition_multiplier("D", "working")


class TestCompStatistics:
    def test_accessories_are_excluded(self):
        query = "Herman Miller Aeron Size B"
        assert relevance_score(query, "Herman Miller Aeron armrest pads") < 0.62
        assert relevance_score(query, "Aeron Chair Replacement Casters") < 0.62
        assert relevance_score(query, "Herman Miller Aeron Size B Graphite") >= 0.9

    def test_unrelated_products_are_excluded(self):
        assert relevance_score("Herman Miller Aeron", "Steelcase Leap V2") < 0.5

    def test_outliers_are_trimmed(self):
        prices = [12.0, 280, 295, 310, 300, 320, 288, 305, 2400.0]
        trimmed = reject_outliers(prices)
        assert 12.0 not in trimmed and 2400.0 not in trimmed

    def test_accessory_prices_do_not_drag_the_estimate_down(self):
        query = "Herman Miller Aeron Size B"
        samples = [
            CompSample("Herman Miller Aeron Chair Size B Fully Loaded", 780),
            CompSample("Herman Miller Aeron Size B Graphite", 720),
            CompSample("Herman Miller Aeron Chair Size B", 850),
            CompSample("Herman Miller Aeron armrest pads replacement", 34),
            CompSample("Aeron chair cylinder only", 45),
            CompSample("Herman Miller Aeron Size B 2023", 920),
        ]
        result = summarize("ebay_sold", query, samples)
        assert result.sample_size == 4
        assert result.median > 700

    def test_thin_evidence_yields_low_confidence(self):
        samples = [CompSample("Aeron Size B", 120), CompSample("Aeron Size B chair", 700)]
        assert summarize("x", "Aeron Size B", samples).confidence < 0.5

    def test_plentiful_agreeing_evidence_yields_high_confidence(self):
        samples = [CompSample(f"Aeron Size B unit {i}", 780 + i * 5) for i in range(12)]
        assert summarize("x", "Aeron Size B", samples).confidence > 0.75

    def test_asking_prices_get_a_haircut(self):
        samples = [CompSample(f"Aeron Size B {i}", 800) for i in range(6)]
        sold = summarize("ebay_sold", "Aeron Size B", samples)
        active = summarize("ebay_active", "Aeron Size B", samples, asking_to_sold=0.78)
        assert active.median < sold.median

    def test_no_relevant_comps_reports_an_error(self):
        result = summarize("x", "Aeron Size B", [CompSample("Toyota Camry", 5000)])
        assert not result.ok and result.error


class TestBlending:
    def test_agreement_boosts_confidence(self):
        results = [
            CompResult("ebay_sold", low=700, median=780, high=860, confidence=0.8, sample_size=12),
            CompResult("internal", low=720, median=800, high=880, confidence=0.6, sample_size=4),
        ]
        _, mid, _, confidence, _ = _blend(results)
        assert 770 < mid < 810
        assert confidence > 0.8

    def test_disagreement_cuts_confidence_and_widens_the_band(self):
        results = [
            CompResult("ebay_sold", low=700, median=780, high=860, confidence=0.8, sample_size=12),
            CompResult("web_research", low=300, median=380, high=450, confidence=0.6, sample_size=3),
        ]
        low, _, high, confidence, _ = _blend(results)
        assert confidence < 0.7
        assert low < 380 and high > 780

    def test_no_usable_results_returns_zeroes(self):
        assert _blend([CompResult("x", error="nope")]) == (0.0, 0.0, 0.0, 0.0, 0)


class TestPriors:
    def test_tools_hold_value_better_than_clothing(self):
        assert get_prior("tools").retention > get_prior("clothing").retention

    def test_retail_anchor_beats_the_asking_price(self):
        _, from_retail, _, method = prior_estimate(200, "tools", retail_new=500)
        assert "retail" in method
        assert from_retail == pytest.approx(500 * get_prior("tools").retention)

    def test_a_price_cut_does_not_reduce_the_estimate(self):
        """A seller conceding is not the item depreciating."""
        _, before, _, _ = prior_estimate(180, "furniture")
        _, after, _, _ = prior_estimate(120, "furniture", anchor_price=180)
        assert after == pytest.approx(before)

    def test_unknown_category_still_produces_an_estimate(self):
        _, mid, _, _ = prior_estimate(100, "not-a-real-category")
        assert mid > 0
