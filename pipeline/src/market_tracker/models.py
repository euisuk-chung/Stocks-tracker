from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA_VERSION = "2.0.0"


class Direction(str, Enum):
    GAINER = "gainer"
    LOSER = "loser"


class Regime(str, Enum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"


class EvidenceLevel(str, Enum):
    CONFIRMED = "confirmed"
    SUPPORTED = "supported"
    UNKNOWN = "unknown"


class ReviewVerdict(str, Enum):
    PASS = "pass"
    REVISE = "revise"
    BLOCK = "block"


class AssetType(str, Enum):
    STOCK = "stock"
    ETF = "etf"


class MovingAverageCross(str, Enum):
    GOLDEN = "golden"
    DEATH = "death"
    NONE = "none"


class LeadPointRole(str, Enum):
    MARKET = "market"
    SECTOR = "sector"
    CATALYST = "catalyst"


def _json_key(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return {_json_key(field.name): _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


class JsonModel:
    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True, slots=True)
class Bar(JsonModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None = None


@dataclass(frozen=True, slots=True)
class ChartPoint(JsonModel):
    date: date
    close: float
    volume: int
    sma20: float | None
    sma40: float | None


@dataclass(frozen=True, slots=True)
class SecuritySnapshot(JsonModel):
    symbol: str
    name: str
    asset_type: AssetType
    sector: str | None
    close: float
    previous_close: float
    change_pct: float
    dollar_volume: float
    average_volume_20: float
    volume_ratio_20: float
    sma20: float
    sma40: float
    sma20_slope_5_pct: float
    sma40_slope_5_pct: float
    distance_sma20_pct: float
    distance_sma40_pct: float
    moving_average_cross: MovingAverageCross
    anomaly_score: float
    history: tuple[ChartPoint, ...]


@dataclass(frozen=True, slots=True)
class RankedMover(JsonModel):
    rank: int
    symbol: str
    direction: Direction
    change_pct: float
    volume_ratio_20: float
    dollar_volume: float
    deep_dive: bool


@dataclass(frozen=True, slots=True)
class NasdaqRegime(JsonModel):
    proxy_symbol: str
    state: Regime
    previous_state: Regime | None
    changed: bool
    rationale: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HeatmapEntry(JsonModel):
    symbol: str
    sector: str
    change_pct: float
    weight: float


@dataclass(frozen=True, slots=True)
class MarketSnapshot(JsonModel):
    schema_version: str
    market_date: date
    captured_at: datetime
    source: str
    universe: tuple[str, ...]
    securities: tuple[SecuritySnapshot, ...]
    gainers: tuple[RankedMover, ...]
    losers: tuple[RankedMover, ...]
    deep_dive_symbols: tuple[str, ...]
    market_etfs: tuple[str, ...]
    income_basket: tuple[str, ...]
    nasdaq_regime: NasdaqRegime
    sector_heatmap: tuple[HeatmapEntry, ...]
    input_hash: str


@dataclass(frozen=True, slots=True)
class EvidenceSource(JsonModel):
    source_id: str
    title: str
    publisher: str
    url: str
    published_at: datetime
    checked_at: datetime
    primary: bool
    canonical_event_id: str | None = None
    source_type: str = "other"
    independence_key: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceItem(JsonModel):
    claim_id: str
    scope: str
    claim: str
    event_date: date
    market_reaction_date: date
    source_ids: tuple[str, ...]
    level: EvidenceLevel
    relevance: str
    uncertainty: str | None
    beginner_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Theme(JsonModel):
    theme_id: str
    title: str
    summary: str
    claim_ids: tuple[str, ...]
    symbols: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceLedger(JsonModel):
    schema_version: str
    market_date: date
    sources: tuple[EvidenceSource, ...]
    evidence: tuple[EvidenceItem, ...]
    themes: tuple[Theme, ...]


@dataclass(frozen=True, slots=True)
class ReviewIssue(JsonModel):
    code: str
    message: str
    references: tuple[str, ...]
    suggested_fix: str


@dataclass(frozen=True, slots=True)
class ReviewResult(JsonModel):
    reviewer: str
    verdict: ReviewVerdict
    blocking_issues: tuple[ReviewIssue, ...]
    improvements: tuple[ReviewIssue, ...]
    checked_items: tuple[str, ...]
    reviewed_at: datetime


@dataclass(frozen=True, slots=True)
class ReportMetadata(JsonModel):
    schema_version: str
    market_date: date
    captured_at: datetime
    generated_at: datetime
    snapshot_hash: str
    language: str = "ko-KR"
    educational_only: bool = True


@dataclass(frozen=True, slots=True)
class ReportQa(JsonModel):
    publishable: bool
    reviewer_statuses: Mapping[str, ReviewVerdict]
    validation_errors: tuple[str, ...]
    revision_count: int


@dataclass(frozen=True, slots=True)
class ReportMover(JsonModel):
    symbol: str
    rank: int
    direction: Direction
    deep_dive: bool
    summary: str
    chart_commentary: str
    risks: tuple[str, ...]
    claim_ids: tuple[str, ...]
    market_data: SecuritySnapshot


@dataclass(frozen=True, slots=True)
class LeadStoryPoint(JsonModel):
    role: LeadPointRole
    text: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LeadStory(JsonModel):
    headline: str
    takeaway: str
    supporting_points: tuple[LeadStoryPoint, ...]


@dataclass(frozen=True, slots=True)
class NextWatchItem(JsonModel):
    title: str
    description: str
    symbols: tuple[str, ...]
    claim_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DailyReport(JsonModel):
    metadata: ReportMetadata
    lead_story: LeadStory
    market_pulse: tuple[str, ...]
    nasdaq_regime: NasdaqRegime
    sector_heatmap: tuple[HeatmapEntry, ...]
    movers: tuple[ReportMover, ...]
    themes: tuple[Theme, ...]
    market_etfs: tuple[SecuritySnapshot, ...]
    income_basket: tuple[SecuritySnapshot, ...]
    sources: tuple[EvidenceSource, ...]
    source_ids: tuple[str, ...]
    reviews: tuple[ReviewResult, ...]
    qa: ReportQa
    next_watch: tuple[NextWatchItem, ...]
    disclaimer: str


def immutable_mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a shallow immutable mapping for auxiliary runtime state."""
    return MappingProxyType(dict(values))
