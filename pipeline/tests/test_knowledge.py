from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from market_tracker.cli import main
from market_tracker.demo import build_demo_documents
from market_tracker.io import read_json, write_json
from market_tracker.knowledge import compile_knowledge_directory, validate_knowledge_bundle


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    _, raw, _ = text.split("---", 2)
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict)
    return parsed


def test_okf_bundle_connects_reports_symbols_themes_and_methods(tmp_path: Path) -> None:
    _, _, report = build_demo_documents(date(2026, 8, 28))
    reports_dir = tmp_path / "reports"
    write_json(reports_dir / "2026-08-28.json", report)

    catalog = compile_knowledge_directory(reports_dir, tmp_path / "knowledge")

    assert catalog["okfVersion"] == "0.2"
    assert catalog["latestMarketDate"] == "2026-08-28"
    assert not validate_knowledge_bundle(tmp_path / "knowledge")
    assert _frontmatter(tmp_path / "knowledge" / "index.md") == {"okf_version": "0.2"}

    daily = tmp_path / "knowledge" / "daily" / "2026" / "08" / "2026-08-28.md"
    daily_meta = _frontmatter(daily)
    assert daily_meta["type"] == "Daily Market Report"
    assert daily_meta["snapshot_hash"] == report.metadata.snapshot_hash
    assert daily_meta["verified"][0]["by"] == "process:daily-report-validator"

    deep_symbol = report.movers[0].symbol
    symbol_page = tmp_path / "knowledge" / "symbols" / f"{deep_symbol}.md"
    assert symbol_page.is_file()
    assert "# 타임라인" in symbol_page.read_text(encoding="utf-8")
    assert (tmp_path / "knowledge" / "themes" / "theme-01.md").is_file()
    assert (tmp_path / "knowledge" / "methodology" / "moving-averages.md").is_file()


def test_knowledge_cli_rejects_unknown_footnote_source(tmp_path: Path) -> None:
    assert main(["demo", "--market-date", "2026-08-28", "--output-dir", str(tmp_path)]) == 0
    page = tmp_path / "knowledge" / "glossary" / "volume-multiple.md"
    page.write_text(page.read_text(encoding="utf-8") + "\n잘못된 근거[^missing]\n", encoding="utf-8")

    errors = validate_knowledge_bundle(tmp_path / "knowledge")

    assert any("unknown source ids: missing" in error for error in errors)
    assert main(["validate-knowledge", "--bundle", str(tmp_path / "knowledge")]) == 2


def test_knowledge_validator_rejects_unlisted_concept_and_invalid_verifier(tmp_path: Path) -> None:
    assert main(["demo", "--market-date", "2026-08-28", "--output-dir", str(tmp_path)]) == 0
    bundle = tmp_path / "knowledge"
    page = bundle / "glossary" / "volume-multiple.md"
    page.write_text(
        page.read_text(encoding="utf-8").replace(
            "verified:\n  by: process:knowledge-validator",
            "verified:\n  by: ''",
        ),
        encoding="utf-8",
    )
    extra = bundle / "glossary" / "unlisted.md"
    extra.write_text(
        "---\n"
        "type: Financial Concept\n"
        "title: 누락 개념\n"
        "status: stable\n"
        "generated: {by: process:test, at: '2026-08-30T00:00:00+00:00'}\n"
        "verified: {by: process:test, at: '2026-08-30T00:00:00+00:00'}\n"
        "---\n\n# 누락 개념\n",
        encoding="utf-8",
    )

    errors = validate_knowledge_bundle(bundle)

    assert any("every verified entry requires a non-empty by" in error for error in errors)
    assert "catalog is missing concept file glossary/unlisted.md" in errors
