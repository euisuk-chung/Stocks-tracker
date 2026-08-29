from __future__ import annotations

import io
import json
import urllib.error
from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest

from market_tracker.alpaca import AlpacaClient, AlpacaError


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def raw_bar(day: str, close: int) -> dict:
    return {"t": f"{day}T21:00:00Z", "o": close - 1, "h": close + 1, "l": close - 2, "c": close, "v": 1000}


def test_pagination_and_batching() -> None:
    requests: list[str] = []

    def opener(request: object, timeout: float) -> FakeResponse:
        url = request.full_url  # type: ignore[attr-defined]
        requests.append(url)
        params = parse_qs(urlsplit(url).query)
        symbols = params["symbols"][0].split(",")
        if "page_token" not in params:
            return FakeResponse(
                {"bars": {symbol: [raw_bar("2026-08-27", 100)] for symbol in symbols}, "next_page_token": "next"}
            )
        return FakeResponse({"bars": {symbol: [raw_bar("2026-08-28", 101)] for symbol in symbols}})

    client = AlpacaClient("key", "secret", batch_size=2, opener=opener)
    result = client.get_daily_bars(("AAA", "BBB", "CCC"), start=date(2026, 8, 1), end=date(2026, 8, 29))

    assert len(requests) == 4
    assert all(len(result[symbol]) == 2 for symbol in ("AAA", "BBB", "CCC"))
    assert result["AAA"][0].close == 100


def test_retries_http_429_with_backoff() -> None:
    attempts = 0
    sleeps: list[float] = []

    def opener(request: object, timeout: float) -> FakeResponse:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise urllib.error.HTTPError("url", 429, "rate limited", {}, io.BytesIO())
        return FakeResponse({"bars": {"AAA": [raw_bar("2026-08-28", 101)]}})

    client = AlpacaClient("key", "secret", max_retries=2, opener=opener, sleeper=sleeps.append)
    result = client.get_daily_bars(("AAA",), start=date(2026, 8, 1), end=date(2026, 8, 29))

    assert attempts == 3
    assert sleeps == [1, 2]
    assert result["AAA"][0].volume == 1000


def test_non_retryable_http_error_fails_immediately() -> None:
    def opener(request: object, timeout: float) -> FakeResponse:
        raise urllib.error.HTTPError("url", 401, "unauthorized", {}, io.BytesIO())

    client = AlpacaClient("key", "secret", opener=opener)
    with pytest.raises(AlpacaError, match="401"):
        client.get_daily_bars(("AAA",), start=date(2026, 8, 1), end=date(2026, 8, 29))
