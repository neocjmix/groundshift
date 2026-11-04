import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { existsSync } from 'node:fs';
import { PNG } from 'pngjs';

const sample = JSON.parse(await readFile('public/worlds/sample/world.json', 'utf8'));
const position = async page => (await page.locator('canvas').getAttribute('data-camera-position')).split(',').map(Number);
const distance = (a, b) => Math.hypot(...a.map((v, i) => v - b[i]));
const ready = page => expect(page.locator('.scene-shell')).toHaveAttribute('data-phase', 'ready', { timeout: 30_000 });

function nonBackgroundPixels(buffer) {
  const png = PNG.sync.read(buffer);
  let colored = 0;
  // Only the central scene area, excluding all UI labels and controls.
  for (let y = Math.floor(png.height * 0.2); y < png.height * 0.75; y++) {
    for (let x = Math.floor(png.width * 0.2); x < png.width * 0.8; x++) {
      const i = (y * png.width + x) * 4;
      if (Math.max(png.data[i], png.data[i + 1], png.data[i + 2]) > 65) colored++;
    }
  }
  return colored;
}

test('actual scene renders; orbit, immediate reset, zoom, folder replacement and responsive view work', async ({ page, browser }, info) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await ready(page);
  await expect(page.locator('.render-details summary')).toContainText('fps');
  const canvas = page.locator('canvas');
  const screenshot = await canvas.screenshot();
  const coloredPixels = nonBackgroundPixels(screenshot);
  expect(coloredPixels).toBeGreaterThan(10_000);
  await page.screenshot({ path: info.outputPath('sample.png') });
  const start = await position(page);
  const box = await canvas.boundingBox();
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.45);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.5, { steps: 12 });
  await page.mouse.up();
  expect(distance(await position(page), start)).toBeGreaterThan(0.1);
  await page.getByRole('button', { name: 'Reset view' }).click();
  await expect.poll(async () => distance(await position(page), start)).toBeLessThan(1e-6);
  await page.waitForTimeout(300);
  expect(distance(await position(page), start)).toBeLessThan(1e-6);
  await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
  await expect.poll(async () => distance(await position(page), sample.navigation.camera.target)).toBeLessThan(distance(start, sample.navigation.camera.target));
  await page.getByRole('button', { name: 'Zoom out', exact: true }).click();
  await page.getByRole('button', { name: 'Reset view' }).click();
  await canvas.hover();
  await page.mouse.wheel(0, -180);
  await expect.poll(async () => distance(await position(page), start)).toBeGreaterThan(0.01);
  await page.getByRole('button', { name: 'Reset view' }).click();
  const fps = [];
  for (let i = 0; i < 5; i++) {
    await page.waitForTimeout(1050);
    fps.push(Number((await page.locator('.render-details summary span').innerText()).replace(' fps', '')));
  }
  await page.locator('.render-details summary').click();
  const details = await page.locator('.render-details').innerText();
  expect(details).toContain('113,648');
  await page.screenshot({ path: info.outputPath('sample-details.png') });
  await page.locator('.render-details summary').click();
  await page.getByLabel('Choose world folder').setInputFiles(path.resolve('public/worlds/sample'));
  await ready(page);
  await expect(canvas).toHaveCount(1);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: info.outputPath('mobile-layout.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('measurements.json'), JSON.stringify({
    time: new Date().toISOString(), browser: browser.version(), viewport: {width:1440,height:1000},
    mode: process.env.HEADLESS === '1' ? 'headless' : 'headed', fpsSamplesRounded: fps,
    centralNonBackgroundPixels: coloredPixels, details,
    checks: ['pixel occupancy', 'orbit', 'immediate reset settles', 'zoom buttons', 'wheel zoom', 'local folder replacement', 'mobile overflow'],
    visualReview: 'Requires separate screenshot inspection; automated pixel check does not prove quality.',
  }, null, 2));
});

test('locally reconstructed artifact renders on the same viewer', async ({page,browser},info) => {
  test.skip(!existsSync('public/worlds/reconstructed/scene.ply'), 'NOT RUN: run the native reconstruction first');
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/?world=/worlds/reconstructed/world.json');
  await ready(page);
  await expect(page.locator('.render-details summary')).toContainText('fps');
  expect(nonBackgroundPixels(await page.locator('canvas').screenshot())).toBeGreaterThan(10_000);
  const fps=[];
  for(let i=0;i<5;i++) { await page.waitForTimeout(1050); fps.push(await page.locator('.render-details summary span').innerText()); }
  await page.screenshot({path:info.outputPath('reconstructed.png')});
  await page.locator('.render-details summary').click();
  const details=await page.locator('.render-details').innerText();
  await page.screenshot({path:info.outputPath('reconstructed-details.png')});
  await writeFile(info.outputPath('measurements.json'),JSON.stringify({time:new Date().toISOString(),browser:browser.version(),details,fps,errors,visualReview:'Requires separate screenshot inspection.'},null,2));
  expect(errors).toEqual([]);
});

test('manifest, missing/corrupt asset, slow-load replacement and GPU context loss are recoverable', async ({ page }, info) => {
  await page.goto('/?world=/missing-world.json');
  await expect(page.getByRole('alert')).toContainText('JSON world manifest');
  await page.getByRole('button', { name: 'Open sample', exact: true }).click();
  await ready(page);
  await page.route('**/broken-world.json', route => route.fulfill({json: {...sample, assets:[{...sample.assets[0],path:'absent.splat'}]}}));
  await page.route('**/absent.splat', route => route.fulfill({status:404,body:'Not found'}));
  await page.locator('.source-picker summary').click();
  await page.getByLabel('World manifest URL').fill('/broken-world.json');
  await page.getByRole('button', { name:'Load world →' }).click();
  await expect(page.locator('.scene-overlay')).toContainText('Scene asset: HTTP 404');
  await page.screenshot({path:info.outputPath('missing-asset.png')});
  await page.route('**/corrupt-world.json', route => route.fulfill({json:{...sample,assets:[{...sample.assets[0],format:'ply',path:'corrupt.ply'}]}}));
  await page.route('**/corrupt.ply', route => route.fulfill({body:'This is not a Gaussian PLY file.'}));
  await page.getByLabel('World manifest URL').fill('/corrupt-world.json');
  await page.getByRole('button', { name:'Load world →' }).click();
  await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','error');
  await page.getByRole('button', { name:'The small things' }).click();
  await ready(page);
  // Delay one actual asset request, replace it, and verify stale completion cannot win.
  await page.route('**/slow-world.json', route => route.fulfill({json:{...sample,id:'slow',assets:[{...sample.assets[0],path:'slow.splat'}]}}));
  await page.route('**/slow.splat', async route => { await new Promise(resolve=>setTimeout(resolve,1500)); await route.fulfill({body:await readFile('public/worlds/sample/plant.splat')}).catch(()=>{}); });
  await page.getByLabel('World manifest URL').fill('/slow-world.json');
  await page.getByRole('button', { name:'Load world →' }).click();
  await expect(page.locator('.scene-topline')).toContainText('slow');
  await page.getByRole('button', { name:'The small things' }).click();
  await ready(page);
  await page.waitForTimeout(1700);
  await expect(page.locator('.scene-topline')).toContainText('houseplant');
  await page.locator('canvas').evaluate(canvas=>canvas.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
  await expect(page.locator('.scene-overlay')).toContainText('graphics context was lost');
  await page.getByRole('button',{name:'Retry scene'}).click();
  await ready(page);
});
