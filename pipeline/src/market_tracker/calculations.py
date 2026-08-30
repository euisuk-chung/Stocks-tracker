from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from statistics import fmean

from .config import DEFAULT_DIVIDEND_STOCKS, DEFAULT_ETP_BASKET, DEFAULT_MARKET_ETFS, SecurityDefinition
from .models import (
    AssetType,
    Bar,
    ChartPoint,
    Direction,
    HeatmapEntry,
    MarketSnapshot,
    MovingAverageCross,
    NasdaqRegime,
    RankedMover,
    Regime,
    SCHEMA_VERSION,
    SecuritySnapshot,
)


MINIMUM_BARS = 45


def _round(value: float, digits: int = 4) -> float:
    return round(value, digits)


def _rolling_average(values: list[float], window: int) -> list[float | None]:
    output: list[float | None] = []
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= window:
            running -= values[index - window]
        output.append(running / window if index >= window - 1 else None)
    return output


def calculate_security(
    definition: SecurityDefinition,
    bars: tuple[Bar, ...],
) -> SecuritySnapshot:
    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    if len(ordered) < MINIMUM_BARS:
        raise ValueError(f"{definition.symbol} has {len(ordered)} bars; at least {MINIMUM_BARS} are required")
    if any(bar.symbol != definition.symbol for bar in ordered):
        raise ValueError(f"Bar symbol mismatch for {definition.symbol}")

    closes = [bar.close for bar in ordered]
    volumes = [float(bar.volume) for bar in ordered]
    if any(value <= 0 for value in closes) or any(value < 0 for value in volumes):
        raise ValueError(f"{definition.symbol} contains invalid price or volume")

    sma20_values = _rolling_average(closes, 20)
    sma40_values = _rolling_average(closes, 40)
    latest, previous = ordered[-1], ordered[-2]
    sma20 = float(sma20_values[-1])
    sma40 = float(sma40_values[-1])
    sma20_prior = float(sma20_values[-6])
    sma40_prior = float(sma40_values[-6])
    prior_sma20 = float(sma20_values[-2])
    prior_sma40 = float(sma40_values[-2])
    average_volume_20 = fmean(volumes[-21:-1])
    volume_ratio = latest.volume / average_volume_20 if average_volume_20 else 0.0
    change_pct = (latest.close / previous.close - 1) * 100

    cross = MovingAverageCross.NONE
    if prior_sma20 <= prior_sma40 and sma20 > sma40:
        cross = MovingAverageCross.GOLDEN
    elif prior_sma20 >= prior_sma40 and sma20 < sma40:
        cross = MovingAverageCross.DEATH

    history = tuple(
        ChartPoint(
            date=bar.timestamp.date(),
            close=_round(bar.close),
            volume=bar.volume,
            sma20=_round(sma20_values[index]) if sma20_values[index] is not None else None,
            sma40=_round(sma40_values[index]) if sma40_values[index] is not None else None,
        )
        for index, bar in enumerate(ordered[-70:], start=max(0, len(ordered) - 70))
    )
    return SecuritySnapshot(
        symbol=definition.symbol,
        name=definition.name,
        asset_type=AssetType(definition.asset_type),
        sector=definition.sector,
        close=_round(latest.close),
        previous_close=_round(previous.close),
        change_pct=_round(change_pct),
        dollar_volume=_round(latest.close * latest.volume, 2),
        average_volume_20=_round(average_volume_20, 2),
        volume_ratio_20=_round(volume_ratio),
        sma20=_round(sma20),
        sma40=_round(sma40),
        sma20_slope_5_pct=_round((sma20 / sma20_prior - 1) * 100),
        sma40_slope_5_pct=_round((sma40 / sma40_prior - 1) * 100),
        distance_sma20_pct=_round((latest.close / sma20 - 1) * 100),
        distance_sma40_pct=_round((latest.close / sma40 - 1) * 100),
        moving_average_cross=cross,
        anomaly_score=_round(abs(change_pct) * max(volume_ratio, 1.0)),
        history=history,
    )


def classify_regime(security: SecuritySnapshot) -> tuple[Regime, tuple[str, ...]]:
    if (
        security.close > security.sma20 > security.sma40
        and security.sma20_slope_5_pct > 0
        and security.sma40_slope_5_pct > 0
    ):
        return Regime.BULLISH, (
            "QQQ 종가가 1개월선(20거래일)과 2개월선(40거래일) 위에 있습니다.",
            "1개월선과 2개월선의 5거래일 기울기가 모두 상승 방향입니다.",
        )
    if (
        security.close < security.sma20 < security.sma40
        and security.sma20_slope_5_pct < 0
        and security.sma40_slope_5_pct < 0
    ):
        return Regime.BEARISH, (
            "QQQ 종가가 1개월선(20거래일)과 2개월선(40거래일) 아래에 있습니다.",
            "1개월선과 2개월선의 5거래일 기울기가 모두 하락 방향입니다.",
        )
    return Regime.NEUTRAL, ("가격 위치와 이동평균선 방향이 한쪽 흐름으로 모이지 않고 엇갈려 있습니다.",)


