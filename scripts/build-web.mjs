import { build } from 'esbuild';
import { mkdir, writeFile } from 'node:fs/promises';
await mkdir('dist/web', { recursive: true });
await build({ entryPoints: ['apps/web/main.tsx'], outdir: 'dist/web', bundle: true, minify: true,
  platform: 'browser', format: 'esm', target: 'es2022', legalComments: 'none',
  define: { 'process.env.NODE_ENV': '"production"' } });
await writeFile('dist/web/index.html', '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Data to Dashboard · Workspace</title><link rel="stylesheet" href="/assets/main.css"></head><body><div id="root"></div><script type="module" src="/assets/main.js"></script></body></html>');
console.log('Reviewed workspace UI built.');
