import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve, delimiter } from 'node:path';

export const python = resolve(process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
export const pythonEnv = {
  ...process.env,
  PYTHONPATH: [resolve('services/api/src'), resolve('services/execution-broker/src'), resolve('services/worker/src')].join(delimiter),
};

if (!existsSync(python)) {
  console.error('Missing .venv. Run uv sync --locked first. See docs/GETTING_STARTED.md.');
  process.exit(1);
}
const child = spawn(python, process.argv.slice(2), { stdio: 'inherit', env: pythonEnv });
child.on('error', (error) => { console.error(error.message); process.exitCode = 1; });
child.on('exit', (code) => { process.exitCode = code ?? 1; });
