from __future__ import annotations

from pathlib import Path

import pytest

from market_tracker.config import SecurityDefinition
from market_tracker.universe import load_or_refresh_universe, parse_sp500_html


def constituent_html(count: int = 500) -> str:
    rows = "".join(
        f"<tr><td>ABC.{index}</td><td>Company {index}</td><td>Technology</td></tr>"
        for index in range(count)
    )
    return (
        '<table id="constituents"><tr><th>Symbol</th><th>Security</th>'
        f"<th>GICS Sector</th></tr>{rows}</table>"
    )


def test_parse_sp500_constituent_table() -> None:
    definitions = parse_sp500_html(constituent_html())

    assert len(definitions) == 500
    assert definitions[0] == SecurityDefinition("ABC-0", "Company 0", "Technology")


def test_parser_rejects_incomplete_table() -> None:
    with pytest.raises(ValueError, match="at least 490"):
        parse_sp500_html(constituent_html(10))


def test_cached_universe_is_used_without_refresh(tmp_path: Path) -> None:
    csv_path = tmp_path / "sp500.csv"
    csv_path.write_text("symbol,name,sector\nAAPL,Apple,Technology\n", encoding="utf-8")

    assert load_or_refresh_universe(csv_path)[0].symbol == "AAPL"
