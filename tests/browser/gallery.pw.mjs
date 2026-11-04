import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import { PNG } from 'pngjs';

const catalog = JSON.parse(await readFile('public/worlds/catalog.json', 'utf8'));
const sceneUrl = scene => `/?world=${encodeURIComponent(scene.manifestPath)}`;
const collection = page => page.getByRole('region', { name: 'Scene collection' });
const ready = page => expect(page.locator('.scene-shell')).toHaveAttribute('data-phase', 'ready', { timeout: 30_000 });
const card = (page, scene) => collection(page).getByRole('link').filter({ has: page.getByRole('heading', { name: scene.title, exact: true }) });

test('gallery shows real previews, filters and mobile layout without starting WebGL or loading scene assets', async ({ page, browser }, info) => {
  const assets = [];
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (/\.(ply|splat|spz|ksplat|sog)$/.test(new URL(request.url()).pathname)) assets.push(request.url());
  });
  await page.addInitScript(() => {
    window.__webglRequests = 0;
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (...args) {
      if (['webgl', 'webgl2', 'experimental-webgl'].includes(args[0])) window.__webglRequests++;
      return original.apply(this, args);
    };
  });
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Places worth returning to.');
  await expect(collection(page).getByRole('link')).toHaveCount(4);
  for (const scene of catalog.scenes) {
    await expect(card(page, scene)).toHaveAttribute('href', sceneUrl(scene));
    await expect.poll(() => card(page, scene).locator('img').evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
  }
  await page.screenshot({ path: info.outputPath('gallery-desktop.png'), fullPage: true });
  await page.getByRole('button', { name: 'Local reconstruction', exact: true }).click();
  await expect(collection(page).getByRole('link')).toHaveCount(2);
  await page.getByRole('button', { name: 'All scenes', exact: true }).click();
  await page.getByRole('searchbox', { name: 'Search scenes' }).fill('desk');
  await expect(collection(page).getByRole('link')).toHaveCount(1);
  await expect(card(page, catalog.scenes.find(scene => scene.id === 'desk'))).toBeVisible();
  await page.getByRole('searchbox', { name: 'Search scenes' }).fill('no-such-place');
  await expect(page.getByRole('status')).toContainText('No scenes match');
  await page.getByRole('button', { name: 'Show all scenes' }).click();
  await expect(collection(page).getByRole('link')).toHaveCount(4);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: info.outputPath('gallery-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.locator('canvas')).toHaveCount(0);
  expect(await page.evaluate(() => window.__webglRequests)).toBe(0);
  expect(assets).toEqual([]);
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('gallery-checks.json'), JSON.stringify({
    time: new Date().toISOString(), browser: browser.version(), mode: process.env.HEADLESS === '1' ? 'headless' : 'headed',
    checks: ['four catalog links and loaded preview images', 'category filter', 'search and empty-state recovery', '390px mobile overflow', 'zero WebGL context requests on gallery', 'zero Gaussian asset requests on gallery'],
    sceneAssetsRequested: assets, webglContextRequests: 0, errors,
  }, null, 2));
});

test('card, saved-scene links, back to scenes and browser history preserve the selected scene', async ({ page }) => {
  const desk = catalog.scenes.find(scene => scene.id === 'desk');
  const independent = catalog.scenes.find(scene => scene.id === 'independent');
  await page.goto('/');
  await card(page, desk).click();
  await expect(page).toHaveURL(url => url.searchParams.get('world') === desk.manifestPath);
  await ready(page);
  await page.getByRole('link', { name: 'Back to scenes' }).click();
  await expect(collection(page)).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(0);
  await expect(page).toHaveURL(url => url.search === '');
  await page.goBack();
  await ready(page);
  await expect(page).toHaveURL(url => url.searchParams.get('world') === desk.manifestPath);
  await page.goBack();
  await expect(collection(page)).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(0);
  await page.goForward();
  await ready(page);
  await page.getByRole('navigation', { name: 'Saved scenes' }).getByRole('link', { name: independent.title }).click();
  await ready(page);
  await expect(page).toHaveURL(url => url.searchParams.get('world') === independent.manifestPath);
  await expect(page.locator('canvas')).toHaveCount(1);
  await page.goBack();
  await ready(page);
  await expect(page).toHaveURL(url => url.searchParams.get('world') === desk.manifestPath);
  await expect(page.locator('canvas')).toHaveCount(1);
});

test('returning to gallery during a delayed manifest load prevents a late viewer or scene download', async ({ page }) => {
  const desk = catalog.scenes.find(scene => scene.id === 'desk');
  const manifest = await readFile(`public${desk.manifestPath}`);
  let release;
  let started;
  const gate = new Promise(resolve => { release = resolve; });
  const requested = new Promise(resolve => { started = resolve; });
  const assets = [];
  page.on('request', request => { if (new URL(request.url()).pathname.endsWith('/desk/scene.ply')) assets.push(request.url()); });
  await page.route(url => url.pathname === desk.manifestPath, async route => {
    started();
    await gate;
    await route.fulfill({ body: manifest, contentType: 'application/json' }).catch(() => {});
  });
  try {
    await page.goto('/');
    await card(page, desk).click();
    await requested;
    await page.getByRole('link', { name: 'Back to scenes' }).click();
    release();
    await expect(collection(page)).toBeVisible();
    await page.waitForTimeout(500);
    await expect(page.locator('canvas')).toHaveCount(0);
    expect(assets).toEqual([]);
  } finally { release(); }
});

for (const scene of catalog.scenes) {
  test(`deep link renders actual ${scene.id} scene and survives reload`, async ({ page, browser }, info) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(sceneUrl(scene));
    await ready(page);
    const canvas = page.locator('canvas');
    await expect(canvas).toHaveCount(1);
    await expect.poll(() => canvas.getAttribute('data-frame-count').then(Number)).toBeGreaterThan(5);
    const png = PNG.sync.read(await canvas.screenshot());
    let brightPixels = 0;
    for (let y = Math.floor(png.height * .2); y < png.height * .75; y++) {
      for (let x = Math.floor(png.width * .2); x < png.width * .8; x++) {
        const i = (y * png.width + x) * 4;
        if (Math.max(png.data[i], png.data[i+1], png.data[i+2]) > 65) brightPixels++;
      }
    }
    expect(brightPixels).toBeGreaterThan(10_000);
    await page.screenshot({ path: info.outputPath(`${scene.id}-viewer.png`) });
    await page.reload();
    await ready(page);
    await expect(page).toHaveURL(url => url.searchParams.get('world') === scene.manifestPath);
    await expect(canvas).toHaveCount(1);
    expect(errors).toEqual([]);
    await writeFile(info.outputPath('render-checks.json'), JSON.stringify({
      time: new Date().toISOString(), browser: browser.version(), mode: process.env.HEADLESS === '1' ? 'headless' : 'headed',
      scene: scene.id, manifest: scene.manifestPath, centralBrightPixels: brightPixels, errors,
      checks: ['direct URL actual asset render', 'nonempty central pixels', 'one canvas', 'reload preserves selected scene'],
      visualReview: 'Separate human/model screenshot review is required; pixels alone do not prove scene quality.',
    }, null, 2));
  });
}