def _rank(
    candidates: tuple[SecuritySnapshot, ...],
    direction: Direction,
    count: int,
    deep_count: int,
) -> tuple[RankedMover, ...]:
    ordered = sorted(
        candidates,
        key=(lambda item: (-item.change_pct, item.symbol))
        if direction == Direction.GAINER
        else (lambda item: (item.change_pct, item.symbol)),
    )[:count]
    deep_symbols = {
        item.symbol
        for item in sorted(ordered, key=lambda item: (-item.anomaly_score, item.symbol))[:deep_count]
    }
    return tuple(
        RankedMover(
            rank=index,
            symbol=item.symbol,
            direction=direction,
            change_pct=item.change_pct,
            volume_ratio_20=item.volume_ratio_20,
            dollar_volume=item.dollar_volume,
            deep_dive=item.symbol in deep_symbols,
        )
        for index, item in enumerate(ordered, start=1)
    )


def build_market_snapshot(
    bars_by_symbol: dict[str, tuple[Bar, ...]],
    definitions: tuple[SecurityDefinition, ...],
    *,
    market_date: date,
    captured_at: datetime,
    previous_regime: Regime | None = None,
    top_count: int = 10,
    deep_count: int = 3,
    source: str = "alpaca",
) -> MarketSnapshot:
    definition_by_symbol = {item.symbol: item for item in definitions}
    securities: list[SecuritySnapshot] = []
    skipped: list[str] = []
    for symbol, definition in definition_by_symbol.items():
        try:
            securities.append(calculate_security(definition, bars_by_symbol.get(symbol, ())))
        except ValueError:
            skipped.append(symbol)

    stock_universe = tuple(
        item for item in securities if item.asset_type == AssetType.STOCK and item.symbol in definition_by_symbol
    )
    if len(stock_universe) < top_count * 2:
        raise ValueError(
            f"Need at least {top_count * 2} valid stock securities; got {len(stock_universe)}. "
            f"Skipped: {', '.join(skipped)}"
        )
    gain_candidates = tuple(item for item in stock_universe if item.change_pct > 0)
    loss_candidates = tuple(item for item in stock_universe if item.change_pct < 0)
    if len(gain_candidates) < top_count or len(loss_candidates) < top_count:
        raise ValueError(f"Need at least {top_count} positive and {top_count} negative movers")

    gainers = _rank(gain_candidates, Direction.GAINER, top_count, deep_count)
    losers = _rank(loss_candidates, Direction.LOSER, top_count, deep_count)
    qqq = next((item for item in securities if item.symbol == "QQQ"), None)
    if qqq is None:
        raise ValueError("QQQ bars are required for Nasdaq regime classification")
    current_regime, rationale = classify_regime(qqq)

    heatmap_candidates = [item for item in stock_universe if item.sector]
    total_dollar_volume = sum(item.dollar_volume for item in heatmap_candidates)
    heatmap = tuple(
        HeatmapEntry(
            symbol=item.symbol,
            sector=item.sector or "Unknown",
            change_pct=item.change_pct,
            weight=_round(item.dollar_volume / total_dollar_volume) if total_dollar_volume else 0.0,
        )
        for item in sorted(heatmap_candidates, key=lambda item: (item.sector or "", -item.dollar_volume, item.symbol))
    )
    deep_dive_symbols = tuple(
        item.symbol for item in (*gainers, *losers) if item.deep_dive
    )
    hash_input = {
        symbol: [
            [bar.timestamp.isoformat(), bar.open, bar.high, bar.low, bar.close, bar.volume]
            for bar in bars_by_symbol.get(symbol, ())
        ]
        for symbol in sorted(bars_by_symbol)
    }
    input_hash = hashlib.sha256(
        json.dumps(hash_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return MarketSnapshot(
        schema_version=SCHEMA_VERSION,
        market_date=market_date,
        captured_at=captured_at,
        source=source,
        universe=tuple(sorted(item.symbol for item in stock_universe)),
        securities=tuple(sorted(securities, key=lambda item: item.symbol)),
        gainers=gainers,
        losers=losers,
        deep_dive_symbols=deep_dive_symbols,
        market_etfs=DEFAULT_MARKET_ETFS,
        income_basket=tuple(dict.fromkeys((*DEFAULT_ETP_BASKET, *DEFAULT_DIVIDEND_STOCKS))),
        nasdaq_regime=NasdaqRegime(
            proxy_symbol="QQQ",
            state=current_regime,
            previous_state=previous_regime,
            changed=previous_regime is not None and previous_regime != current_regime,
            rationale=rationale,
        ),
        sector_heatmap=heatmap,
        input_hash=input_hash,
    )
