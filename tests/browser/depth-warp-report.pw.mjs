import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';

const summary = JSON.parse(await readFile('public/experiments/depth-warp/summary.json', 'utf8'));

test('depth-guided report displays observed, generated and actual GS render evidence', async ({ page, browser }, info) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('link', { name: 'Depth-guided scene experiment' }).click();
  await expect(page).toHaveURL(/\/experiments\/depth-warp\/$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('깊이를 이용해 중간 장면 만들기');
  await expect(page.locator('.status')).toContainText('3D 품질 개선 FAIL');
  expect(summary.sourcePhotos.map(photo => photo.imageId)).toHaveLength(3);
  expect(summary.coverage.sourceConsistentDepthWarpFraction).toBeGreaterThan(0);
  expect(summary.gaussian.matchedRenders).toHaveLength(2);
  const images = page.locator('figure img');
  await expect(images).toHaveCount(summary.images.length);
  for (let index = 0; index < summary.images.length; index++) {
    await images.nth(index).scrollIntoViewIfNeeded();
    await expect.poll(() => images.nth(index).evaluate(image => image.complete && image.naturalWidth === 512 && image.naturalHeight === 512),
      { timeout: process.env.GS_BASE_URL ? 30_000 : 5_000 }).toBe(true);
  }
  await page.screenshot({ path: info.outputPath('depth-warp-report.png'), fullPage: true });
  await page.getByRole('link', { name: '실제 48장 + 생성 1장 GS' }).click();
  await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase', 'ready', {
    timeout: process.env.GS_BASE_URL ? 90_000 : 30_000,
  });
  await expect(page.locator('canvas')).toHaveCount(1);
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('depth-warp-checks.json'), JSON.stringify({
    browser: browser.version(), origin: new URL(page.url()).origin,
    images: summary.images.length, scene: 'beijing-depth', errors,
    checks: ['all 512px report images decoded', 'GS scene opened and canvas reached ready phase'],
  }, null, 2));
});
