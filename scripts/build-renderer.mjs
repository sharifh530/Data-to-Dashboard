import { build } from 'esbuild';
import { mkdir, copyFile } from 'node:fs/promises';

// Only reviewed fixtures are compiled here. Generated source requires the future offline sandbox.
await mkdir('dist/lab', { recursive: true });
await build({
  entryPoints: { shell: 'tests/renderer-lab/shell.tsx', fixture: 'tests/renderer-lab/fixture.tsx' },
  outdir: 'dist/lab', bundle: true, minify: true, format: 'iife', platform: 'browser', target: 'es2022',
  define: { 'process.env.NODE_ENV': '"production"' }, legalComments: 'none',
});
await copyFile('tests/renderer-lab/style.css', 'dist/lab/style.css');
console.log('Reviewed React lab fixtures built. No generated code was compiled.');
