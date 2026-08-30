from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse

from .evidence import evidence_window
from .models import (
    DailyReport,
    EvidenceLedger,
    EvidenceLevel,
    LeadPointRole,
    MarketSnapshot,
    ReviewVerdict,
    SCHEMA_VERSION,
)


REQUIRED_REVIEWERS = frozenset({"fact_checker", "blog_quality_reviewer", "humanify_reviewer"})
SECRET_PATTERNS = (
    re.compile(r"APCA-API-(?:KEY|SECRET)", re.IGNORECASE),
    re.compile(r"ALPACA_(?:API_KEY|SECRET_KEY)", re.IGNORECASE),
)


def validate_snapshot(snapshot: MarketSnapshot) -> tuple[str, ...]:
    errors: list[str] = []
    if snapshot.schema_version != SCHEMA_VERSION:
        errors.append("snapshot schemaVersion is unsupported")
    if len(snapshot.gainers) != 10 or len(snapshot.losers) != 10:
        errors.append("snapshot must contain exactly 10 gainers and 10 losers")
    if len(snapshot.deep_dive_symbols) != 6 or len(set(snapshot.deep_dive_symbols)) != 6:
        errors.append("snapshot must contain exactly 6 unique deep-dive symbols")
    if [item.rank for item in snapshot.gainers] != list(range(1, 11)):
        errors.append("gainer ranks must be contiguous from 1 to 10")
    if [item.rank for item in snapshot.losers] != list(range(1, 11)):
        errors.append("loser ranks must be contiguous from 1 to 10")
    if any(item.change_pct <= 0 for item in snapshot.gainers):
        errors.append("every gainer must have a positive changePct")
    if any(item.change_pct >= 0 for item in snapshot.losers):
        errors.append("every loser must have a negative changePct")
    if "QQQ" not in {item.symbol for item in snapshot.securities}:
        errors.append("QQQ security data is missing")
    if any(len(item.history) < 30 for item in snapshot.securities):
        errors.append("each security must have at least 30 chart points")
    if any(not item.history or item.history[-1].date != snapshot.market_date for item in snapshot.securities):
        errors.append("each security must end on snapshot marketDate")
    if abs(sum(item.weight for item in snapshot.sector_heatmap) - 1.0) > 0.01:
        errors.append("sector heatmap weights must sum to approximately 1")
    if len(snapshot.input_hash) != 64:
        errors.append("snapshot inputHash must be a SHA-256 hex digest")
    return tuple(errors)


def validate_ledger(ledger: EvidenceLedger, snapshot: MarketSnapshot) -> tuple[str, ...]:
    errors: list[str] = []
    if ledger.schema_version != SCHEMA_VERSION:
        errors.append("ledger schemaVersion is unsupported")
    if ledger.market_date != snapshot.market_date:
        errors.append("ledger marketDate does not match snapshot")
    source_ids = [item.source_id for item in ledger.sources]
    claim_ids = [item.claim_id for item in ledger.evidence]
    if len(source_ids) != len(set(source_ids)):
        errors.append("ledger sourceId values must be unique")
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("ledger claimId values must be unique")
    source_lookup = {item.source_id: item for item in ledger.sources}
    window_start, window_end = evidence_window(snapshot.market_date)
    for source in ledger.sources:
        parsed = urlparse(source.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"source {source.source_id} has an invalid URL")
        if not window_start <= source.published_at.date() <= window_end:
            errors.append(f"source {source.source_id} is outside the 7-day evidence window")
    for item in ledger.evidence:
        linked = [source_lookup.get(source_id) for source_id in item.source_ids]
        if any(source is None for source in linked):
            errors.append(f"claim {item.claim_id} references an unknown sourceId")
            continue
        valid_sources = [source for source in linked if source is not None]
        if item.event_date > item.market_reaction_date:
            errors.append(f"claim {item.claim_id} event occurs after its market reaction")
        if any(source.published_at.date() > item.market_reaction_date for source in valid_sources):
            errors.append(f"claim {item.claim_id} uses a source published after the market reaction")
        if item.level == EvidenceLevel.CONFIRMED and not any(source.primary for source in valid_sources):
            errors.append(f"confirmed claim {item.claim_id} lacks a primary source")
        if item.level == EvidenceLevel.SUPPORTED:
            independence_keys = {
                (source.independence_key or source.publisher).casefold()
                for source in valid_sources
            }
            if len(independence_keys) < 2:
                errors.append(f"supported claim {item.claim_id} lacks two independent sources")
    if len(ledger.themes) > 3:
        errors.append("ledger may contain at most 3 themes")
    valid_claim_ids = {
        item.claim_id for item in ledger.evidence if item.level != EvidenceLevel.UNKNOWN
    }
    for theme in ledger.themes:
        if not theme.claim_ids or not set(theme.claim_ids).issubset(valid_claim_ids):
            errors.append(f"theme {theme.theme_id} must reference supported or confirmed claims")
    return tuple(errors)


