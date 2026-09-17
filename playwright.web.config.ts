import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/web', workers: 1, retries: 0, forbidOnly: Boolean(process.env.CI),
  use: { baseURL: 'http://127.0.0.1:4180', headless: true, trace: 'off' },
  webServer: { command: 'npm run build:web && node scripts/python.mjs scripts/web-test-server.py',
    url: 'http://127.0.0.1:4180', reuseExistingServer: false, timeout: 30000 },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
