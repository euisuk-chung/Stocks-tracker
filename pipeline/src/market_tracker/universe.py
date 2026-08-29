from __future__ import annotations

import csv
import io
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .config import SecurityDefinition, load_universe


SP500_SOURCE_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


class _ConstituentsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_target_table = False
        self.table_depth = 0
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_by_name = dict(attrs)
        if tag == "table" and attrs_by_name.get("id") == "constituents":
            self.in_target_table = True
            self.table_depth = 1
        elif self.in_target_table and tag == "table":
            self.table_depth += 1
        elif self.in_target_table and tag == "tr":
            self.current_row = []
        elif self.in_target_table and tag in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.in_target_table:
            return
        if tag in {"td", "th"} and self.in_cell:
            self.current_row.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell = False
        elif tag == "tr" and self.current_row:
            self.rows.append(self.current_row)
            self.current_row = []
        elif tag == "table":
            self.table_depth -= 1
            if self.table_depth == 0:
                self.in_target_table = False


def parse_sp500_html(html: str) -> tuple[SecurityDefinition, ...]:
    parser = _ConstituentsParser()
    parser.feed(html)
    if not parser.rows:
        raise ValueError("S&P 500 constituents table was not found")
    headers = parser.rows[0]
    try:
        symbol_index = headers.index("Symbol")
        name_index = headers.index("Security")
        sector_index = headers.index("GICS Sector")
    except ValueError as exc:
        raise ValueError("S&P 500 table headers have changed") from exc
    definitions: list[SecurityDefinition] = []
    for row in parser.rows[1:]:
        if len(row) <= max(symbol_index, name_index, sector_index):
            continue
        symbol = row[symbol_index].strip().upper().replace(".", "-")
        if symbol:
            definitions.append(
                SecurityDefinition(
                    symbol=symbol,
                    name=row[name_index].strip() or symbol,
                    sector=row[sector_index].strip() or None,
                )
            )
    if len(definitions) < 490:
        raise ValueError(f"Expected at least 490 S&P 500 rows, found {len(definitions)}")
    return tuple(definitions)


def fetch_sp500_universe(
    *,
    url: str = SP500_SOURCE_URL,
    timeout_seconds: float = 30.0,
    opener: Any = urllib.request.urlopen,
) -> tuple[SecurityDefinition, ...]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "StocksTracker/0.1 (+educational market report)"},
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            html = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Failed to refresh S&P 500 universe from {url}") from exc
    return parse_sp500_html(html)


def write_universe_csv(path: Path, definitions: tuple[SecurityDefinition, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=("symbol", "name", "sector", "asset_type"), lineterminator="\n")
    writer.writeheader()
    for item in definitions:
        writer.writerow(
            {"symbol": item.symbol, "name": item.name, "sector": item.sector or "", "asset_type": item.asset_type}
        )
    # This cache is generated runtime data, not a hand-edited project source.
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")


def load_or_refresh_universe(
    path: Path,
    *,
    max_age_days: int = 7,
    force_refresh: bool = False,
) -> tuple[SecurityDefinition, ...]:
    fresh = False
    if path.is_file() and not force_refresh:
        age_seconds = time.time() - path.stat().st_mtime
        fresh = age_seconds <= max_age_days * 86400
    if fresh:
        return load_universe(path)
    try:
        definitions = fetch_sp500_universe()
        write_universe_csv(path, definitions)
        return definitions
    except (RuntimeError, ValueError):
        if path.is_file():
            return load_universe(path)
        raise
