"""HTTP surface, including the auth boundary."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from flipscan.collectors import DemoCollector
from flipscan.pipeline import run_scan

AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture
def client(settings):
    from flipscan.main import app

    asyncio.run(run_scan(settings, trigger="test",
                         collectors=[DemoCollector(settings)], notify=False))
    with TestClient(app) as test_client:
        yield test_client


class TestAuth:
    def test_no_token_is_rejected(self, client):
        assert client.get("/api/deals").status_code == 401

    def test_wrong_token_is_rejected(self, client):
        assert client.get("/api/deals",
                          headers={"Authorization": "Bearer nope"}).status_code == 401

    def test_valid_token_is_accepted(self, client):
        assert client.get("/api/deals", headers=AUTH).status_code == 200

    def test_health_needs_no_auth(self, client):
        assert client.get("/health").status_code == 200

    def test_a_token_prefix_is_not_enough(self, client):
        """Guards against a non-constant-time compare leaking the secret."""
        assert client.get("/api/deals",
                          headers={"Authorization": "Bearer test-toke"}).status_code == 401


class TestDeals:
    def test_feed_returns_scored_deals(self, client):
        deals = client.get("/api/deals", headers=AUTH).json()
        assert deals
        assert all(d["net_profit"] > 0 for d in deals)

    def test_sorted_by_profit(self, client):
        deals = client.get("/api/deals?sort=profit", headers=AUTH).json()
        profits = [d["net_profit"] for d in deals]
        assert profits == sorted(profits, reverse=True)

    def test_min_profit_filter(self, client):
        deals = client.get("/api/deals?min_profit=200", headers=AUTH).json()
        assert all(d["net_profit"] >= 200 for d in deals)

    def test_timestamps_carry_a_utc_offset(self, client):
        """Regression: SQLite drops tzinfo, so these used to serialise naive
        and every client read them as local time."""
        deals = client.get("/api/deals", headers=AUTH).json()
        assert all(d["created_at"].endswith("+00:00") for d in deals)

    def test_detail_itemises_every_cost(self, client):
        deal_id = client.get("/api/deals", headers=AUTH).json()[0]["id"]
        detail = client.get(f"/api/deals/{deal_id}", headers=AUTH).json()
        money = detail["money"]
        recomputed = (money["resale_estimate"] - money["buy_price"]
                      - money["platform_fees"] - money["shipping_cost"]
                      - money["refurb_cost"] - money["trip_cost"])
        assert money["net_profit"] == pytest.approx(recomputed, abs=0.02)

    def test_detail_includes_a_safety_brief(self, client):
        deal_id = client.get("/api/deals", headers=AUTH).json()[0]["id"]
        safety = client.get(f"/api/deals/{deal_id}", headers=AUTH).json()["safety"]
        assert safety["level"] in ("routine", "elevated", "high")
        assert safety["rules"]

    def test_missing_deal_is_404(self, client):
        assert client.get("/api/deals/999999", headers=AUTH).status_code == 404


class TestFeedback:
    def test_recording_a_sale_reports_the_estimate_error(self, client):
        deal_id = client.get("/api/deals", headers=AUTH).json()[0]["id"]
        response = client.post(f"/api/deals/{deal_id}/feedback", headers=AUTH,
                               json={"action": "sold", "actual_sale_price": 640}).json()
        assert response["ok"]
        assert "estimate_error_pct" in response

    def test_passing_removes_it_from_the_feed(self, client):
        deals = client.get("/api/deals", headers=AUTH).json()
        deal_id = deals[0]["id"]
        client.post(f"/api/deals/{deal_id}/feedback", headers=AUTH,
                    json={"action": "passed"})
        remaining = [d["id"] for d in client.get("/api/deals", headers=AUTH).json()]
        assert deal_id not in remaining

    def test_invalid_action_is_rejected(self, client):
        deal_id = client.get("/api/deals", headers=AUTH).json()[0]["id"]
        assert client.post(f"/api/deals/{deal_id}/feedback", headers=AUTH,
                           json={"action": "nonsense"}).status_code == 400


class TestSettings:
    def test_overrides_round_trip(self, client):
        client.patch("/api/settings", headers=AUTH,
                     json={"updates": {"profit.min_net_profit": 150}})
        settings = client.get("/api/settings", headers=AUTH).json()
        assert settings["overrides"]["profit.min_net_profit"] == 150

    def test_unknown_key_is_rejected(self, client):
        assert client.patch("/api/settings", headers=AUTH,
                            json={"updates": {"nope.x": 1}}).status_code == 400

    def test_watchlists_are_seeded(self, client):
        assert len(client.get("/api/watchlists", headers=AUTH).json()) >= 15

    def test_watchlist_crud(self, client):
        created = client.post("/api/watchlists", headers=AUTH, json={
            "name": "Test", "query": "test query", "category": "tools",
            "bulk_class": "box", "priority": 3}).json()
        assert client.patch(f"/api/watchlists/{created['id']}", headers=AUTH,
                            json={"enabled": False}).json()["enabled"] is False
        assert client.delete(f"/api/watchlists/{created['id']}",
                             headers=AUTH).json()["ok"]


class TestStatus:
    def test_reports_missing_configuration(self, client):
        status = client.get("/api/status", headers=AUTH).json()
        assert any("eBay" in warning for warning in status["warnings"])
        assert any("Anthropic" in warning for warning in status["warnings"])

    def test_manual_submission_is_queued(self, client):
        response = client.post("/api/deals/manual", headers=AUTH, json={
            "url": "https://www.facebook.com/marketplace/item/555000111/",
            "text": "Vintage Teak Credenza\nAsking 275 obo\nLocation: Sellwood"}).json()
        assert response["ok"]
        assert response["queued"]["price"] == 275.0

    def test_empty_manual_submission_is_rejected(self, client):
        assert client.post("/api/deals/manual", headers=AUTH, json={}).status_code == 400


class TestDevices:
    def test_webpush_requires_a_subscription_object(self, client):
        assert client.post("/api/devices", headers=AUTH, json={
            "platform": "webpush", "token": "not json"}).status_code == 400

    def test_registration_round_trips(self, client):
        subscription = '{"endpoint":"https://web.push.apple.com/x","keys":{"p256dh":"a","auth":"b"}}'
        assert client.post("/api/devices", headers=AUTH, json={
            "platform": "webpush", "token": subscription, "label": "iPhone"}).json()["ok"]
        devices = client.get("/api/devices", headers=AUTH).json()
        assert len(devices) == 1
        # The full push token must never come back out of the API.
        assert devices[0]["token_preview"] != subscription

    def test_unknown_platform_is_rejected(self, client):
        assert client.post("/api/devices", headers=AUTH, json={
            "platform": "carrier-pigeon", "token": "x"}).status_code == 400
