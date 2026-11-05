import { test, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { PNG } from 'pngjs';

const reportPath = '/experiments/panoramic-pair/';
const ready = (page, title) => Promise.all([
  expect(page.locator('#cloud-status')).toContainText(title),
  expect(page.locator('#cloud-status')).toContainText('개 표시 점'),
  expect(page.locator('#capture-4')).toBeEnabled(),
]);
async function openReport(page) {
  await page.goto(reportPath);
  const response = await page.request.get(new URL('summary.json', page.url()).href);
  expect(response.ok(), 'Restore the selected observation release assets before this test').toBe(true);
  const summary = await response.json();
  expect(summary.models.map(model => model.id)).toEqual(['da2', 'dav2']);
  await expect(page.locator('#model-select')).toBeEnabled();
  return summary;
}
function coloredPixels(buffer) {
  const png = PNG.sync.read(buffer);
  let count = 0;
  // Canvas only: status text and controls cannot satisfy this rendering check.
  for (let i = 0; i < png.data.length; i += 4) {
    if (Math.max(png.data[i], png.data[i + 1], png.data[i + 2]) > 65) count++;
  }
  return count;
}

test('adjacent real panorama clouds render with source, camera and directional diagnostic controls', async ({ page, browser }, info) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const summary = await openReport(page);
  const observations = [];
  await expect(page.locator('#sources img')).toHaveCount(2);
  for (const model of summary.models) {
    expect(model.cloud, 'This executed experiment must retain both exported point clouds').toBeTruthy();
    await page.selectOption('#model-select', model.id);
    await ready(page, model.title);
    await expect(page.locator('#model-status')).toContainText(`실행 ${model.status}`);
    await expect(page.locator('#model-status')).toContainText(`공간 일치 ${model.qualityStatus}`);
    await page.locator('#cloud').scrollIntoViewIfNeeded();
    await page.click('#overview-view');
    await page.selectOption('#source-select', 'both');
    await page.selectOption('#color-mode', 'rgb');
    await page.waitForTimeout(150);
    const canvas = page.locator('#cloud canvas');
    await expect(canvas).toHaveCount(1);
    const rgb = await canvas.screenshot({ path: info.outputPath(`${model.id}-overview-rgb.png`) });
    const pixelCount = coloredPixels(rgb);
    expect(pixelCount).toBeGreaterThan(1_000);
    await page.selectOption('#color-mode', 'source');
    const sourceColors = await canvas.screenshot({ path: info.outputPath(`${model.id}-overview-sources.png`) });
    expect(sourceColors.equals(rgb), 'Source colors must change actual rendered pixels').toBe(false);
    for (const source of ['0', '1']) {
      await page.selectOption('#source-select', source);
      await expect(page.locator('#cloud-status')).toContainText(`${Number(source) + 4}번 출처만`);
      const subset = await canvas.screenshot({ path: info.outputPath(`${model.id}-source-${Number(source) + 4}.png`) });
      expect(subset.equals(sourceColors), 'Selecting one source must change actual rendered pixels').toBe(false);
      expect(coloredPixels(subset)).toBeGreaterThan(1_000);
    }
    await page.selectOption('#source-select', 'both');
    await page.selectOption('#color-mode', 'rgb');
    const captures = [];
    for (const source of ['4', '5']) {
      await page.click(`#capture-${source}`);
      await page.waitForTimeout(150);
      captures.push(await canvas.screenshot({ path: info.outputPath(`${model.id}-capture-${source}-rgb.png`) }));
    }
    expect(captures[0].equals(captures[1]), 'The two estimated camera views must differ').toBe(false);
    await page.click('#overview-view');
    await page.locator('#point-size').fill('5');
    await page.locator('#point-size').dispatchEvent('input');
    await page.click('#reset');
    for (const direction of model.directions) {
      await page.selectOption('#direction-select', direction.id);
      for (const key of ['source', 'target', 'depth', 'warp', 'residual', 'mask']) {
        await expect(page.locator(`#direction-${key}`)).toHaveAttribute('src', direction[key]);
      }
      await expect.poll(() => page.locator('figure:not([hidden]) img').evaluateAll(images =>
        images.length === 8 && images.every(image => image.complete && image.naturalWidth > 0))).toBe(true);
      await page.locator('#direction-warp').screenshot({ path: info.outputPath(`${model.id}-${direction.id}-warp.png`) });
    }
    observations.push({ model: model.id, status: 'PASS', coloredPixels: pixelCount,
      cloud: await page.locator('#cloud-status').innerText(), metrics: await page.locator('#metrics').innerText() });
  }
  await page.screenshot({ path: info.outputPath('pair-report.png'), fullPage: true });
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('pair-render-checks.json'), JSON.stringify({
    time: new Date().toISOString(), browser: browser.version(), origin: new URL(page.url()).origin,
    mode: process.env.HEADLESS === '1' ? 'headless' : 'headed', status: 'PASS', observations, errors,
    evidenceLimit: 'Existing real assets rendered; inference and reconstruction were not rerun. Pixel checks do not establish geometric quality. Screenshots need separate visual inspection.',
  }, null, 2));
});

