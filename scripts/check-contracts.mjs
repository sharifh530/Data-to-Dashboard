import { spawnSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import openapiTS, { astToString } from 'openapi-typescript';

const checked = spawnSync(process.execPath, ['scripts/python.mjs', 'scripts/export-contracts.py', '--check'], { stdio: 'inherit' });
if (checked.status !== 0) process.exit(checked.status ?? 1);
const expected = astToString(await openapiTS(new URL('../packages/contracts/openapi.json', import.meta.url)));
const existing = await readFile('packages/contracts/api.d.ts', 'utf8');
// The CLI prepends a generated-file comment; compare the declaration content.
if (existing.slice(existing.indexOf('export interface')) !== expected.slice(expected.indexOf('export interface'))) {
  console.error('TypeScript contract drift. Run npm run contracts:generate.');
  process.exit(1);
}
console.log('TypeScript contracts checked.');
