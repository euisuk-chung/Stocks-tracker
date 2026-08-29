from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


DEFAULT_MARKET_ETFS = ("SPY", "QQQ", "DIA", "IWM")
DEFAULT_ETP_BASKET = ("SPY", "QQQ", "SCHD", "VYM", "DGRO", "JEPI")
DEFAULT_DIVIDEND_STOCKS = ("MSFT", "JPM", "JNJ", "PG", "KO", "MCD", "XOM", "NEE", "O", "UPS")


@dataclass(frozen=True, slots=True)
class SecurityDefinition:
    symbol: str
    name: str
    sector: str | None
    asset_type: str = "stock"


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    alpaca_api_key: str | None
    alpaca_secret_key: str | None
    alpaca_data_url: str = "https://data.alpaca.markets"
    feed: str = "iex"
    lookback_sessions: int = 70
    top_count: int = 10
    deep_dive_per_direction: int = 3
    max_retries: int = 3
    request_batch_size: int = 200
    request_timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls, *, require_credentials: bool = True) -> "PipelineConfig":
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=False)
        key = os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID")
        secret = os.getenv("ALPACA_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY")
        if require_credentials and (not key or not secret):
            raise ValueError(
                "Alpaca credentials are required. Set ALPACA_API_KEY and ALPACA_SECRET_KEY "
                "(or APCA_API_KEY_ID/APCA_API_SECRET_KEY)."
            )
        return cls(
            alpaca_api_key=key,
            alpaca_secret_key=secret,
            alpaca_data_url=os.getenv("ALPACA_DATA_URL", "https://data.alpaca.markets"),
            feed=os.getenv("ALPACA_FEED", "iex"),
        )


def load_universe(path: Path) -> tuple[SecurityDefinition, ...]:
    if not path.is_file():
        raise FileNotFoundError(f"Universe CSV not found: {path}")
    definitions: list[SecurityDefinition] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"symbol", "name", "sector"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("Universe CSV must contain symbol,name,sector columns")
        seen: set[str] = set()
        for row in reader:
            symbol = row["symbol"].strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            definitions.append(
                SecurityDefinition(
                    symbol=symbol,
                    name=row["name"].strip() or symbol,
                    sector=row["sector"].strip() or None,
                    asset_type=(row.get("asset_type") or "stock").strip().lower(),
                )
            )
    if not definitions:
        raise ValueError("Universe CSV contains no securities")
    return tuple(definitions)