test('late real cloud response cannot replace selection; a simulated HTTP failure recovers', async ({ page }, info) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const summary = await openReport(page);
  const [first, second] = summary.models;
  await page.selectOption('#model-select', second.id);
  await ready(page, second.title);
  const firstUrl = new URL(first.cloud, page.url()).href;
  let release;
  let started;
  const delayed = new Promise(resolve => { release = resolve; });
  const requestStarted = new Promise(resolve => { started = resolve; });
  await page.route(firstUrl, async route => {
    started();
    const response = await route.fetch();
    await delayed;
    await route.fulfill({ response });
  });
  try {
    await page.selectOption('#model-select', first.id);
    await requestStarted;
    await page.selectOption('#model-select', second.id);
    await ready(page, second.title);
    const delayedResponse = page.waitForResponse(firstUrl);
    release();
    await delayedResponse;
    await page.waitForTimeout(500);
    await expect(page.locator('#model-select')).toHaveValue(second.id);
    await ready(page, second.title);
    await expect(page.locator('#cloud canvas')).toHaveCount(1);
  } finally {
    release();
    await page.unroute(firstUrl);
  }
  await page.route(firstUrl, route => route.fulfill({ status: 503, body: 'Deliberate UI error-state test' }));
  await page.selectOption('#model-select', first.id);
  await expect(page.locator('#cloud-status')).toContainText('점군 불러오기 실패');
  await expect(page.locator('#capture-4')).toBeDisabled();
  await expect(page.locator('#color-mode')).toBeDisabled();
  await page.locator('#cloud').screenshot({ path: info.outputPath('simulated-http-failure.png') });
  await page.unroute(firstUrl);
  await page.selectOption('#model-select', second.id);
  await ready(page, second.title);
  await page.selectOption('#model-select', first.id);
  await ready(page, first.title);
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('pair-async-checks.json'), JSON.stringify({
    status: 'PASS', staleResponse: 'PASS', simulatedHttp503Recovery: 'PASS', errors,
    evidenceLimit: 'Injected network timing/failure tests validate UI recovery only; they are not failed reconstruction runs.',
  }, null, 2));
});

test('pair remains discoverable in both lab orders and the preserved one-panorama report renders', async ({ page }, info) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/experiments/lab/');
  const card = page.locator('.entry[data-id="report-panoramic-pair"]');
  await expect(card).toBeVisible();
  for (const order of ['newest', 'oldest']) {
    await page.selectOption('#order', order);
    const dates = await page.locator('.entry[data-created-at]').evaluateAll(entries => entries.map(entry => Date.parse(entry.dataset.createdAt)));
    expect(dates.length).toBeGreaterThan(2);
    expect(dates.every(Number.isFinite)).toBe(true);
    expect(dates.every((date, index) => index === 0 || (order === 'newest' ? date <= dates[index - 1] : date >= dates[index - 1]))).toBe(true);
    await expect(card.locator('h2 a')).toHaveAttribute('href', reportPath);
  }
  await card.locator('h2 a').click();
  await expect(page).toHaveURL(/\/experiments\/panoramic-pair\/$/);
  await page.getByRole('link', { name: '앞선 한 파노라마 실험 ↗' }).click();
  await expect(page).toHaveURL(/\/experiments\/panoramic-depth\/$/);
  await expect(page.locator('#cloud-status')).toContainText('개 표시 점');
  await page.locator('#cloud').scrollIntoViewIfNeeded();
  const screenshot = await page.locator('#cloud canvas').screenshot({ path: info.outputPath('preserved-one-panorama.png') });
  expect(coloredPixels(screenshot)).toBeGreaterThan(1_000);
  await expect.poll(() => page.locator('#source, #depth, #range, #mask').evaluateAll(images =>
    images.length === 4 && images.every(image => image.complete && image.naturalWidth > 0))).toBe(true);
  expect(errors).toEqual([]);
});
