from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import EvidenceItem, EvidenceLedger, EvidenceLevel, EvidenceSource, SCHEMA_VERSION, Theme


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in {"ref", "source"}
        )
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def normalize_ledger(
    *,
    market_date: date,
    sources: tuple[EvidenceSource, ...],
    evidence: tuple[EvidenceItem, ...],
    themes: tuple[Theme, ...],
) -> EvidenceLedger:
    """Deduplicate sources and conservatively normalize evidence levels."""
    source_by_key: dict[str, EvidenceSource] = {}
    replaced_source_ids: dict[str, str] = {}
    for source in sources:
        event_key = source.canonical_event_id or canonicalize_url(source.url)
        if event_key in source_by_key:
            replaced_source_ids[source.source_id] = source_by_key[event_key].source_id
            continue
        clean = replace(source, url=canonicalize_url(source.url))
        source_by_key[event_key] = clean
        replaced_source_ids[source.source_id] = clean.source_id

    normalized_sources = tuple(sorted(source_by_key.values(), key=lambda item: item.source_id))
    source_lookup = {item.source_id: item for item in normalized_sources}
    normalized_evidence: list[EvidenceItem] = []
    for item in evidence:
        source_ids = tuple(dict.fromkeys(replaced_source_ids.get(source_id, source_id) for source_id in item.source_ids))
        linked = [source_lookup[source_id] for source_id in source_ids if source_id in source_lookup]
        independence_count = len(
            {
                (source.independence_key or source.publisher).casefold()
                for source in linked
            }
        )
        has_primary = any(source.primary for source in linked)
        level = item.level
        uncertainty = item.uncertainty
        if item.event_date > item.market_reaction_date:
            level = EvidenceLevel.UNKNOWN
            uncertainty = uncertainty or "사건 시점이 시장 반응보다 늦어 원인으로 연결할 수 없습니다."
        elif has_primary:
            level = EvidenceLevel.CONFIRMED
        elif independence_count >= 2:
            level = EvidenceLevel.SUPPORTED
        else:
            level = EvidenceLevel.UNKNOWN
            uncertainty = uncertainty or "독립적인 일반 뉴스 출처가 2개 미만입니다."
        normalized_evidence.append(
            replace(item, source_ids=source_ids, level=level, uncertainty=uncertainty)
        )

    valid_claims = {
        item.claim_id for item in normalized_evidence if item.level != EvidenceLevel.UNKNOWN
    }
    normalized_themes = tuple(
        replace(theme, claim_ids=tuple(claim for claim in theme.claim_ids if claim in valid_claims))
        for theme in themes[:3]
        if any(claim in valid_claims for claim in theme.claim_ids)
    )
    return EvidenceLedger(
        schema_version=SCHEMA_VERSION,
        market_date=market_date,
        sources=normalized_sources,
        evidence=tuple(sorted(normalized_evidence, key=lambda item: item.claim_id)),
        themes=normalized_themes,
    )


def evidence_window(market_date: date) -> tuple[date, date]:
    return market_date - timedelta(days=7), market_date
