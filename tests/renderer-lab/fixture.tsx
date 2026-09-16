/** Reviewed, fixed synthetic fixture. No model-produced source is built on the host. */
import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { CHANNELS, record, type Channel } from '../../packages/renderer-bridge/protocol';

type Row = { channel: string; revenue: number; orders: number };
const nonce = location.hash.slice(1);
const runId = 'synthetic-run';
let port: MessagePort | undefined;
const callbacks = new Map<string, (rows: Row[]) => void>();
let connected: (() => void) | undefined;

window.addEventListener('message', (event: MessageEvent<unknown>) => {
  if (port || event.source !== window.parent || event.origin !== 'http://127.0.0.1:4173') return;
  if (!record(event.data) || event.data.type !== 'init' || event.data.version !== 1 ||
    event.data.nonce !== nonce || event.data.runId !== runId || event.ports.length !== 1) return;
  port = event.ports[0];
  if (!port) return;
  port.onmessage = (message: MessageEvent<unknown>) => {
    const value = message.data;
    if (!record(value) || value.type !== 'result' || value.version !== 1 || value.nonce !== nonce ||
      value.runId !== runId || typeof value.requestId !== 'string' || !Array.isArray(value.data)) return;
    if (!value.data.every((row) => record(row) && typeof row.channel === 'string' &&
      typeof row.revenue === 'number' && typeof row.orders === 'number')) return;
    callbacks.get(value.requestId)?.(value.data as Row[]);
    callbacks.delete(value.requestId);
  };
  port.start();
  connected?.();
});

function query(channel: Channel, callback: (rows: Row[]) => void) {
  const requestId = crypto.randomUUID();
  callbacks.set(requestId, callback);
  port?.postMessage({ version: 1, type: 'query', nonce, runId, requestId, queryId: 'revenue_by_channel', channel });
}

async function probes(): Promise<string[]> {
  const results: string[] = [];
  for (const [name, attempt] of [
    ['parent DOM', () => window.parent.document.body],
    ['cookies', () => document.cookie],
    ['local storage', () => localStorage.getItem('app-secret')],
    ['runtime eval', () => (0, eval)('1 + 1')],
  ] as const) {
    try { attempt(); results.push(`${name}: FAILED`); }
    catch { results.push(`${name}: blocked`); }
  }
  try {
    await fetch('http://127.0.0.1:4173/probe-egress', { mode: 'no-cors' });
    results.push('network: FAILED');
  } catch { results.push('network: blocked'); }
  return results;
}

function Fixture() {
  const [rows, setRows] = useState<Row[]>([]);
  const [channel, setChannel] = useState<Channel>('All channels');
  const [checks, setChecks] = useState<string[]>([]);
  useEffect(() => {
    connected = () => query('All channels', setRows);
    window.parent.postMessage({ version: 1, type: 'ready', nonce }, 'http://127.0.0.1:4173');
    void probes().then(setChecks);
    return () => { connected = undefined; callbacks.clear(); };
  }, []);

  return <article>
    <div className="heading"><div><span className="eyebrow">SYNTHETIC SALES / FIXED REACT FIXTURE</span>
      <h2>Channel performance</h2></div>
      <label>Channel<select aria-label="Channel" value={channel} onChange={(event) => {
        const next = event.target.value as Channel;
        setChannel(next); query(next, setRows);
      }}>{CHANNELS.map((value) => <option key={value}>{value}</option>)}</select></label></div>
    <div className="metrics"><section><span>Revenue</span><strong data-testid="revenue">${rows.reduce((total, row) => total + row.revenue, 0).toLocaleString('en-US')}</strong></section>
      <section><span>Orders</span><strong>{rows.reduce((total, row) => total + row.orders, 0)}</strong></section>
      <section><span>Data source</span><strong className="small">Synthetic aggregates</strong></section></div>
    <table><caption>Revenue and orders by channel</caption><thead><tr><th>Channel</th><th>Revenue</th><th>Orders</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.channel}><td>{row.channel}</td><td>${row.revenue.toLocaleString('en-US')}</td><td>{row.orders}</td></tr>)}</tbody></table>
    <aside><h3>Isolation probes</h3><ul>{checks.map((check) => <li key={check}>{check}</li>)}</ul></aside>
  </article>;
}

createRoot(document.getElementById('root')!).render(<Fixture />);
