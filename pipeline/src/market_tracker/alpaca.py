from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from datetime import date, datetime, timezone
from typing import Any

from .models import Bar


class AlpacaError(RuntimeError):
    pass


class AlpacaClient:
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        *,
        base_url: str = "https://data.alpaca.markets",
        feed: str = "iex",
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        batch_size: int = 200,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key or not secret_key:
            raise ValueError("Alpaca credentials must not be empty")
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.feed = feed
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.batch_size = batch_size
        self._opener = opener
        self._sleeper = sleeper

    def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}{path}?{query}",
            headers={
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.secret_key,
                "Accept": "application/json",
            },
        )
        for attempt in range(self.max_retries + 1):
            try:
                with self._opener(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise AlpacaError("Alpaca returned a non-object response")
                    return payload
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt >= self.max_retries:
                    detail = _http_error_detail(exc)
                    suffix = f": {detail}" if detail else ""
                    raise AlpacaError(f"Alpaca request failed with HTTP {exc.code}{suffix}") from exc
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                delay = float(retry_after) if retry_after else 2**attempt
                self._sleeper(delay)
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt >= self.max_retries:
                    raise AlpacaError("Alpaca request failed after retries") from exc
                self._sleeper(2**attempt)
        raise AssertionError("unreachable")

    def get_daily_bars(
        self,
        symbols: Iterable[str],
        *,
        start: date,
        end: date,
    ) -> dict[str, tuple[Bar, ...]]:
        unique = tuple(dict.fromkeys(symbol.upper() for symbol in symbols))
        result: dict[str, list[Bar]] = {symbol: [] for symbol in unique}
        for offset in range(0, len(unique), self.batch_size):
            batch = unique[offset : offset + self.batch_size]
            page_token: str | None = None
            while True:
                params = {
                    "symbols": ",".join(batch),
                    "timeframe": "1Day",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "adjustment": "all",
                    "feed": self.feed,
                    "limit": "10000",
                    "sort": "asc",
                }
                if page_token:
                    params["page_token"] = page_token
                payload = self._get_json("/v2/stocks/bars", params)
                bars_by_symbol = payload.get("bars") or {}
                if not isinstance(bars_by_symbol, dict):
                    raise AlpacaError("Alpaca bars field is invalid")
                for symbol, raw_bars in bars_by_symbol.items():
                    if symbol not in result or not isinstance(raw_bars, list):
                        continue
                    for raw in raw_bars:
                        result[symbol].append(_parse_bar(symbol, raw))
                page_token = payload.get("next_page_token")
                if not page_token:
                    break
        return {
            symbol: tuple(sorted(bars, key=lambda bar: bar.timestamp))
            for symbol, bars in result.items()
        }


def _parse_bar(symbol: str, raw: dict[str, Any]) -> Bar:
    timestamp = datetime.fromisoformat(str(raw["t"]).replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return Bar(
        symbol=symbol,
        timestamp=timestamp,
        open=float(raw["o"]),
        high=float(raw["h"]),
        low=float(raw["l"]),
        close=float(raw["c"]),
        volume=int(raw["v"]),
        vwap=float(raw["vw"]) if raw.get("vw") is not None else None,
    )


def _http_error_detail(exc: urllib.error.HTTPError) -> str | None:
    """Return Alpaca's public error message without exposing request headers."""
    try:
        raw = exc.read(4096)
        payload = json.loads(raw.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    message = payload.get("message")
    return str(message)[:500] if message else None
