from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .models import (
    AssetType,
    ChartPoint,
    DailyReport,
    Direction,
    EvidenceItem,
    EvidenceLedger,
    EvidenceLevel,
    EvidenceSource,
    HeatmapEntry,
    LeadPointRole,
    LeadStory,
    LeadStoryPoint,
    MarketSnapshot,
    MovingAverageCross,
    NextWatchItem,
    NasdaqRegime,
    RankedMover,
    Regime,
    ReportMetadata,
    ReportMover,
    ReportQa,
    ReviewIssue,
    ReviewResult,
    ReviewVerdict,
    SecuritySnapshot,
    Theme,
    immutable_mapping,
)


def _date(value: Any) -> date:
    return date.fromisoformat(str(value))


def _datetime(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"datetime must include a timezone: {value}")
    return parsed


def _chart_point(raw: dict[str, Any]) -> ChartPoint:
    return ChartPoint(
        date=_date(raw["date"]),
        close=float(raw["close"]),
        volume=int(raw["volume"]),
        sma20=float(raw["sma20"]) if raw.get("sma20") is not None else None,
        sma40=float(raw["sma40"]) if raw.get("sma40") is not None else None,
    )


def _security(raw: dict[str, Any]) -> SecuritySnapshot:
    return SecuritySnapshot(
        symbol=str(raw["symbol"]),
        name=str(raw["name"]),
        asset_type=AssetType(raw["assetType"]),
        sector=raw.get("sector"),
        close=float(raw["close"]),
        previous_close=float(raw["previousClose"]),
        change_pct=float(raw["changePct"]),
        dollar_volume=float(raw["dollarVolume"]),
        average_volume_20=float(raw["averageVolume20"]),
        volume_ratio_20=float(raw["volumeRatio20"]),
        sma20=float(raw["sma20"]),
        sma40=float(raw["sma40"]),
        sma20_slope_5_pct=float(raw["sma20Slope5Pct"]),
        sma40_slope_5_pct=float(raw["sma40Slope5Pct"]),
        distance_sma20_pct=float(raw["distanceSma20Pct"]),
        distance_sma40_pct=float(raw["distanceSma40Pct"]),
        moving_average_cross=MovingAverageCross(raw["movingAverageCross"]),
        anomaly_score=float(raw["anomalyScore"]),
        history=tuple(_chart_point(item) for item in raw["history"]),
    )


def _ranked_mover(raw: dict[str, Any]) -> RankedMover:
    return RankedMover(
        rank=int(raw["rank"]),
        symbol=str(raw["symbol"]),
        direction=Direction(raw["direction"]),
        change_pct=float(raw["changePct"]),
        volume_ratio_20=float(raw["volumeRatio20"]),
        dollar_volume=float(raw["dollarVolume"]),
        deep_dive=bool(raw["deepDive"]),
    )


def _regime(raw: dict[str, Any]) -> NasdaqRegime:
    return NasdaqRegime(
        proxy_symbol=str(raw["proxySymbol"]),
        state=Regime(raw["state"]),
        previous_state=Regime(raw["previousState"]) if raw.get("previousState") else None,
        changed=bool(raw["changed"]),
        rationale=tuple(str(item) for item in raw["rationale"]),
    )


def _heatmap(raw: dict[str, Any]) -> HeatmapEntry:
    return HeatmapEntry(
        symbol=str(raw["symbol"]),
        sector=str(raw["sector"]),
        change_pct=float(raw["changePct"]),
        weight=float(raw["weight"]),
    )


def parse_snapshot(raw: dict[str, Any]) -> MarketSnapshot:
    return MarketSnapshot(
        schema_version=str(raw["schemaVersion"]),
        market_date=_date(raw["marketDate"]),
        captured_at=_datetime(raw["capturedAt"]),
        source=str(raw["source"]),
        universe=tuple(str(item) for item in raw["universe"]),
        securities=tuple(_security(item) for item in raw["securities"]),
        gainers=tuple(_ranked_mover(item) for item in raw["gainers"]),
        losers=tuple(_ranked_mover(item) for item in raw["losers"]),
        deep_dive_symbols=tuple(str(item) for item in raw["deepDiveSymbols"]),
        market_etfs=tuple(str(item) for item in raw["marketEtfs"]),
        income_basket=tuple(str(item) for item in raw["incomeBasket"]),
        nasdaq_regime=_regime(raw["nasdaqRegime"]),
        sector_heatmap=tuple(_heatmap(item) for item in raw["sectorHeatmap"]),
        input_hash=str(raw["inputHash"]),
    )


def _source(raw: dict[str, Any]) -> EvidenceSource:
    return EvidenceSource(
        source_id=str(raw["sourceId"]),
        title=str(raw["title"]),
        publisher=str(raw["publisher"]),
        url=str(raw["url"]),
        published_at=_datetime(raw["publishedAt"]),
        checked_at=_datetime(raw["checkedAt"]),
        primary=bool(raw["primary"]),
        canonical_event_id=raw.get("canonicalEventId"),
        source_type=str(raw.get("sourceType", "other")),
        independence_key=raw.get("independenceKey"),
    )


