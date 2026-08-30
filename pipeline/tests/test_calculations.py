from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date

import pytest

from market_tracker.calculations import calculate_security
from market_tracker.config import SecurityDefinition
from market_tracker.demo import build_demo_documents, demo_bars
from market_tracker.models import AssetType, Direction
from market_tracker.validation import validate_report, validate_snapshot


MARKET_DATE = date(2026, 8, 28)


def test_demo_snapshot_has_rankings_deep_dives_and_chart_indicators() -> None:
    snapshot, ledger, report = build_demo_documents(MARKET_DATE)

    assert validate_snapshot(snapshot) == ()
    assert len(snapshot.gainers) == 10
    assert len(snapshot.losers) == 10
    assert all(item.direction == Direction.GAINER for item in snapshot.gainers)
    assert all(item.direction == Direction.LOSER for item in snapshot.losers)
    assert len(snapshot.deep_dive_symbols) == 6
    assert len(set(snapshot.deep_dive_symbols)) == 6
    assert validate_report(report, snapshot, ledger) == ()


def test_indicator_values_use_prior_twenty_sessions_for_volume_baseline() -> None:
    bars = demo_bars(MARKET_DATE)["AAPL"]
    security = calculate_security(SecurityDefinition("AAPL", "Apple", "Technology"), bars)
    expected_average = sum(bar.volume for bar in bars[-21:-1]) / 20

    assert security.asset_type == AssetType.STOCK
    assert security.average_volume_20 == round(expected_average, 2)
    assert security.volume_ratio_20 == round(bars[-1].volume / expected_average, 4)
    assert security.sma20 == round(sum(bar.close for bar in bars[-20:]) / 20, 4)
    assert security.sma40 == round(sum(bar.close for bar in bars[-40:]) / 40, 4)
    assert len(security.history) == 70


def test_models_are_immutable() -> None:
    snapshot, _, _ = build_demo_documents(MARKET_DATE)
    with pytest.raises(FrozenInstanceError):
        snapshot.source = "changed"  # type: ignore[misc]


def test_json_contract_uses_camel_case_and_publish_gate() -> None:
    _, _, report = build_demo_documents(MARKET_DATE)
    payload = report.to_dict()

    assert payload["metadata"]["marketDate"] == "2026-08-28"
    assert payload["qa"]["publishable"] is True
    assert payload["qa"]["reviewerStatuses"] == {
        "fact_checker": "pass",
        "blog_quality_reviewer": "pass",
        "humanify_reviewer": "pass",
    }
    assert {item["role"] for item in payload["leadStory"]["supportingPoints"]} == {
        "market",
        "sector",
        "catalyst",
    }
    assert 1 <= len(payload["nextWatch"]) <= 3
    assert "market_date" not in payload["metadata"]


def test_stale_chart_data_is_rejected() -> None:
    snapshot, _, _ = build_demo_documents(MARKET_DATE)
    stale_security = replace(snapshot.securities[0], history=snapshot.securities[0].history[:-1])
    stale_snapshot = replace(snapshot, securities=(stale_security, *snapshot.securities[1:]))

    assert "each security must end on snapshot marketDate" in validate_snapshot(stale_snapshot)
