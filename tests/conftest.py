"""Shared fixtures. Every test runs against a throwaway database."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point every test at its own SQLite file.

    Autouse because a test that quietly writes into the developer's real
    database is worse than a test that fails.
    """
    from flipscan import config, db

    monkeypatch.setenv("FLIPSCAN_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("FLIPSCAN_MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("FLIPSCAN_API_TOKEN", "test-token")
    monkeypatch.setenv("FLIPSCAN_ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("FLIPSCAN_SOURCES__COLLECTORS", "demo")

    config.get_settings.cache_clear()
    db._engine = None
    db.init_db()
    yield
    db._engine = None
    config.get_settings.cache_clear()


@pytest.fixture
def settings():
    from flipscan.config import Settings

    return Settings()


@pytest.fixture
def analysis():
    """A neutral, duck-typed stand-in for an Analysis row."""

    def build(**overrides):
        base = dict(
            condition_grade="B",
            condition_score=75.0,
            condition_summary="clean, light wear",
            functional_status="working",
            resale_condition_multiplier=1.0,
            scam_risk=0.0,
            authenticity_concern=False,
            uses_stock_photos=False,
            description_red_flags=[],
            missing_parts=[],
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    return build


@pytest.fixture
def score(settings, analysis):
    """Score a listing with sensible defaults, overridable per test."""
    from flipscan.scoring import score_listing

    def run(**overrides):
        kwargs = dict(
            buy_price=180.0,
            resale_low=650.0,
            resale_mid=800.0,
            resale_high=950.0,
            comp_confidence=0.85,
            comp_sample_size=14,
            est_days_to_sell=9,
            distance_miles=12.0,
            bulk_class="two_person",
            analysis=analysis(),
            settings=settings,
        )
        kwargs.update(overrides)
        return score_listing(**kwargs)

    return run
