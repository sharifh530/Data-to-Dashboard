import { useEffect, useState } from 'react';
import type { components } from '../../packages/contracts/api';

type Result = components['schemas']['ProfileView'];

export function Profile({ versionId, csrf }: { versionId: string; csrf: string }) {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const pending = result?.status === 'queued' || result?.status === 'running';
  useEffect(() => {
    const controller = new AbortController();
    async function refresh() {
      try {
        const response = await fetch(`/api/v1/dataset-versions/${versionId}/profile`, { signal: controller.signal });
        if (response.status === 404) return;
        if (!response.ok) throw new Error('Cannot load profile.');
        const value = await response.json();
        if (!controller.signal.aborted) setResult(value);
      } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Connection failed.'); }
    }
    void refresh();
    const timer = pending ? setInterval(() => void refresh(), 2000) : undefined;
    return () => { controller.abort(); if (timer) clearInterval(timer); };
  }, [versionId, pending]);
  async function start() {
    setBusy(true); setError('');
    try {
      const response = await fetch(`/api/v1/dataset-versions/${versionId}/profile`, { method: 'POST', headers: { 'X-CSRF-Token': csrf } });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message ?? 'Cannot request profile.');
      setResult(body);
    } catch (e) { setError(e instanceof Error ? e.message : 'Connection failed.'); }
    finally { setBusy(false); }
  }
  const table = result?.report?.tables[0];
  return <section className="profile" aria-label="Dataset profile">
    {!result && <button className="secondary" disabled={busy} onClick={() => void start()}>{busy ? 'Requesting…' : 'Profile selected table'}</button>}
    {error && <p role="alert">{error}</p>}
    {result && <p role="status">Profile: {result.status}{result.error ? ` — ${result.error.replaceAll('_', ' ').toLowerCase()}` : ''}</p>}
    {pending && <p className="muted">Counting values in the isolated sandbox.</p>}
    {table && <><p>{table.row_count.toLocaleString()} rows profiled · {table.profile.length} columns</p>
      <div className="preview-scroll" tabIndex={0} role="region" aria-label="Profile statistics"><table><thead><tr><th scope="col">Column</th><th scope="col">Missing</th><th scope="col">Distinct</th><th scope="col">Numeric</th><th scope="col">Other</th><th scope="col">Numeric range</th><th scope="col">Most frequent values</th></tr></thead><tbody>{table.profile.map((column, index) => <tr key={index}><th scope="row">{column.name || '(unnamed)'}</th><td>{table.missing[index]}</td><td>{column.distinct}</td><td>{column.numeric_count}</td><td>{column.nonnumeric_count}</td><td>{column.numeric_min === null ? '—' : `${column.numeric_min} to ${column.numeric_max}`}</td><td>{column.top_values.map(value => `${value.value} (${value.count})`).join(', ') || '—'}</td></tr>)}</tbody></table></div>
      <p className="muted">Numeric means values that parse as finite numbers; identifiers may also look numeric. Counts do not change the original data. Profile fingerprint: {result?.report_sha256}</p>
    </>}
  </section>;
}
