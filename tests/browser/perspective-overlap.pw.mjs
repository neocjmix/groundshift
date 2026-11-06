import { test, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { PNG } from 'pngjs';

const timeout = process.env.GS_BASE_URL ? 60_000 : 10_000;
function visiblePixels(buffer) {
  const png = PNG.sync.read(buffer); let count = 0;
  for (let i = 64 * png.width * 4; i < png.data.length; i += 4) {
    if (Math.max(png.data[i], png.data[i + 1], png.data[i + 2]) > 65) count++;
  }
  return count;
}

test('four actual perspective overlap stages render; evidence, source controls and timeline remain inspectable', async ({ page, browser }, info) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto('/experiments/perspective-overlap/');
  const response = await page.request.get(new URL('summary.json', page.url()).href);
  expect(response.ok()).toBe(true); const summary = await response.json();
  expect(summary.models.map(model => model.id)).toEqual(['best', 'consensus', 'level', 'erp']);
  await expect(page.locator('h1')).toHaveText(summary.heading);
  await expect(page.locator('#quality-status')).toHaveText('공간 일치 NOT ACCEPTED');
  const observations = [];
  for (const model of summary.models) {
    await page.selectOption('#model-select', model.id);
    await expect(page.locator('#cloud-status')).toContainText(model.title, { timeout });
    await expect(page.locator('#capture-4')).toBeEnabled({ timeout });
    await page.locator('#cloud').scrollIntoViewIfNeeded();
    const canvas = page.locator('#cloud canvas');
    await page.click('#overview-view');
    const overview = await canvas.screenshot({ path: info.outputPath(`${model.id}-overview.png`) });
    expect(visiblePixels(overview)).toBeGreaterThan(1_000);
    await page.selectOption('#color-mode', 'source');
    const colors = await canvas.screenshot({ path: info.outputPath(`${model.id}-sources.png`) });
    expect(colors.equals(overview)).toBe(false);
    await page.selectOption('#source-select', '0');
    await expect(page.locator('#cloud-status')).toContainText('4번 출처만');
    const one = await canvas.screenshot(); expect(one.equals(colors)).toBe(false);
    await page.selectOption('#source-select', 'both'); await page.selectOption('#color-mode', 'rgb');
    const captures = [];
    for (const source of ['4', '5']) {
      await page.click(`#capture-${source}`);
      const frame = await canvas.screenshot({ path: info.outputPath(`${model.id}-capture-${source}.png`) });
      expect(visiblePixels(frame)).toBeGreaterThan(1_000); captures.push(frame);
    }
    expect(captures[0].equals(captures[1])).toBe(false);
    for (const direction of model.directions) {
      await page.selectOption('#direction-select', direction.id);
      for (const key of ['source', 'target', 'depth', 'warp', 'residual', 'mask', 'overlap']) {
        if (direction[key]) await expect(page.locator(`#direction-${key}`)).toHaveAttribute('src', direction[key]);
        else await expect(page.locator(`#direction-${key}`)).toBeHidden();
      }
      await expect.poll(() => page.locator('figure:not([hidden]) img').evaluateAll(images =>
        images.every(image => image.complete && image.naturalWidth > 0)), { timeout }).toBe(true);
    }
    observations.push({ id: model.id, coloredPixels: visiblePixels(overview), status: await page.locator('#cloud-status').innerText() });
  }
  await page.selectOption('#model-select', 'best');
  await expect(page.locator('#cloud-status')).toContainText(summary.models[0].title, { timeout });
  await page.locator('#direction-depth').screenshot({ path: info.outputPath('depth.png') });
  await page.locator('#direction-overlap').screenshot({ path: info.outputPath('overlap.png') });
  await page.screenshot({ path: info.outputPath('report.png'), fullPage: true });
  await page.goto('/experiments/lab/');
  await expect(page.locator('.entry[data-id="report-perspective-overlap"]')).toBeVisible();
  const dates = await page.locator('[data-created-at]').evaluateAll(elements => elements.map(element => Date.parse(element.dataset.createdAt)));
  expect(dates.length).toBeGreaterThan(20);
  expect(dates).toEqual([...dates].sort((a,b) => b-a));
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('render-checks.json'), JSON.stringify({
    status: 'PASS', time: new Date().toISOString(), origin: new URL(page.url()).origin,
    browser: browser.version(), headed: process.env.HEADLESS !== '1', observations, errors,
    limitation: 'Actual assets and rendered pixels; geometry accuracy requires separate evidence and remains NOT ACCEPTED.',
  }, null, 2));
});
