from __future__ import annotations

from pathlib import Path
from datetime import date

from market_tracker.cli import main
from market_tracker.demo import build_demo_documents
from market_tracker.io import read_json


def test_demo_and_validation_cli(tmp_path: Path) -> None:
    assert main(["demo", "--market-date", "2026-08-28", "--output-dir", str(tmp_path)]) == 0
    snapshot = tmp_path / "artifacts" / "2026-08-28" / "market-snapshot.json"
    ledger = tmp_path / "artifacts" / "2026-08-28" / "evidence-ledger.json"
    report = tmp_path / "reports" / "2026-08-28.json"

    assert report.is_file()
    assert read_json(report)["qa"]["publishable"] is True
    assert main(["validate", "--snapshot", str(snapshot), "--ledger", str(ledger), "--report", str(report)]) == 0


def test_schema_cli_writes_all_contracts(tmp_path: Path) -> None:
    assert main(["schemas", "--output-dir", str(tmp_path)]) == 0
    assert {path.name for path in tmp_path.glob("*.json")} == {
        "market-snapshot.schema.json",
        "evidence-ledger.schema.json",
        "review-result.schema.json",
        "daily-report.schema.json",
    }


def test_checked_in_report_fixture_matches_generator() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "reports" / "2026-08-28.json"
    _, _, expected_report = build_demo_documents(date(2026, 8, 28))

    assert read_json(fixture) == expected_report.to_dict()
