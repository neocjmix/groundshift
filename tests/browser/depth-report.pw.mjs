import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';

const summary = JSON.parse(await readFile('public/experiments/depth-v2/summary.json', 'utf8'));

test('public depth diagnostic shows three observed crops and three MPS predictions', async ({ page, browser }, info) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('link', { name: 'Inspect photo depth maps' }).click();
  await expect(page).toHaveURL(/\/experiments\/depth-v2\/$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('사진에서 깊이를 추정해 봤다');
  await expect(page.locator('.status')).toContainText('GS 개선 NOT RUN');
  const images = page.locator('figure img');
  await expect(images).toHaveCount(6);
  for (let index = 0; index < 6; index++) {
    await images.nth(index).scrollIntoViewIfNeeded();
    await expect.poll(() => images.nth(index).evaluate(image => image.complete && image.naturalWidth === 512 && image.naturalHeight === 512),
      { timeout: process.env.GS_BASE_URL ? 30_000 : 5_000 }).toBe(true);
  }
  await expect(page.getByRole('link', { name: '원본 사진/저작자' })).toHaveCount(3);
  expect(summary.images).toHaveLength(3);
  expect(summary.images.map(image => image.sparseObservations)).toEqual([317, 312, 281]);
  expect(summary.status).toContain('GS improvement NOT RUN');
  expect(errors).toEqual([]);
  await page.screenshot({ path: info.outputPath('depth-report.png'), fullPage: true });
  await writeFile(info.outputPath('depth-checks.json'), JSON.stringify({
    browser: browser.version(), origin: new URL(page.url()).origin, images: 6,
    status: summary.status, errors,
    limit: 'Displayed depth maps and saved MPS measurements do not establish metric geometry or GS improvement.',
  }, null, 2));
});
