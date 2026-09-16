import { spawnSync } from 'node:child_process';
for (const args of [['ruff', 'check', '.'], ['ruff', 'format', '--check', '.'], ['mypy']]) {
  const result = spawnSync(process.execPath, ['scripts/python.mjs', '-m', ...args], { stdio: 'inherit' });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
