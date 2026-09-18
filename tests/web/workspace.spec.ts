import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('real local sign-in, upload, history, cancellation, refresh and logout', async ({ page }) => {
  test.setTimeout(90000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Open your workspace' })).toBeVisible();
  await page.getByLabel('One-time access code').fill(await readFile('.local/web-test-ticket', 'utf8'));
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByLabel('New project').fill('Quarterly sales');
  await page.getByRole('button', { name: 'Create project' }).click();
  await expect(page.getByRole('heading', { name: 'Quarterly sales' })).toBeVisible();
  const fixture = process.env.DTD_TEST_INSPECTION_IMAGE
    ? await readFile('samples/synthetic-sales-messy.csv') : Buffer.from('sales\n42\n');
  await page.locator('#file').setInputFiles({ name: 'sample.csv', mimeType: 'text/csv', buffer: fixture });
  await page.getByRole('button', { name: 'Store dataset' }).click();
  await expect(page.getByText('Awaiting isolated inspection', { exact: false }).first()).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download original' }).click();
  const download = await downloadPromise;
  expect(await download.failure()).toBeNull();
  if (process.env.DTD_TEST_INSPECTION_IMAGE) {
    await page.getByRole('button', { name: 'Inspect dataset' }).click();
    await expect(page.getByText('Inspection: ready', { exact: true })).toBeVisible({ timeout: 60000 });
    await expect(page.getByRole('columnheader', { name: 'order_id' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'ORD-0001', exact: true })).toBeVisible();
    await expect(page.getByText('245 rows · 11 columns', { exact: false })).toBeVisible();
    await page.getByRole('button', { name: 'Use this table' }).click();
    await expect(page.getByRole('button', { name: 'Table saved' })).toBeVisible();
    await page.getByLabel('CSV delimiter').selectOption(';');
    await page.getByRole('button', { name: 'Reinspect with delimiter' }).click();
    await expect(page.getByText('Inspection: ready', { exact: true })).toBeVisible({ timeout: 60000 });
    await expect(page.getByText('245 rows · 1 columns', { exact: false })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Use this table' })).toBeVisible();
    await page.getByLabel('CSV delimiter').selectOption(',');
    await page.getByRole('button', { name: 'Reinspect with delimiter' }).click();
    await expect(page.getByText('245 rows · 11 columns', { exact: false })).toBeVisible({ timeout: 60000 });
    await page.getByRole('button', { name: 'Use this table' }).click();
  }
  await page.getByRole('button', { name: 'Start sample run' }).click();
  await expect(page.getByText('Waiting for the local worker.')).toBeVisible();
  await page.reload();
  await expect(page.getByRole('link', { name: 'Download original' })).toBeVisible();
  if (process.env.DTD_TEST_INSPECTION_IMAGE) await expect(page.getByRole('button', { name: 'Table saved' })).toBeVisible();
  await page.getByRole('button', { name: 'Cancel run' }).click();
  await expect(page.getByText('cancelled', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/workspace-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Quarterly sales' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: 'test-results/workspace-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByRole('heading', { name: 'Open your workspace' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Open your workspace' })).toBeVisible();
  expect(errors).toEqual([]);
});
