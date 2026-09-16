import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [['list']],
  use: { baseURL: 'http://127.0.0.1:4173', headless: true, trace: 'retain-on-failure' },
  webServer: { command: 'npm run dev:lab', url: 'http://127.0.0.1:4173', reuseExistingServer: false, timeout: 30000 },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
