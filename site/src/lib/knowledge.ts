import rawCatalog from '../data/knowledge/catalog.json';

export interface KnowledgeOccurrence {
  marketDate: string;
  direction?: 'gainer' | 'loser';
  rank?: number;
  changePct?: number;
  deepDive?: boolean;
  summary: string;
  claimIds?: string[];
  symbols?: string[];
  reportRoute: string;
}

export interface KnowledgeConcept {
  id: string;
  type: 'Daily Market Report' | 'Security' | 'Market Theme' | 'Fund' | 'Financial Concept' | 'Attested Computation';
  title: string;
  description: string;
  path: string;
  route: string;
  tags: string[];
  status: 'draft' | 'stable' | 'deprecated';
  trust: 'unverified' | 'machine-confirmed' | 'human-reviewed';
  updatedAt: string;
  marketDate?: string;
  symbol?: string;
  sector?: string;
  themeId?: string;
  symbols?: string[];
  occurrences?: KnowledgeOccurrence[];
  latestObservation?: { marketDate: string; close: number; changePct: number };
}

export interface KnowledgeCatalog {
  okfVersion: string;
  generatedAt: string;
  latestMarketDate: string;
  concepts: KnowledgeConcept[];
}

export const knowledgeCatalog = rawCatalog as KnowledgeCatalog;
export const knowledgeConcepts = knowledgeCatalog.concepts;

export const securityConcepts = knowledgeConcepts
  .filter((concept) => concept.type === 'Security')
  .sort((a, b) => (a.symbol ?? '').localeCompare(b.symbol ?? ''));

export const themeConcepts = knowledgeConcepts
  .filter((concept) => concept.type === 'Market Theme')
  .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));

export const referenceConcepts = knowledgeConcepts
  .filter((concept) => ['Fund', 'Financial Concept', 'Attested Computation'].includes(concept.type))
  .sort((a, b) => a.title.localeCompare(b.title, 'ko'));

export function withBase(route: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return `${base}${route.startsWith('/') ? route : `/${route}`}`;
}

export function conceptHref(concept: KnowledgeConcept): string {
  return withBase(concept.route);
}

export function okfSourceHref(concept: KnowledgeConcept): string {
  return withBase(`/data/knowledge/${concept.path}`);
}

export function trustLabel(trust: KnowledgeConcept['trust']): string {
  if (trust === 'human-reviewed') return '사람 검토 완료';
  if (trust === 'machine-confirmed') return '자동 검증 완료';
  return '미검증';
}
