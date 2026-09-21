import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import type { components } from '../../packages/contracts/api';
import './style.css';
import { Inspection } from './Inspection';
import { DashboardFallback } from './DashboardFallback';

type Project = components['schemas']['ProjectView'];
type Dataset = components['schemas']['StoredDataset'];
type Run = components['schemas']['RunView'];
type Session = components['schemas']['SessionInfo'];
type Page<T> = { items: T[]; next_cursor: string | null };
const terminal = new Set(['succeeded', 'succeeded_with_warnings', 'failed', 'cancelled']);
const stages = ['profile_fixture', 'summarize_fixture', 'publish_fixture'];
const label = (value: string) => value.replaceAll('_', ' ');

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [checking, setChecking] = useState(true);
  const [ticket, setTicket] = useState('');
  const [projects, setProjects] = useState<Page<Project>>({ items: [], next_cursor: null });
  const [projectId, setProjectId] = useState('');
  const [name, setName] = useState('');
  const [datasets, setDatasets] = useState<Page<Dataset>>({ items: [], next_cursor: null });
  const [runs, setRuns] = useState<Page<Run>>({ items: [], next_cursor: null });
  const [file, setFile] = useState<File | null>(null);
  const [format, setFormat] = useState('csv');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [uploadKey, setUploadKey] = useState(crypto.randomUUID());
  const [dashboardRunId, setDashboardRunId] = useState<string | null>(null);

  async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch('/api/v1' + path, { ...init, credentials: 'same-origin',
      headers: { ...(init.method ? { 'X-CSRF-Token': session?.csrf_token ?? '' } : {}), ...init.headers } });
    if (!response.ok) {
      if (response.status === 401) { setSession(null); setProjects({ items: [], next_cursor: null }); setProjectId(''); }
      const body = await response.json().catch(() => null);
      throw new Error((body?.error?.message ?? 'Request failed. Please retry.') + (body?.error?.request_id ? ` Reference: ${body.error.request_id}` : ''));
    }
    return response.status === 204 ? undefined as T : response.json();
  }
  async function act(work: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await work(); } catch (e) { setError(e instanceof Error ? e.message : 'Connection failed. Please retry.'); }
    finally { setBusy(false); }
  }
  const post = <T,>(path: string, body: object, key = crypto.randomUUID()) => api<T>(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key }, body: JSON.stringify(body),
  });

  useEffect(() => {
    fetch('/api/v1/auth/session', { credentials: 'same-origin' }).then(async response => {
      if (response.ok) setSession(await response.json());
      else if (response.status !== 401) setError('The workspace is unavailable. Check the local API and database, then reload.');
    }).catch(() => setError('Cannot connect to the workspace. Please reload.')).finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    api<Page<Project>>('/projects', { signal: controller.signal }).then(result => {
      setProjects(result); setProjectId(previous => previous || result.items[0]?.id || '');
    }).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
    // Session changes restart the owned project list.
  }, [session]);

  useEffect(() => {
    setDatasets({ items: [], next_cursor: null }); setRuns({ items: [], next_cursor: null });
    setFile(null);
    if (!session || !projectId) return;
    const controller = new AbortController(); setLoading(true);
    Promise.all([
      api<Page<Dataset>>(`/projects/${projectId}/datasets`, { signal: controller.signal }),
      api<Page<Run>>(`/projects/${projectId}/runs`, { signal: controller.signal }),
    ]).then(([files, history]) => { if (!controller.signal.aborted) { setDatasets(files); setRuns(history); } })
      .catch(e => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [projectId, session, refresh]);

  const active = runs.items.filter(run => !terminal.has(run.status)).map(run => run.id).join(',');
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    const timer = setInterval(() => {
      Promise.all(active.split(',').map(id => api<Run>(`/runs/${id}`, { signal: controller.signal })))
        .then(updated => { if (!controller.signal.aborted) setRuns(previous => ({ ...previous, items: previous.items.map(run => updated.find(item => item.id === run.id) ?? run) })); })
        .catch(e => { if (!controller.signal.aborted) setError(e.message); });
    }, 2000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [active]);

  if (checking) return <main className="signin"><p role="status">Opening your workspace…</p></main>;
  return <div className="layout">
    <aside><a className="brand" href="/">d<span>↗</span>d <small>DATA TO DASHBOARD</small></a>
      <div className="workspace-label">YOUR WORKSPACE</div><h2>Make room<br/>for discovery.</h2>
      <p className="aside-copy">Keep your datasets and analysis runs together in one place.</p>
      {session && <><div className="project-list" aria-label="Projects">{projects.items.map(project => <button disabled={busy} className={project.id === projectId ? 'selected' : ''} key={project.id} onClick={() => { setProjectId(project.id); setError(''); }}>{project.name}</button>)}</div>
        {projects.next_cursor && <button className="secondary" disabled={busy} onClick={() => void act(async () => { const next = await api<Page<Project>>(`/projects?cursor=${projects.next_cursor}`); setProjects({ items: [...projects.items, ...next.items], next_cursor: next.next_cursor }); })}>More projects</button>}
        <form onSubmit={e => { e.preventDefault(); void act(async () => { const project = await post<Project>('/projects', { name }); setProjects(previous => ({ ...previous, items: [...previous.items, project] })); setProjectId(project.id); setName(''); }); }}>
          <label htmlFor="project-name">New project</label><input id="project-name" value={name} onChange={e => setName(e.target.value)} maxLength={120} required placeholder="e.g. Quarterly sales"/><button disabled={busy || !name.trim()}>Create project</button></form></>}
      <div className="aside-footer"><span className="dot"/> Local workspace <small>Your files stay in your local database.</small></div>
    </aside>
    <main><header><span>WORKSPACE / {session ? 'OVERVIEW' : 'WELCOME'}</span>{session && <button className="text-button" disabled={busy} onClick={() => void act(async () => { await api('/auth/logout', { method: 'POST' }); setSession(null); setProjectId(''); setTicket(''); })}>Sign out</button>}</header>
      {error && <div className="error" role="alert">{error}<button className="text-button" onClick={() => setError('')}>Dismiss</button></div>}
      {notice && <p className="notice" role="status">{notice}</p>}
      {!session ? <section className="welcome"><p className="eyebrow">YOUR DATA. A CLEARER PICTURE.</p><h1>Start with a dataset.<br/><em>Find what matters.</em></h1><p>Sign in to create a project, store a file, and follow your analysis runs.</p>
        <form className="card login" onSubmit={e => { e.preventDefault(); void act(async () => { const value = ticket; setTicket(''); setSession(await post<Session>('/auth/exchange', { token: value })); }); }}>
          <h2>Open your workspace</h2><label htmlFor="ticket">One-time access code</label><input id="ticket" type="password" autoComplete="off" value={ticket} onChange={e => setTicket(e.target.value)} required minLength={43} maxLength={43}/><p className="muted">Use the five-minute code issued by your local workspace operator.</p><button disabled={busy}>{busy ? 'Signing in…' : 'Continue →'}</button>
        </form></section> : <>
        <section className="heading"><p className="eyebrow">PROJECT OVERVIEW</p><h1>{projects.items.find(project => project.id === projectId)?.name ?? 'Your next discovery'}</h1><p>Bring your data together. Keep track of what happens next.</p></section>
        {!projectId ? <section className="card"><h2>A fresh start</h2><p>Create your first project using the form in the sidebar.</p></section> : <>
          <div className="boundary"><strong>Store and inspect your data. Analysis is coming next.</strong><p>Upload a file, then request an isolated inspection to review its tables and preview rows. Cleaning, modeling, and generated dashboards are not available yet.</p></div>
          <div className="columns"><section className="card"><span className="step">01 / ADD YOUR DATA</span><h2>A place for your raw data</h2><p className="muted">CSV or SQLite · Up to 10 MiB per file · 50 MiB per account</p>
            <form onSubmit={e => { e.preventDefault(); if (!file) return; const selected = file; void act(async () => {
              if (!selected.size || selected.size > 10485760) throw new Error('Choose a file between 1 byte and 10 MiB.');
              await api<Dataset>(`/projects/${projectId}/raw-datasets?file_format=${format}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream', 'Idempotency-Key': uploadKey }, body: selected });
              setUploadKey(crypto.randomUUID()); setRefresh(n => n + 1); setNotice('File stored. Use Inspect dataset below to request a preview.');
            }); }}>
              <label className="filebox" htmlFor="file"><span className="upload-icon">↑</span><strong>{file?.name ?? 'Choose a dataset'}</strong><span>Original bytes are preserved.</span></label><input id="file" type="file" accept=".csv,.sqlite,.sqlite3,.db" disabled={busy} onChange={e => { setFile(e.target.files?.[0] ?? null); setUploadKey(crypto.randomUUID()); }}/>
              <label htmlFor="format">File format</label><select id="format" value={format} disabled={busy} onChange={e => { setFormat(e.target.value); setUploadKey(crypto.randomUUID()); }}><option value="csv">CSV</option><option value="sqlite">SQLite</option></select>
              <button disabled={busy || !file}>{busy ? 'Working…' : 'Store dataset →'}</button>
            </form></section>
            <section className="card demo"><span className="step">02 / EXPLORE THE WORKFLOW</span><h2>Try a sample run</h2><p>See how a run moves through its stages using fixed sales totals. This sample does not use your uploaded files or train a model.</p><div className="sample-mark">3<span>reviewed sample stages</span></div><button className="secondary" disabled={busy || !!active} onClick={() => void act(async () => { await post(`/projects/${projectId}/demo-runs`, {}); setRefresh(n => n + 1); })}>Start sample run</button><p className="muted">Progress updates every two seconds while this page is open.</p></section></div>
          <section className="card listing"><div className="section-title"><h2>Stored datasets</h2><button className="text-button" disabled={busy} onClick={() => setRefresh(n => n + 1)}>Refresh</button></div>
            {loading ? <p role="status">Loading project…</p> : !datasets.items.length ? <p className="empty">No files yet. Your first upload will appear here.</p> : datasets.items.map(dataset => <article className="data-row" key={dataset.id}><div><strong>{dataset.format.toUpperCase()} dataset · {dataset.id.slice(0, 8)}</strong><p>{dataset.size_bytes < 1024 ? `${dataset.size_bytes} bytes` : `${(dataset.size_bytes / 1024).toFixed(1)} KiB`} · {dataset.inspection_status ? 'Inspection ' + dataset.inspection_status : 'Awaiting isolated inspection'}</p><details><summary>Checksum and identifier</summary><code>{dataset.sha256}</code><code>{dataset.id}</code></details><Inspection id={dataset.id} csrf={session.csrf_token} format={dataset.format}/></div><a className="download" href={`/api/v1/datasets/${dataset.id}/raw`}>Download original ↓</a></article>)}
            {datasets.next_cursor && <button className="secondary" disabled={busy} onClick={() => void act(async () => { const next = await api<Page<Dataset>>(`/projects/${projectId}/datasets?cursor=${datasets.next_cursor}`); setDatasets({ items: [...datasets.items, ...next.items], next_cursor: next.next_cursor }); })}>More datasets</button>}
          </section>
          <section className="card listing"><h2>Run history</h2>{!loading && !runs.items.length && <p className="empty">No runs yet. Try the sample workflow above.</p>}
            {runs.items.map(run => <article className="run" key={run.id}><div className="section-title"><strong>{run.mode === 'analysis' ? 'Analysis Run' : 'Sales sample'} · {run.id.slice(0, 8)}</strong><span className="status" role="status">{label(run.status)}</span></div><ol className="stages">{(run.mode === 'analysis' ? ['clean_dataset', 'train_baseline', 'plan_dashboard'] : stages).map(stage => <li key={stage} className={run.completed_stages.includes(stage) ? 'complete' : ''}>{run.completed_stages.includes(stage) ? '✓ ' : '○ '}{label(stage)}</li>)}</ol>{run.status === 'queued' && <p className="muted">Waiting for the local worker.</p>}{!terminal.has(run.status) && <button className="secondary" disabled={busy || run.status === 'cancelling'} onClick={() => void act(async () => { await api(`/runs/${run.id}/cancel`, { method: 'POST' }); setRefresh(n => n + 1); })}>Cancel run</button>}{run.completed_stages.includes('plan_dashboard') && <button className="secondary" style={{ marginLeft: '8px' }} onClick={() => setDashboardRunId(run.id)}>View Dashboard →</button>}{run.result && <p className="result">Result: {run.result.title ? String(run.result.title) : `Sample revenue: ${String(run.result.revenue)} · Sample orders: ${String(run.result.orders)}`}</p>}</article>)}
            {runs.next_cursor && <button className="secondary" disabled={busy} onClick={() => void act(async () => { const next = await api<Page<Run>>(`/projects/${projectId}/runs?cursor=${runs.next_cursor}`); setRuns({ items: [...runs.items, ...next.items], next_cursor: next.next_cursor }); })}>More runs</button>}
          </section>
          {dashboardRunId && <DashboardFallback runId={dashboardRunId} csrf={session.csrf_token} onClose={() => setDashboardRunId(null)} />}
        </>}
      </>}
      <footer>DATA TO DASHBOARD <span>From raw data to understanding.</span></footer>
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<App/>);
