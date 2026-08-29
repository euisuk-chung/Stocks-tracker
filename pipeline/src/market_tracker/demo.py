from __future__ import annotations

import math
from datetime import date, datetime, time, timezone

from .calculations import build_market_snapshot
from .calendar import trading_days_ending
from .config import DEFAULT_DIVIDEND_STOCKS, DEFAULT_ETP_BASKET, DEFAULT_MARKET_ETFS, SecurityDefinition
from .evidence import normalize_ledger
from .models import (
    Bar,
    DailyReport,
    EvidenceItem,
    EvidenceLedger,
    EvidenceLevel,
    EvidenceSource,
    ReportMetadata,
    ReportMover,
    ReportQa,
    ReviewResult,
    ReviewVerdict,
    SCHEMA_VERSION,
    MarketSnapshot,
    Theme,
    immutable_mapping,
)


DEMO_STOCKS = (
    ("AAPL", "Apple", "Technology"),
    ("MSFT", "Microsoft", "Technology"),
    ("NVDA", "NVIDIA", "Technology"),
    ("AMZN", "Amazon", "Consumer Cyclical"),
    ("META", "Meta Platforms", "Communication Services"),
    ("GOOGL", "Alphabet", "Communication Services"),
    ("JPM", "JPMorgan Chase", "Financial"),
    ("XOM", "Exxon Mobil", "Energy"),
    ("LLY", "Eli Lilly", "Healthcare"),
    ("GE", "GE Aerospace", "Industrials"),
    ("WMT", "Walmart", "Consumer Defensive"),
    ("NEE", "NextEra Energy", "Utilities"),
    ("TSLA", "Tesla", "Consumer Cyclical"),
    ("AMD", "Advanced Micro Devices", "Technology"),
    ("NFLX", "Netflix", "Communication Services"),
    ("BA", "Boeing", "Industrials"),
    ("CVX", "Chevron", "Energy"),
    ("JNJ", "Johnson & Johnson", "Healthcare"),
    ("PG", "Procter & Gamble", "Consumer Defensive"),
    ("KO", "Coca-Cola", "Consumer Defensive"),
    ("MCD", "McDonald's", "Consumer Cyclical"),
    ("O", "Realty Income", "Real Estate"),
    ("UPS", "UPS", "Industrials"),
    ("BAC", "Bank of America", "Financial"),
)


def demo_definitions() -> tuple[SecurityDefinition, ...]:
    definitions = [SecurityDefinition(symbol, name, sector) for symbol, name, sector in DEMO_STOCKS]
    existing = {item.symbol for item in definitions}
    for symbol in dict.fromkeys((*DEFAULT_MARKET_ETFS, *DEFAULT_ETP_BASKET)):
        if symbol not in existing:
            definitions.append(SecurityDefinition(symbol, symbol, "ETF", "etf"))
            existing.add(symbol)
    for symbol in DEFAULT_DIVIDEND_STOCKS:
        if symbol not in existing:
            definitions.append(SecurityDefinition(symbol, symbol, "Dividend Basket"))
            existing.add(symbol)
    return tuple(definitions)


def demo_bars(market_date: date) -> dict[str, tuple[Bar, ...]]:
    sessions = trading_days_ending(market_date, 70)
    definitions = demo_definitions()
    results: dict[str, tuple[Bar, ...]] = {}
    for symbol_index, definition in enumerate(definitions):
        base = 45.0 + symbol_index * 7.0
        trend = 0.0018 if definition.symbol == "QQQ" else ((symbol_index % 5) - 2) * 0.00025
        closes: list[float] = []
        for index in range(len(sessions)):
            wave = math.sin((index + symbol_index) / 6) * 0.006
            closes.append(base * (1 + trend * index + wave))
        if definition.asset_type == "stock":
            magnitude = 0.012 + (symbol_index % 12) * 0.0025
            signed_change = magnitude if symbol_index < 12 else -magnitude
            closes[-1] = closes[-2] * (1 + signed_change)
        elif definition.symbol == "QQQ":
            closes[-1] = closes[-2] * 1.006
        bars: list[Bar] = []
        for index, (session, close) in enumerate(zip(sessions, closes, strict=True)):
            volume = 1_000_000 + symbol_index * 25_000 + index * 2_500
            if index == len(sessions) - 1:
                volume = int(volume * (1.25 + (symbol_index % 4) * 0.2))
            bars.append(
                Bar(
                    symbol=definition.symbol,
                    timestamp=datetime.combine(session, time(21, 0), tzinfo=timezone.utc),
                    open=round(close * 0.995, 4),
                    high=round(close * 1.01, 4),
                    low=round(close * 0.99, 4),
                    close=round(close, 4),
                    volume=volume,
                    vwap=round(close, 4),
                )
            )
        results[definition.symbol] = tuple(bars)
    return results


