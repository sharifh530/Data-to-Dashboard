import { useEffect, useState } from 'react';
import type { components } from '../../packages/contracts/api';

type Result = components['schemas']['InspectionView'];

export function Inspection({ id, csrf }: { id: string; csrf: string }) {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState(0);
  const pending = result?.status === 'queued' || result?.status === 'running';
  useEffect(() => {
    const controller = new AbortController();
    async function refresh() {
      try {
        const response = await fetch(`/api/v1/datasets/${id}/inspection`, { signal: controller.signal });
        if (response.status === 404) return;
        if (!response.ok) throw new Error('Cannot load inspection. Check your session and refresh.');
        const value = await response.json();
        if (!controller.signal.aborted) setResult(value);
      } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Connection failed.'); }
    }
    void refresh();
    const timer = pending ? setInterval(() => void refresh(), 2000) : undefined;
    return () => { controller.abort(); if (timer) clearInterval(timer); };
  }, [id, pending]);
  async function start() {
    setBusy(true); setError('');
    try {
      const response = await fetch(`/api/v1/datasets/${id}/inspection`, { method: 'POST', headers: { 'X-CSRF-Token': csrf } });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message ?? 'Inspection unavailable.');
      setResult(body);
    } catch (e) { setError(e instanceof Error ? e.message : 'Connection failed.'); }
    finally { setBusy(false); }
  }
  const report = result?.report;
  const table = report?.tables[selected];
  return <section className="inspection" aria-label="Dataset inspection">
    {!result && <button className="secondary" disabled={busy} onClick={() => void start()}>{busy ? 'Requesting…' : 'Inspect dataset'}</button>}
    {error && <p role="alert">{error}</p>}
    {result && <p role="status">Inspection: {result.status}{result.error ? ` — ${result.error.replaceAll('_', ' ').toLowerCase()}` : ''}</p>}
    {pending && <p className="muted">Waiting for or running the isolated inspector. This does not clean your data or train a model.</p>}
    {report?.status === 'ready' && <>
      <label htmlFor={`table-${id}`}>Preview table</label><select id={`table-${id}`} value={selected} onChange={e => setSelected(Number(e.target.value))}>{report.tables.map((value, index) => <option key={index} value={index}>{value.name}</option>)}</select>
      {table && <><p>{table.row_count.toLocaleString()} rows · {table.columns.length} columns · {table.missing.reduce((a, b) => a + b, 0)} empty values</p>
        <div className="preview-scroll" tabIndex={0} role="region" aria-label="Dataset preview"><table><thead><tr>{table.columns.map((name, index) => <th key={index} scope="col">{name || '(unnamed)'}</th>)}</tr></thead><tbody>{table.preview.map((row, index) => <tr key={index}>{row.map((value, column) => <td key={column}>{value === null ? 'NULL' : value === '' ? '(empty)' : value}</td>)}</tr>)}</tbody></table></div>
        <p className="muted">First {table.preview.length} rows; preview cells limited to 128 characters. Original bytes are unchanged. Choosing a preview table does not start analysis.</p>
      </>}
      {report.warnings.map(warning => <p className="muted" key={warning}>{warning.replaceAll('_', ' ').toLowerCase()}</p>)}
    </>}
  </section>;
}
