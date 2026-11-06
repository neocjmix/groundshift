import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import { PNG } from 'pngjs';

const summary = JSON.parse(await readFile('public/experiments/street/summary.json', 'utf8'));
const modelUrl = model => `/?world=${encodeURIComponent(model.world)}`;
const ready = page => expect(page.locator('.scene-shell')).toHaveAttribute('data-phase', 'ready', { timeout: process.env.GS_BASE_URL ? 90_000 : 30_000 });
const vector = async (page, key) => (await page.locator('canvas').getAttribute(key)).split(',').map(Number);
const delta = (a, b) => Math.hypot(...a.map((v, i) => v - b[i]));

test('street conclusion exposes every actual outcome, matching images, metrics, decoded motion and mobile layout', async ({ page, browser }, info) => {
  const errors = [], gaussianRequests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (/\.(ply|splat|spz)$/.test(new URL(request.url()).pathname)) gaussianRequests.push(request.url()); });
  await page.goto('/experiments/street/');
  await expect(page.locator('#status')).toContainText('실제 학습·렌더 PASS');
  await expect(page.locator('#verdict-title')).toHaveText(summary.verdict.title);
  await expect(page.locator('#verdict-summary')).toHaveText(summary.verdict.summary);
  await expect(page.locator('#best-world')).toHaveAttribute('href', '/?world=' + summary.models.find(m => m.id === summary.best).world);
  await expect(page.locator('#best-world')).toBeInViewport();
  await expect(page.locator('.street-card')).toHaveCount(summary.models.length);
  await expect(page.locator('#run-metrics tbody tr')).toHaveCount(summary.models.length);
  await expect(page.locator('.street-stage')).toHaveCount(summary.stages.length);
  for (const model of summary.models) {
    const card = page.locator(`.street-card[data-model="${model.id}"]`);
    await card.scrollIntoViewIfNeeded();
    await expect.poll(() => card.locator('img').evaluate(img => img.complete && img.naturalWidth > 0)).toBe(true);
    await expect(card).toContainText(model.quality);
  }
  for (const view of [summary.views.find(v => v.kind === 'held'), summary.views.find(v => v.kind === 'held' && v.id.includes('-down-')), summary.views.find(v => v.kind === 'train'), summary.views.find(v => v.kind === 'offpath')]) {
    await page.locator('#view-select').selectOption(view.id);
    const images = page.locator('#compare-images img');
    await expect(images).toHaveCount(summary.models.length + (view.source ? 1 : 0));
    await expect.poll(() => images.evaluateAll(imgs => imgs.every(img => img.complete && img.naturalWidth === 512))).toBe(true);
    for (const region of ['band', 'road-band', 'mid-height-band']) {
      await page.locator('#region-select').selectOption(region);
      const rows = page.locator('#view-metrics tbody tr');
      await expect(rows).toHaveCount(summary.models.length);
      for (let i = 0; i < summary.models.length; i++) {
        const metric = summary.metrics.find(r => r.model === summary.models[i].id && r.view === view.id)?.regions[region];
        await expect(rows.nth(i).locator('td').nth(1)).toHaveText(metric ? metric.pixelCount.toLocaleString('ko-KR') : 'NOT RUN');
      }
    }
  }
  const video = page.locator('#comparison-video');
  await video.scrollIntoViewIfNeeded();
  await video.evaluate(v => v.load());
  await expect.poll(() => video.evaluate(v => v.readyState)).toBeGreaterThanOrEqual(2);
  expect(await video.evaluate(v => v.duration)).toBeGreaterThan(8);
  const decoded = [];
  for (const seconds of [1, 5]) {
    await video.evaluate((v, t) => new Promise(resolve => { v.addEventListener('seeked', resolve, { once: true }); v.currentTime = t; }), seconds);
    decoded.push(await video.evaluate(v => { const c = document.createElement('canvas'); c.width = 96; c.height = 96; c.getContext('2d').drawImage(v, 0, 0, 96, 96); return Array.from(c.getContext('2d').getImageData(0, 0, 96, 96).data).reduce((s, x) => s + x, 0); }));
  }
  expect(decoded[0]).not.toBe(decoded[1]);
  await page.locator('#verdict-title').scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('street-conclusion.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('street-mobile.png') });
  await expect(page.locator('canvas,iframe')).toHaveCount(0);
  expect(gaussianRequests).toEqual([]);
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('report-checks.json'), JSON.stringify({ time: new Date().toISOString(), browser: browser.version(), actualModels: summary.models.map(m => m.id), actualVideoDecodedFrameSums: decoded, checks: ['all model previews decoded', 'held level/down, train and offpath references; all region denominators', 'actual video seek and different decoded frames', 'all success/failure stages retained', '390px overflow', 'no automatic Gaussian download'], errors }, null, 2));
});

test('street report opens the recommended actual scene on demand with one renderer', async ({ page }) => {
  await page.goto('/experiments/street/');
  await expect(page.locator('#scene-select')).toBeEnabled();
  await expect(page.locator('#scene-select')).toHaveValue(summary.best);
  await page.locator('#open-scene').click();
  const frame = page.frameLocator('#viewer-host iframe');
  await expect(frame.locator('.scene-shell')).toHaveAttribute('data-phase', 'ready', { timeout: process.env.GS_BASE_URL ? 90_000 : 30_000 });
  await expect(frame.locator('canvas')).toHaveCount(1);
});

