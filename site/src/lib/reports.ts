export type Regime = '강세' | '중립' | '약세';

export interface ChartPoint {
  date: string;
  close: number;
  ma20?: number | null;
  ma40?: number | null;
}

export interface Mover {
  symbol: string;
  name: string;
  sector: string;
  close: number;
  changePct: number;
  volumeRatio: number;
  deepDive: boolean;
}

export interface DailyReport {
  metadata: { marketDate: string; generatedAt: string; dataSource: string; isDemo: boolean };
  leadStory: {
    headline: string;
    takeaway: string;
    supportingPoints: Array<{ role: 'market' | 'sector' | 'catalyst'; text: string; claimIds: string[] }>;
  };
  summary: string[];
  marketPulse: Array<{ ticker: string; name: string; tracks: string; role: string; close: number; changePct: number }>;
  nasdaqRegime: { current: Regime; previous: Regime | '이전 기록 없음'; explanation: string };
  sectorHeatmap: Array<{ sector: string; symbol: string; changePct: number; dollarVolume: number }>;
  movers: { gainers: Mover[]; losers: Mover[] };
  deepDives: Array<{
    symbol: string;
    headline: string;
    explanation: string;
    risk: string;
    chartReading: string;
    claimIds: string[];
    chart: ChartPoint[];
  }>;
  themes: Array<{ title: string; summary: string; symbols: string[]; claimIds: string[] }>;
  incomeBasket: Array<{ symbol: string; name: string; kind: 'ETF' | '주식'; description: string; changePct: number }>;
  sources: Array<{ id: string; title: string; publisher: string; url: string; publishedAt: string }>;
  qa: { publishable: boolean; rounds: number; reviews: Array<{ reviewer: string; verdict: 'pass' | 'revise' | 'block' }> };
  nextWatch: Array<{ title: string; description: string; symbols: string[]; claimIds: string[] }>;
}

interface RawSecurity {
  symbol: string;
  name: string;
  assetType: 'stock' | 'etf';
  sector: string | null;
  close: number;
  changePct: number;
  volumeRatio20: number;
  distanceSma20Pct: number;
  movingAverageCross: 'golden' | 'death' | 'none';
  history: Array<{ date: string; close: number; sma20: number | null; sma40: number | null }>;
}

interface RawReport {
  metadata: { marketDate: string; generatedAt: string };
  leadStory: DailyReport['leadStory'];
  marketPulse: string[];
  nasdaqRegime: {
    state: 'bullish' | 'neutral' | 'bearish';
    previousState: 'bullish' | 'neutral' | 'bearish' | null;
    rationale: string[];
  };
  sectorHeatmap: Array<{ sector: string; symbol: string; changePct: number; weight: number }>;
  movers: Array<{
    symbol: string;
    rank: number;
    direction: 'gainer' | 'loser';
    deepDive: boolean;
    summary: string;
    chartCommentary: string;
    risks: string[];
    claimIds: string[];
    marketData: RawSecurity;
  }>;
  themes: Array<{ title: string; summary: string; symbols: string[]; claimIds: string[] }>;
  marketEtfs: RawSecurity[];
  incomeBasket: RawSecurity[];
  sources: Array<{ sourceId: string; title: string; publisher: string; url: string; publishedAt: string }>;
  reviews: Array<{ reviewer: string; verdict: 'pass' | 'revise' | 'block' }>;
  qa: { publishable: boolean; revisionCount: number };
  nextWatch: DailyReport['nextWatch'];
}

const regimeLabels = { bullish: '강세', neutral: '중립', bearish: '약세' } as const;
const marketReferences: Record<string, { name: string; tracks: string; role: string }> = {
  SPY: { name: 'S&P 500', tracks: '미국 대형주 약 500곳', role: '미국 대형주 시장의 체온계' },
  QQQ: { name: 'Nasdaq-100', tracks: 'Nasdaq 상장 비금융 대형주 100곳', role: '대형 성장주 흐름을 보는 창' },
  DIA: { name: 'Dow 30', tracks: '미국 대표 우량주 30곳', role: '전통 대형주의 흐름을 보는 지표' },
  IWM: { name: 'Russell 2000', tracks: '미국 중소형주 약 2,000곳', role: '중소형주 투자심리의 체온계' },
};

