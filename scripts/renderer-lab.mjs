import './build-renderer.mjs';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const style = await readFile('dist/lab/style.css', 'utf8');
const hash = (content) => `'sha256-${createHash('sha256').update(content).digest('base64')}'`;
const servers = [];
let egressAttempts = 0;
for (const [port, entry, route] of [[4173, 'shell', '/'], [4174, 'fixture', '/fixture']]) {
  const script = await readFile(`dist/lab/${entry}.js`, 'utf8');
  if (/<\/script/i.test(script) || /<\/style/i.test(style)) throw new Error('Unsafe inline asset terminator');
  const child = entry === 'fixture';
  const csp = [
    "default-src 'none'", `script-src ${hash(script)}`, `style-src ${hash(style)}`,
    "connect-src 'none'", "img-src 'none'", "object-src 'none'", "base-uri 'none'", "form-action 'none'",
    child ? "frame-src 'none'" : 'frame-src http://localhost:4174',
    child ? 'frame-ancestors http://127.0.0.1:4173' : "frame-ancestors 'none'",
    ...(child ? ['sandbox allow-scripts'] : []),
  ].join('; ');
  const server = createServer((request, response) => {
    if (!child && request.url === '/probe-egress') {
      egressAttempts += 1;
      response.writeHead(200); response.end('Unexpected egress reached the server'); return;
    }
    if (!child && request.url === '/__lab/egress-count') {
      response.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      response.end(JSON.stringify({ count: egressAttempts })); return;
    }
    if (request.url?.split('?')[0] !== route || request.method !== 'GET') {
      response.writeHead(404, { 'Cache-Control': 'no-store' }); response.end(); return;
    }
    response.writeHead(200, {
      'Content-Type': 'text/html; charset=utf-8', 'Content-Security-Policy': csp,
      'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
      'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
    });
    response.end(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Data-to-Dashboard • Isolation lab</title><style>${style}</style></head><body><div id="root"></div><script>${script}</script></body></html>`);
  });
  server.on('error', (error) => { console.error(error.message); servers.forEach((item) => item.close()); process.exit(1); });
  server.listen(port, '127.0.0.1', () => console.log(`${entry}: http://${child ? 'localhost' : '127.0.0.1'}:${port}${route}`));
  servers.push(server);
}
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => {
  servers.forEach((server) => { server.closeAllConnections(); server.close(); });
});