test('street report retains a visible error for an explicit HTTP failure fixture', async ({ page }) => {
  await page.route('**/experiments/street/summary.json', route => route.fulfill({ status: 503, body: 'TEST ONLY unavailable' }));
  await page.goto('/experiments/street/');
  await expect(page.locator('#status')).toContainText('FAIL · Error: summary.json HTTP 503');
  await expect(page.locator('#open-scene')).toBeDisabled();
  await expect(page.locator('canvas,iframe')).toHaveCount(0);
});

test('chronological lab retains every old result and makes the completed street comparison first', async ({ page }) => {
  const timeline = JSON.parse(await readFile('public/experiments/lab/timeline.json', 'utf8'));
  await page.goto('/experiments/lab/');
  await expect(page.locator('.entry')).toHaveCount(timeline.entries.length);
  await expect(page.locator('.entry').first()).toHaveAttribute('data-id', 'report-street-conclusion');
  for (const model of summary.models) await expect(page.locator(`.entry[data-id="street-${model.id}"]`)).toHaveCount(1);
  for (const order of ['newest', 'oldest']) {
    await page.selectOption('#order', order);
    const dates = await page.locator('.entry[data-created-at]').evaluateAll(cards => cards.map(card => Date.parse(card.dataset.createdAt)));
    expect(dates).toEqual([...dates].sort((a, b) => order === 'newest' ? b - a : a - b));
  }
  await page.selectOption('#kind', 'report');
  await expect(page.locator('.entry')).toHaveCount(timeline.entries.filter(e => e.kind === 'report').length);
});

for (const model of summary.models) {
  test(`actual street ${model.id} renders substantial pixels and supports recovered-route playback`, async ({ page, browser }, info) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(modelUrl(model));
    await ready(page);
    const canvas = page.locator('canvas');
    await expect(canvas).toHaveAttribute('data-navigation-mode', 'camera-path');
    await expect.poll(() => canvas.getAttribute('data-frame-count').then(Number)).toBeGreaterThan(10);
    const png = PNG.sync.read(await canvas.screenshot());
    let centralBrightPixels = 0;
    for (let y = Math.floor(png.height * .2); y < png.height * .75; y++) for (let x = Math.floor(png.width * .2); x < png.width * .8; x++) {
      const i = (y * png.width + x) * 4;
      if (Math.max(png.data[i], png.data[i + 1], png.data[i + 2]) > 65) centralBrightPixels++;
    }
    expect(centralBrightPixels).toBeGreaterThan(10_000);
    const start = await vector(page, 'data-camera-position');
    const orientation = await vector(page, 'data-camera-quaternion');
    await page.getByRole('button', { name: 'Play path', exact: true }).click();
    await expect.poll(() => canvas.getAttribute('data-path-progress').then(Number)).toBeGreaterThan(.05);
    await page.getByRole('button', { name: 'Pause path', exact: true }).click();
    const paused = await canvas.getAttribute('data-path-progress');
    await page.waitForTimeout(250);
    expect(await canvas.getAttribute('data-path-progress')).toBe(paused);
    expect(delta(await vector(page, 'data-camera-position'), start)).toBeGreaterThan(.001);
    await canvas.focus();
    const position = await vector(page, 'data-camera-position');
    const beforeLook = await vector(page, 'data-camera-quaternion');
    await page.keyboard.press('ArrowLeft');
    await expect.poll(async () => delta(await vector(page, 'data-camera-quaternion'), beforeLook)).toBeGreaterThan(.01);
    expect(delta(await vector(page, 'data-camera-position'), position)).toBeLessThan(1e-9);
    await page.getByRole('button', { name: 'Reset view', exact: true }).click();
    await expect.poll(async () => delta(await vector(page, 'data-camera-position'), start)).toBeLessThan(1e-9);
    expect(delta(await vector(page, 'data-camera-quaternion'), orientation)).toBeLessThan(1e-9);
    const fpsSamples = [];
    for (let i = 0; i < 3; i++) { await page.waitForTimeout(1100); fpsSamples.push(await page.locator('.render-details summary span').textContent()); }
    const adapter = await canvas.evaluate(c => { const gl = c.getContext('webgl2'); if (!gl) return null; const ext = gl.getExtension('WEBGL_debug_renderer_info'); return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); });
    await page.screenshot({ path: info.outputPath(model.id + '-actual.png') });
    expect(errors).toEqual([]);
    await writeFile(info.outputPath('native-browser-checks.json'), JSON.stringify({ time: new Date().toISOString(), browser: browser.version(), mode: process.env.HEADLESS === '1' ? 'headless' : 'headed', model: model.id, url: page.url(), viewport: page.viewportSize(), adapter, centralBrightPixels, fpsSamples, fpsMeaning: 'Three displayed one-second samples at the initial route camera; single session, not a controlled performance benchmark.', checks: ['actual local trained asset', 'substantial rendered central pixels', 'play/pause recovered path', 'free look keeps position', 'reset pose', 'one canvas'], geometricAccuracy: 'NOT RUN: independently measured ground truth unavailable', errors }, null, 2));
  });
}