function normalizeReport(raw: RawReport): DailyReport {
  const toMover = (item: RawReport['movers'][number]): Mover => ({
    symbol: item.symbol,
    name: item.marketData.name,
    sector: item.marketData.sector ?? '미분류',
    close: item.marketData.close,
    changePct: item.marketData.changePct,
    volumeRatio: item.marketData.volumeRatio20,
    deepDive: item.deepDive,
  });

  return {
    metadata: {
      marketDate: raw.metadata.marketDate,
      generatedAt: raw.metadata.generatedAt,
      dataSource: 'Alpaca 시세 · SEC/기업 IR 및 검증된 뉴스',
      isDemo: raw.sources.length > 0 && raw.sources.every((source) => source.url.includes('example.com')),
    },
    leadStory: raw.leadStory,
    summary: raw.marketPulse,
    marketPulse: raw.marketEtfs.map((item) => ({
      ticker: item.symbol,
      name: marketReferences[item.symbol]?.name ?? item.name,
      tracks: marketReferences[item.symbol]?.tracks ?? item.name,
      role: marketReferences[item.symbol]?.role ?? '시장 흐름을 비교하는 ETF',
      close: item.close,
      changePct: item.changePct,
    })),
    nasdaqRegime: {
      current: regimeLabels[raw.nasdaqRegime.state],
      previous: raw.nasdaqRegime.previousState ? regimeLabels[raw.nasdaqRegime.previousState] : '이전 기록 없음',
      explanation: raw.nasdaqRegime.rationale.join(' '),
    },
    sectorHeatmap: raw.sectorHeatmap.map((item) => ({ ...item, dollarVolume: item.weight })),
    movers: {
      gainers: raw.movers.filter((item) => item.direction === 'gainer').sort((a, b) => a.rank - b.rank).map(toMover),
      losers: raw.movers.filter((item) => item.direction === 'loser').sort((a, b) => a.rank - b.rank).map(toMover),
    },
    deepDives: raw.movers.filter((item) => item.deepDive).map((item) => ({
      symbol: item.symbol,
      headline: item.summary === '확인된 단일 촉매 없음' ? item.summary : `${item.symbol}, 확인된 근거로 움직임 읽기`,
      explanation: item.summary,
      risk: item.risks.join(' '),
      chartReading: item.chartCommentary,
      claimIds: item.claimIds,
      chart: item.marketData.history.map((point) => ({ date: point.date, close: point.close, ma20: point.sma20, ma40: point.sma40 })),
    })),
    themes: raw.themes,
    incomeBasket: raw.incomeBasket.map((item) => ({
      symbol: item.symbol,
      name: item.name,
      kind: item.assetType === 'etf' ? 'ETF' : '주식',
      description: `20일 평균 거래량 대비 ${item.volumeRatio20.toFixed(2)}배 · 20일선 대비 ${formatPct(item.distanceSma20Pct)}`,
      changePct: item.changePct,
    })),
    sources: raw.sources.map((source) => ({ id: source.sourceId, ...source })),
    qa: { publishable: raw.qa.publishable, rounds: raw.qa.revisionCount, reviews: raw.reviews },
    nextWatch: raw.nextWatch,
  };
}

const modules = import.meta.glob<{ default: RawReport }>('../data/reports/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json', { eager: true });

export const reports = Object.values(modules)
  .map((module) => normalizeReport(module.default))
  .filter((report) => report.qa.publishable)
  .sort((a, b) => b.metadata.marketDate.localeCompare(a.metadata.marketDate));

export const latestReport = reports[0];

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
}

export function formatPct(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function reportHref(date: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return `${base}/reports/${date}/`;
}
