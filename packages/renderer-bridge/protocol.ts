export const PROTOCOL_VERSION = 1 as const;
export const CHANNELS = ['All channels', 'Direct', 'Organic', 'Referral'] as const;
export type Channel = (typeof CHANNELS)[number];

export type FilterValue = {
  operator: 'eq' | 'in' | 'between' | 'gte' | 'lte';
  value: unknown;
};

export type LegacyQueryRequest = {
  version: 1;
  type: 'query';
  nonce: string;
  runId: string;
  requestId: string;
  queryId: 'revenue_by_channel';
  channel: Channel;
};

export type GeneralizedQueryRequest = {
  version: 1;
  type: 'query';
  nonce: string;
  runId: string;
  requestId: string;
  queryId?: string;
  query_id?: string;
  filters?: Record<string, FilterValue>;
  cursor?: number;
  pageSize?: number;
  page_size?: number;
  sortBy?: string;
  sort_by?: string;
  sortDirection?: 'asc' | 'desc';
  sort_direction?: 'asc' | 'desc';
};

export type QueryRequest = LegacyQueryRequest | GeneralizedQueryRequest;

export function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function exactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key));
}

export function isReady(value: unknown, nonce: string): boolean {
  return record(value) && exactKeys(value, ['version', 'type', 'nonce']) &&
    value.version === 1 && value.type === 'ready' && value.nonce === nonce;
}

const ALLOWED_GENERALIZED_KEYS = new Set([
  'version', 'type', 'nonce', 'runId', 'requestId',
  'queryId', 'query_id', 'filters', 'cursor',
  'pageSize', 'page_size', 'sortBy', 'sort_by',
  'sortDirection', 'sort_direction',
]);

export function isQuery(value: unknown, nonce: string, runId: string): value is QueryRequest {
  if (!record(value)) return false;
  if (value.version !== 1 || value.type !== 'query' || value.nonce !== nonce || value.runId !== runId) return false;
  if (typeof value.requestId !== 'string' || !/^[a-zA-Z0-9-]{1,64}$/.test(value.requestId)) return false;

  // Check legacy fixture query
  if (value.queryId === 'revenue_by_channel') {
    return exactKeys(value, ['version', 'type', 'nonce', 'runId', 'requestId', 'queryId', 'channel']) &&
      typeof value.channel === 'string' && CHANNELS.some((channel) => channel === value.channel);
  }

  // Check generalized query
  const keys = Object.keys(value);
  if (!keys.every((key) => ALLOWED_GENERALIZED_KEYS.has(key))) return false;

  const qid = value.query_id ?? value.queryId;
  if (typeof qid !== 'string' || !/^[a-zA-Z0-9_-]{1,64}$/.test(qid)) return false;

  if ('filters' in value && value.filters !== undefined && !record(value.filters)) return false;
  if ('cursor' in value && value.cursor !== undefined && (typeof value.cursor !== 'number' || value.cursor < 0)) return false;
  const pSize = value.page_size ?? value.pageSize;
  if (pSize !== undefined && (typeof pSize !== 'number' || pSize < 1 || pSize > 100)) return false;
  const sDir = value.sort_direction ?? value.sortDirection;
  if (sDir !== undefined && sDir !== 'asc' && sDir !== 'desc') return false;

  return true;
}

export class RequestGate {
  private seen = new Set<string>();
  private active = true;

  constructor(private nonce: string, private runId: string, private limit = 50) { }

  accept(value: unknown): value is QueryRequest {
    if (!this.active || !isQuery(value, this.nonce, this.runId)) return false;
    if (this.seen.has(value.requestId) || this.seen.size >= this.limit) return false;
    this.seen.add(value.requestId);
    return true;
  }

  dispose(): void {
    this.active = false;
    this.seen.clear();
  }
}