def build_demo_documents(market_date: date) -> tuple[MarketSnapshot, EvidenceLedger, DailyReport]:
    captured_at = datetime.combine(market_date, time(23, 0), tzinfo=timezone.utc)
    snapshot = build_market_snapshot(
        demo_bars(market_date),
        demo_definitions(),
        market_date=market_date,
        captured_at=captured_at,
        source="demo-fixture",
    )
    sources: list[EvidenceSource] = []
    evidence: list[EvidenceItem] = []
    for index, symbol in enumerate(snapshot.deep_dive_symbols, start=1):
        source_id = f"src-{index:02d}"
        claim_id = f"claim-{index:02d}"
        sources.append(
            EvidenceSource(
                source_id=source_id,
                title=f"{symbol} 공식 발표 예시",
                publisher=f"{symbol} Investor Relations",
                url=f"https://example.com/{symbol.lower()}/event-{index}",
                published_at=captured_at,
                checked_at=captured_at,
                primary=True,
                canonical_event_id=f"event-{index}",
                source_type="company_ir",
                independence_key=f"{symbol.lower()}-ir",
            )
        )
        evidence.append(
            EvidenceItem(
                claim_id=claim_id,
                scope=symbol,
                claim=f"{symbol}의 공식 발표가 확인됐습니다. 이 문장은 계약 검증용 데모 데이터입니다.",
                event_date=market_date,
                market_reaction_date=market_date,
                source_ids=(source_id,),
                level=EvidenceLevel.CONFIRMED,
                relevance="당일 변동과 같은 날 공개된 공식 자료입니다.",
                uncertainty=None,
                beginner_terms=("거래량", "이동평균선"),
            )
        )
    themes = (
        Theme(
            theme_id="theme-01",
            title="기술주 변동성",
            summary="기술주 중심으로 거래량을 동반한 가격 변화가 나타난 데모 테마입니다.",
            claim_ids=tuple(item.claim_id for item in evidence[:2]),
            symbols=tuple(snapshot.deep_dive_symbols[:2]),
        ),
        Theme(
            theme_id="theme-02",
            title="경기민감주 재평가",
            summary="경기민감 업종의 움직임을 묶은 데모 테마입니다.",
            claim_ids=tuple(item.claim_id for item in evidence[2:4]),
            symbols=tuple(snapshot.deep_dive_symbols[2:4]),
        ),
    )
    ledger = normalize_ledger(
        market_date=market_date,
        sources=tuple(sources),
        evidence=tuple(evidence),
        themes=themes,
    )
    claim_by_symbol = {item.scope: item.claim_id for item in ledger.evidence}
    security_by_symbol = {item.symbol: item for item in snapshot.securities}
    movers: list[ReportMover] = []
    for mover in (*snapshot.gainers, *snapshot.losers):
        security = security_by_symbol[mover.symbol]
        claim_ids = (claim_by_symbol[mover.symbol],) if mover.symbol in claim_by_symbol else ()
        summary = (
            ledger.evidence[next(i for i, item in enumerate(ledger.evidence) if item.claim_id == claim_ids[0])].claim
            if claim_ids
            else "확인된 단일 촉매 없음"
        )
        position = "위" if security.close >= security.sma20 else "아래"
        movers.append(
            ReportMover(
                symbol=mover.symbol,
                rank=mover.rank,
                direction=mover.direction,
                deep_dive=mover.deep_dive,
                summary=summary,
                chart_commentary=f"종가는 20일 이동평균선 {position}에 있습니다. 이를 매매 신호로 단정하지 않습니다.",
                risks=("단일 거래일의 가격 변화만으로 추세를 확정할 수 없습니다.",),
                claim_ids=claim_ids,
                market_data=security,
            )
        )
    reviews = tuple(
        ReviewResult(
            reviewer=name,
            verdict=ReviewVerdict.PASS,
            blocking_issues=(),
            improvements=(),
            checked_items=("numbers", "claims", "language"),
            reviewed_at=captured_at,
        )
        for name in ("fact_checker", "blog_quality_reviewer", "humanify_reviewer")
    )
    statuses = immutable_mapping({review.reviewer: review.verdict for review in reviews})
    report = DailyReport(
        metadata=ReportMetadata(
            schema_version=SCHEMA_VERSION,
            market_date=market_date,
            captured_at=captured_at,
            generated_at=captured_at,
            snapshot_hash=snapshot.input_hash,
        ),
        market_pulse=(
            "S&P 500 구성 종목의 상승·하락 폭을 함께 살펴봅니다.",
            f"Nasdaq 대용 지표 QQQ의 국면은 {snapshot.nasdaq_regime.state.value}입니다.",
            "거래량과 이동평균선은 맥락을 돕는 관찰 지표이며 매매 신호가 아닙니다.",
        ),
        nasdaq_regime=snapshot.nasdaq_regime,
        sector_heatmap=snapshot.sector_heatmap,
        movers=tuple(movers),
        themes=ledger.themes,
        market_etfs=tuple(security_by_symbol[symbol] for symbol in snapshot.market_etfs),
        income_basket=tuple(security_by_symbol[symbol] for symbol in snapshot.income_basket),
        sources=ledger.sources,
        source_ids=tuple(item.source_id for item in ledger.sources),
        reviews=reviews,
        qa=ReportQa(
            publishable=True,
            reviewer_statuses=statuses,
            validation_errors=(),
            revision_count=0,
        ),
        disclaimer="이 리포트는 교육 목적의 정보이며 투자 조언이나 매수·매도 추천이 아닙니다.",
    )
    return snapshot, ledger, report
