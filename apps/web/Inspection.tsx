import { useEffect, useState } from 'react';
import type { components } from '../../packages/contracts/api';

type Result = components['schemas']['InspectionView'];

export function Inspection({ id, csrf, format }: { id: string; csrf: string; format: string }) {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState('');
  const [delimiter, setDelimiter] = useState('');
  const pending = result?.status === 'queued' || result?.status === 'running';
  useEffect(() => {
    const controller = new AbortController();
    async function refresh() {
      try {
        const response = await fetch(`/api/v1/datasets/${id}/inspection`, { signal: controller.signal });
        if (response.status === 404) return;
        if (!response.ok) throw new Error('Cannot load inspection. Check your session and refresh.');
        const value = await response.json();
        if (!controller.signal.aborted) {
          setResult(value);
          setSelected(value.selected_table ?? value.report?.tables[0]?.name ?? '');
          setDelimiter(value.delimiter_override ?? '');
        }
      } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Connection failed.'); }
    }
    void refresh();
    const timer = pending ? setInterval(() => void refresh(), 2000) : undefined;
    return () => { controller.abort(); if (timer) clearInterval(timer); };
  }, [id, pending]);
  async function start() {
    setBusy(true); setError('');
    try {
      const response = await fetch(`/api/v1/datasets/${id}/inspection`, { method: 'POST', headers: { 'X-CSRF-Token': csrf, 'Content-Type': 'application/json' }, body: JSON.stringify({ delimiter: delimiter || null }) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message ?? 'Inspection unavailable.');
      setResult(body);
      if (body.status === 'queued') setSelected('');
    } catch (e) { setError(e instanceof Error ? e.message : 'Connection failed.'); }
    finally { setBusy(false); }
  }
  async function saveSelection() {
    setBusy(true); setError('');
    try {
      const response = await fetch(`/api/v1/datasets/${id}/inspection/selection`, { method: 'POST', headers: { 'X-CSRF-Token': csrf, 'Content-Type': 'application/json' }, body: JSON.stringify({ table: selected }) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message ?? 'Cannot save table choice.');
      setResult(body);
    } catch (e) { setError(e instanceof Error ? e.message : 'Connection failed.'); }
    finally { setBusy(false); }
  }
  const report = result?.report;
  const table = report?.tables.find(value => value.name === selected);
  return <section className="inspection" aria-label="Dataset inspection">
    {format === 'csv' && <><label htmlFor={`delimiter-${id}`}>CSV delimiter</label><select id={`delimiter-${id}`} value={delimiter} disabled={busy || pending} onChange={e => setDelimiter(e.target.value)}><option value="">Detect automatically</option><option value=",">Comma</option><option value=";">Semicolon</option><option value={'\t'}>Tab</option><option value="|">Pipe</option></select></>}
    {(!result || (!pending && format === 'csv' && delimiter !== (result.delimiter_override ?? ''))) && <button className="secondary" disabled={busy} onClick={() => void start()}>{busy ? 'Requesting…' : result ? 'Reinspect with delimiter' : 'Inspect dataset'}</button>}
    {error && <p role="alert">{error}</p>}
    {result && <p role="status">Inspection: {result.status}{result.error ? ` — ${result.error.replaceAll('_', ' ').toLowerCase()}` : ''}</p>}
    {pending && <p className="muted">Waiting for or running the isolated inspector. This does not clean your data or train a model.</p>}
    {report?.status === 'ready' && <>
      <label htmlFor={`table-${id}`}>Analysis table</label><select id={`table-${id}`} value={selected} onChange={e => setSelected(e.target.value)}>{report.tables.map((value, index) => <option key={index} value={value.name}>{value.name}</option>)}</select>
      <button className="secondary" disabled={busy || !selected || selected === result?.selected_table} onClick={() => void saveSelection()}>{result?.selected_table === selected ? 'Table saved' : 'Use this table'}</button>
      {table && <><p>{table.row_count.toLocaleString()} rows · {table.columns.length} columns · {table.missing.reduce((a, b) => a + b, 0)} empty values</p>
        <div className="preview-scroll" tabIndex={0} role="region" aria-label="Dataset preview"><table><thead><tr>{table.columns.map((name, index) => <th key={index} scope="col">{name || '(unnamed)'}</th>)}</tr></thead><tbody>{table.preview.map((row, index) => <tr key={index}>{row.map((value, column) => <td key={column}>{value === null ? 'NULL' : value === '' ? '(empty)' : value}</td>)}</tr>)}</tbody></table></div>
        <p className="muted">First {table.preview.length} rows; preview cells limited to 128 characters. Original bytes are unchanged. The saved table choice will be used by a future analysis workflow.</p>
      </>}
      {report.warnings.map(warning => <p className="muted" key={warning}>{warning.replaceAll('_', ' ').toLowerCase()}</p>)}
    </>}
  </section>;
}
