export const PROTOCOL_VERSION = 1 as const;
export const CHANNELS = ['All channels', 'Direct', 'Organic', 'Referral'] as const;
export type Channel = (typeof CHANNELS)[number];

export type QueryRequest = {
  version: 1;
  type: 'query';
  nonce: string;
  runId: string;
  requestId: string;
  queryId: 'revenue_by_channel';
  channel: Channel;
};

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

export function isQuery(value: unknown, nonce: string, runId: string): value is QueryRequest {
  return record(value) &&
    exactKeys(value, ['version', 'type', 'nonce', 'runId', 'requestId', 'queryId', 'channel']) &&
    value.version === 1 && value.type === 'query' && value.nonce === nonce && value.runId === runId &&
    typeof value.requestId === 'string' && /^[a-zA-Z0-9-]{1,64}$/.test(value.requestId) &&
    value.queryId === 'revenue_by_channel' && CHANNELS.some((channel) => channel === value.channel);
}

export class RequestGate {
  private seen = new Set<string>();
  private active = true;

  constructor(private nonce: string, private runId: string, private limit = 30) {}

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
