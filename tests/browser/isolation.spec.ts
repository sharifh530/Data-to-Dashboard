import { expect, test } from '@playwright/test';

test('fixed React fixture filters synthetic data across an opaque-origin bridge', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText('Isolated renderer connected');
  const frame = page.frameLocator('iframe');
  await expect(frame.getByTestId('revenue')).toHaveText('$27,200');
  await frame.getByLabel('Channel', { exact: true }).selectOption('Direct');
  await expect(frame.getByTestId('revenue')).toHaveText('$12,800');
  await page.getByRole('button', { name: 'Reset renderer' }).click();
  await expect(frame.getByTestId('revenue')).toHaveText('$27,200');
});

test('browser blocks parent, storage, eval, and network access', async ({ page, request }) => {
  const response = await page.goto('/');
  expect(response?.headers()['content-security-policy']).toContain("connect-src 'none'");
  await expect(page.locator('iframe')).toHaveAttribute('sandbox', 'allow-scripts');
  const frame = page.frameLocator('iframe');
  for (const probe of ['parent DOM', 'cookies', 'local storage', 'runtime eval', 'network']) {
    await expect(frame.getByText(`${probe}: blocked`, { exact: true })).toBeVisible();
  }
  await expect(frame.getByText(/FAILED/)).toHaveCount(0);
  // Independently verify denial at the server, not only the fixture's reported fetch error.
  const counter = await request.get('/__lab/egress-count');
  expect((await counter.json()).count).toBe(0);
});

test('renderer response enforces sandbox even outside the parent embed', async ({ request }) => {
  const result = await request.get('http://localhost:4174/fixture');
  expect(result.status()).toBe(200);
  const policy = result.headers()['content-security-policy'];
  expect(policy).toContain('sandbox allow-scripts');
  expect(policy).toContain("script-src 'sha256-");
  expect(policy).not.toContain('unsafe-inline');
  expect(policy).not.toContain('unsafe-eval');
  expect(result.headers()['set-cookie']).toBeUndefined();
});

test('trusted parent can replace the renderer with a standard layout', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText('Isolated renderer connected');
  await page.getByRole('button', { name: 'Use standard layout' }).click();
  await expect(page.locator('iframe')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Synthetic sales summary' })).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Standard layout active');
  await page.getByRole('button', { name: 'Reset renderer' }).click();
  await expect(page.frameLocator('iframe').getByTestId('revenue')).toHaveText('$27,200');
});

test('forged window messages cannot impersonate the opaque frame', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText('Isolated renderer connected');
  await page.evaluate(() => {
    window.postMessage({ version: 1, type: 'ready', nonce: 'forged' }, '*');
    window.postMessage({ version: 1, type: 'query', runId: 'other-run', queryId: 'execute_sql' }, '*');
  });
  await expect(page.frameLocator('iframe').getByTestId('revenue')).toHaveText('$27,200');
});