def validate_report(
    report: DailyReport,
    snapshot: MarketSnapshot,
    ledger: EvidenceLedger,
) -> tuple[str, ...]:
    errors = [*validate_snapshot(snapshot), *validate_ledger(ledger, snapshot)]
    if report.metadata.schema_version != SCHEMA_VERSION:
        errors.append("report schemaVersion is unsupported")
    if report.metadata.market_date != snapshot.market_date:
        errors.append("report metadata.marketDate does not match snapshot")
    if report.metadata.snapshot_hash != snapshot.input_hash:
        errors.append("report snapshotHash does not match snapshot inputHash")
    if len(report.market_pulse) != 3:
        errors.append("report marketPulse must contain exactly 3 lines")
    if not report.lead_story.headline.strip() or not report.lead_story.takeaway.strip():
        errors.append("report leadStory headline and takeaway are required")
    if report.lead_story.headline.strip() == "오늘 시장에서 놓치지 말아야 할 변화":
        errors.append("report leadStory headline must be specific to the market date")
    lead_roles = [item.role for item in report.lead_story.supporting_points]
    if len(lead_roles) != 3 or set(lead_roles) != set(LeadPointRole):
        errors.append("report leadStory must contain market, sector, and catalyst support exactly once")
    if any(item.claim_ids for item in report.lead_story.supporting_points if item.role != LeadPointRole.CATALYST):
        errors.append("report market and sector lead points must not contain causal claimIds")
    if len(report.next_watch) < 1 or len(report.next_watch) > 3:
        errors.append("report nextWatch must contain between 1 and 3 items")
    if len(report.movers) != 20:
        errors.append("report must contain exactly 20 movers")

    expected = {
        (item.symbol, item.rank, item.direction, item.deep_dive)
        for item in (*snapshot.gainers, *snapshot.losers)
    }
    actual = {(item.symbol, item.rank, item.direction, item.deep_dive) for item in report.movers}
    if actual != expected:
        errors.append("report movers do not match snapshot rankings")
    if sum(item.deep_dive for item in report.movers) != 6:
        errors.append("report must identify exactly 6 deep-dive movers")

    ledger_claims = {item.claim_id for item in ledger.evidence}
    used_claims = {claim for mover in report.movers for claim in mover.claim_ids}
    used_claims.update(claim for theme in report.themes for claim in theme.claim_ids)
    used_claims.update(claim for point in report.lead_story.supporting_points for claim in point.claim_ids)
    used_claims.update(claim for item in report.next_watch for claim in item.claim_ids)
    unknown_claims = used_claims - ledger_claims
    if unknown_claims:
        errors.append(f"report references unknown claimIds: {', '.join(sorted(unknown_claims))}")
    ledger_sources = {item.source_id for item in ledger.sources}
    if not set(report.source_ids).issubset(ledger_sources):
        errors.append("report references unknown sourceIds")
    if report.sources != ledger.sources:
        errors.append("report sources differ from evidence ledger")
    if report.nasdaq_regime != snapshot.nasdaq_regime:
        errors.append("report Nasdaq regime differs from snapshot")
    snapshot_by_symbol = {item.symbol: item for item in snapshot.securities}
    if tuple(item.symbol for item in report.market_etfs) != snapshot.market_etfs:
        errors.append("report marketEtfs do not match snapshot")
    if tuple(item.symbol for item in report.income_basket) != snapshot.income_basket:
        errors.append("report incomeBasket does not match snapshot")
    if any(item.market_data != snapshot_by_symbol.get(item.symbol) for item in report.movers):
        errors.append("report mover marketData differs from snapshot")
    if any(item != snapshot_by_symbol.get(item.symbol) for item in (*report.market_etfs, *report.income_basket)):
        errors.append("report basket market data differs from snapshot")

    reviewer_names = [review.reviewer for review in report.reviews]
    if set(reviewer_names) != REQUIRED_REVIEWERS or len(reviewer_names) != len(REQUIRED_REVIEWERS):
        errors.append("report must contain exactly one result from each required reviewer")
    reviewer_statuses = {review.reviewer: review.verdict for review in report.reviews}
    if dict(report.qa.reviewer_statuses) != reviewer_statuses:
        errors.append("qa reviewerStatuses do not match review results")
    review_gate = (
        reviewer_statuses.get("fact_checker") == ReviewVerdict.PASS
        and all(verdict != ReviewVerdict.BLOCK for verdict in reviewer_statuses.values())
    )
    expected_publishable = review_gate and not errors and not report.qa.validation_errors
    if report.qa.publishable != expected_publishable:
        errors.append("qa.publishable does not match validation and review status")
    if report.qa.revision_count < 0 or report.qa.revision_count > 2:
        errors.append("qa revisionCount must be between 0 and 2")
    if not report.metadata.educational_only:
        errors.append("report must be marked educationalOnly")

    serialized = str(report.to_dict())
    if any(pattern.search(serialized) for pattern in SECRET_PATTERNS):
        errors.append("report appears to contain a secret variable or credential")
    return tuple(dict.fromkeys(errors))


def validate_json_contract(document: dict, kind: str) -> tuple[str, ...]:
    """Fast structural guard for JSON returned by agents before model construction."""
    required: dict[str, tuple[str, ...]] = {
        "snapshot": ("schemaVersion", "marketDate", "capturedAt", "gainers", "losers", "inputHash"),
        "ledger": ("schemaVersion", "marketDate", "sources", "evidence", "themes"),
        "report": ("metadata", "leadStory", "marketPulse", "nasdaqRegime", "movers", "marketEtfs", "incomeBasket", "sources", "reviews", "qa", "nextWatch", "disclaimer"),
        "review": ("reviewer", "verdict", "blockingIssues", "improvements", "checkedItems", "reviewedAt"),
    }
    if kind not in required:
        raise ValueError(f"Unknown contract kind: {kind}")
    errors = [f"missing required field: {field}" for field in required[kind] if field not in document]
    if kind == "report" and isinstance(document.get("metadata"), dict):
        if "marketDate" not in document["metadata"]:
            errors.append("missing required field: metadata.marketDate")
    if kind == "report" and isinstance(document.get("qa"), dict):
        if "publishable" not in document["qa"]:
            errors.append("missing required field: qa.publishable")
        if "reviewerStatuses" not in document["qa"]:
            errors.append("missing required field: qa.reviewerStatuses")
    return tuple(errors)


def duplicate_values(values: list[str]) -> set[str]:
    return {value for value, count in Counter(values).items() if count > 1}
