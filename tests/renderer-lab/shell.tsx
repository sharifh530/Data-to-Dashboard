import { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { connectRenderer } from '../../packages/renderer-bridge/host';

const rows = [
  { channel: 'Direct', revenue: 12800, orders: 80 },
  { channel: 'Organic', revenue: 9600, orders: 64 },
  { channel: 'Referral', revenue: 4800, orders: 32 },
];

function Lab() {
  const frame = useRef<HTMLIFrameElement>(null);
  const [instance, setInstance] = useState(() => crypto.randomUUID());
  const [connected, setConnected] = useState(false);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    if (!frame.current || fallback) return;
    return connectRenderer({
      frame: frame.current, nonce: instance, runId: 'synthetic-run',
      onConnected: () => setConnected(true),
      query: ({ channel }) => rows.filter((row) => channel === 'All channels' || row.channel === channel),
    });
  }, [instance, fallback]);

  function reset() {
    setConnected(false);
    setFallback(false);
    setInstance(crypto.randomUUID());
  }

  return <main>
    <header><span className="eyebrow">DATA-TO-DASHBOARD / ENGINEERING LAB</span>
      <h1>One dashboard. A separate boundary.</h1>
      <p>A fixed React fixture receives synthetic aggregates through a scoped message channel.
        This is a security test harness, not the upload application.</p></header>
    <section className="toolbar" aria-label="Renderer controls">
      <span role="status">{fallback ? 'Standard layout active' : connected ? 'Isolated renderer connected' : 'Connecting renderer…'}</span>
      <button onClick={reset}>Reset renderer</button>
      <button onClick={() => setFallback(true)}>Use standard layout</button>
    </section>
    {fallback ? <section className="fallback"><h2>Synthetic sales summary</h2>
      <p>Total revenue: $27,200 across 176 orders.</p>
      <table><caption>Revenue by channel</caption><thead><tr><th>Channel</th><th>Revenue</th><th>Orders</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.channel}><td>{row.channel}</td><td>${row.revenue.toLocaleString('en-US')}</td><td>{row.orders}</td></tr>)}</tbody></table>
    </section> : <iframe key={instance} ref={frame} title="Isolated synthetic dashboard"
      sandbox="allow-scripts" referrerPolicy="no-referrer"
      src={`http://localhost:4174/fixture#${instance}`} />}
    <footer>Synthetic data only · No uploads · No LLM calls · Python execution disabled</footer>
  </main>;
}

createRoot(document.getElementById('root')!).render(<Lab />);