def _evidence(raw: dict[str, Any]) -> EvidenceItem:
    return EvidenceItem(
        claim_id=str(raw["claimId"]),
        scope=str(raw["scope"]),
        claim=str(raw["claim"]),
        event_date=_date(raw["eventDate"]),
        market_reaction_date=_date(raw["marketReactionDate"]),
        source_ids=tuple(str(item) for item in raw["sourceIds"]),
        level=EvidenceLevel(raw["level"]),
        relevance=str(raw["relevance"]),
        uncertainty=raw.get("uncertainty"),
        beginner_terms=tuple(str(item) for item in raw["beginnerTerms"]),
    )


def _theme(raw: dict[str, Any]) -> Theme:
    return Theme(
        theme_id=str(raw["themeId"]),
        title=str(raw["title"]),
        summary=str(raw["summary"]),
        claim_ids=tuple(str(item) for item in raw["claimIds"]),
        symbols=tuple(str(item) for item in raw["symbols"]),
    )


def parse_ledger(raw: dict[str, Any]) -> EvidenceLedger:
    return EvidenceLedger(
        schema_version=str(raw["schemaVersion"]),
        market_date=_date(raw["marketDate"]),
        sources=tuple(_source(item) for item in raw["sources"]),
        evidence=tuple(_evidence(item) for item in raw["evidence"]),
        themes=tuple(_theme(item) for item in raw["themes"]),
    )


def _issue(raw: dict[str, Any]) -> ReviewIssue:
    return ReviewIssue(
        code=str(raw["code"]),
        message=str(raw["message"]),
        references=tuple(str(item) for item in raw["references"]),
        suggested_fix=str(raw["suggestedFix"]),
    )


def _review(raw: dict[str, Any]) -> ReviewResult:
    return ReviewResult(
        reviewer=str(raw["reviewer"]),
        verdict=ReviewVerdict(raw["verdict"]),
        blocking_issues=tuple(_issue(item) for item in raw["blockingIssues"]),
        improvements=tuple(_issue(item) for item in raw["improvements"]),
        checked_items=tuple(str(item) for item in raw["checkedItems"]),
        reviewed_at=_datetime(raw["reviewedAt"]),
    )


def _report_mover(raw: dict[str, Any]) -> ReportMover:
    return ReportMover(
        symbol=str(raw["symbol"]),
        rank=int(raw["rank"]),
        direction=Direction(raw["direction"]),
        deep_dive=bool(raw["deepDive"]),
        summary=str(raw["summary"]),
        chart_commentary=str(raw["chartCommentary"]),
        risks=tuple(str(item) for item in raw["risks"]),
        claim_ids=tuple(str(item) for item in raw["claimIds"]),
        market_data=_security(raw["marketData"]),
    )


def _lead_story_point(raw: dict[str, Any]) -> LeadStoryPoint:
    return LeadStoryPoint(
        role=LeadPointRole(raw["role"]),
        text=str(raw["text"]),
        claim_ids=tuple(str(item) for item in raw["claimIds"]),
    )


def _lead_story(raw: dict[str, Any]) -> LeadStory:
    return LeadStory(
        headline=str(raw["headline"]),
        takeaway=str(raw["takeaway"]),
        supporting_points=tuple(_lead_story_point(item) for item in raw["supportingPoints"]),
    )


def _next_watch(raw: dict[str, Any]) -> NextWatchItem:
    return NextWatchItem(
        title=str(raw["title"]),
        description=str(raw["description"]),
        symbols=tuple(str(item) for item in raw["symbols"]),
        claim_ids=tuple(str(item) for item in raw["claimIds"]),
    )


def parse_report(raw: dict[str, Any]) -> DailyReport:
    metadata = raw["metadata"]
    qa = raw["qa"]
    return DailyReport(
        metadata=ReportMetadata(
            schema_version=str(metadata["schemaVersion"]),
            market_date=_date(metadata["marketDate"]),
            captured_at=_datetime(metadata["capturedAt"]),
            generated_at=_datetime(metadata["generatedAt"]),
            snapshot_hash=str(metadata["snapshotHash"]),
            language=str(metadata.get("language", "ko-KR")),
            educational_only=bool(metadata.get("educationalOnly", True)),
        ),
        lead_story=_lead_story(raw["leadStory"]),
        market_pulse=tuple(str(item) for item in raw["marketPulse"]),
        nasdaq_regime=_regime(raw["nasdaqRegime"]),
        sector_heatmap=tuple(_heatmap(item) for item in raw["sectorHeatmap"]),
        movers=tuple(_report_mover(item) for item in raw["movers"]),
        themes=tuple(_theme(item) for item in raw["themes"]),
        market_etfs=tuple(_security(item) for item in raw["marketEtfs"]),
        income_basket=tuple(_security(item) for item in raw["incomeBasket"]),
        sources=tuple(_source(item) for item in raw["sources"]),
        source_ids=tuple(str(item) for item in raw["sourceIds"]),
        reviews=tuple(_review(item) for item in raw["reviews"]),
        qa=ReportQa(
            publishable=bool(qa["publishable"]),
            reviewer_statuses=immutable_mapping(
                {name: ReviewVerdict(verdict) for name, verdict in qa["reviewerStatuses"].items()}
            ),
            validation_errors=tuple(str(item) for item in qa["validationErrors"]),
            revision_count=int(qa["revisionCount"]),
        ),
        next_watch=tuple(_next_watch(item) for item in raw["nextWatch"]),
        disclaimer=str(raw["disclaimer"]),
    )
