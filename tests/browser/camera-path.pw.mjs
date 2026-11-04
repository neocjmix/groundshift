import { test, expect } from '@playwright/test';
import { existsSync } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';

const value = async (page, attribute) => (await page.locator('canvas').getAttribute(attribute)).split(',').map(Number);
const progress = async page => Number(await page.locator('canvas').getAttribute('data-path-progress'));
const distance = (a, b) => Math.hypot(...a.map((v, i) => v - b[i]));

test('real poses render with test-only continuity: playback, gaps, free look, reset and orbit', async ({ page, browser }, info) => {
  test.skip(!existsSync('public/worlds/reconstructed/scene.ply'), 'NOT RUN: reconstruct the real sample first');
  const manifest = JSON.parse(await readFile('public/worlds/reconstructed/world.json', 'utf8'));
  const cameras = JSON.parse(await readFile('public/worlds/reconstructed/cameras.json', 'utf8'));
  // Real measured poses and real reconstructed scene. Only these continuity
  // flags are fixtures: this test proves UI behavior, never physical route quality.
  const fixture = {
    ...cameras,
    sequenceNotes: 'TEST ONLY: continuity markers exercise controls and a gap. They do not establish a recovered walking trajectory.',
    frames: cameras.frames.slice(0, 6).map((frame, index) => ({
      ...frame, componentId: 'test-only-component', continuousFromPrevious: index > 0 && index !== 3,
    })),
  };
  await page.route(url => url.pathname === '/worlds/reconstructed/path-test-world.json', route => route.fulfill({ json: {
    ...manifest,
    navigation: { ...manifest.navigation, mode: 'camera-path', camerasPath: 'path-test-cameras.json' },
  } }));
  await page.route(url => url.pathname === '/worlds/reconstructed/path-test-cameras.json', route => route.fulfill({ json: fixture }));
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/?world=/worlds/reconstructed/path-test-world.json');
  await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase', 'ready', { timeout: 30_000 });
  const canvas = page.locator('canvas');
  await expect(canvas).toHaveAttribute('data-navigation-mode', 'camera-path');
  const startPosition = await value(page, 'data-camera-position');
  const startQuaternion = await value(page, 'data-camera-quaternion');
  const firstMeasuredPosition = fixture.frames[0].cameraToWorld.slice(0, 3).map(row => row[3]);
  expect(distance(startPosition, firstMeasuredPosition)).toBeLessThan(1e-9);
  await page.getByRole('button', { name: 'Play path', exact: true }).click();
  await expect.poll(() => progress(page)).toBeGreaterThan(0.1);
  await page.getByRole('button', { name: 'Pause path', exact: true }).click();
  const paused = await progress(page);
  await page.waitForTimeout(250);
  expect(await progress(page)).toBe(paused);

  await page.getByLabel('Path speed').selectOption('2');
  await page.getByRole('button', { name: 'Play path', exact: true }).click();
  await expect.poll(() => progress(page)).toBe(2);
  await expect(page.getByRole('button', { name: 'Play path', exact: true })).toBeDisabled();
  await expect(page.locator('.path-note')).toContainText('Continuity between these views is unverified');
  await page.waitForTimeout(250);
  expect(await progress(page)).toBe(2);
  const gapPosition = await value(page, 'data-camera-position');
  expect(distance(gapPosition, fixture.frames[2].cameraToWorld.slice(0, 3).map(row => row[3]))).toBeLessThan(1e-9);

  // Looking around must rotate only the view, never move off the recorded route.
  const beforeLook = await value(page, 'data-camera-quaternion');
  const box = await canvas.boundingBox();
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.55, { steps: 8 });
  await page.mouse.up();
  await expect.poll(async () => distance(await value(page, 'data-camera-quaternion'), beforeLook)).toBeGreaterThan(0.05);
  expect(distance(await value(page, 'data-camera-position'), gapPosition)).toBeLessThan(1e-9);
  await canvas.focus();
  const pointerLook = await value(page, 'data-camera-quaternion');
  await page.keyboard.press('ArrowLeft');
  await expect.poll(async () => distance(await value(page, 'data-camera-quaternion'), pointerLook)).toBeGreaterThan(0.01);
  expect(distance(await value(page, 'data-camera-position'), gapPosition)).toBeLessThan(1e-9);

  await page.getByRole('button', { name: 'Next recorded view', exact: true }).click();
  await expect.poll(() => progress(page)).toBe(3);
  await page.getByLabel('Path direction').selectOption('-1');
  await expect(page.getByRole('button', { name: 'Play path', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Previous recorded view', exact: true }).click();
  await expect.poll(() => progress(page)).toBe(2);
  await page.getByRole('button', { name: 'Play path', exact: true }).click();
  await expect.poll(() => progress(page)).toBe(0);
  await page.getByRole('button', { name: 'Reset view', exact: true }).click();
  await expect.poll(async () => distance(await value(page, 'data-camera-quaternion'), startQuaternion)).toBeLessThan(1e-9);
  expect(distance(await value(page, 'data-camera-position'), startPosition)).toBeLessThan(1e-9);

  await page.getByRole('button', { name: 'Orbit', exact: true }).click();
  await expect(canvas).toHaveAttribute('data-navigation-mode', 'orbit');
  await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
  await expect.poll(async () => distance(await value(page, 'data-camera-position'), manifest.navigation.camera.position)).toBeGreaterThan(0.01);
  await page.getByRole('button', { name: 'Camera path', exact: true }).click();
  await expect(canvas).toHaveAttribute('data-navigation-mode', 'camera-path');
  expect(distance(await value(page, 'data-camera-position'), startPosition)).toBeLessThan(1e-9);
  await expect(canvas).toHaveCount(1);
  await page.getByLabel('Path direction').selectOption('1');
  await page.getByRole('button', { name: 'Next recorded view', exact: true }).click();
  await page.getByRole('button', { name: 'Next recorded view', exact: true }).click();
  await page.screenshot({ path: info.outputPath('camera-path-gap.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: info.outputPath('camera-path-mobile.png'), fullPage: true });
  const panelBox = await page.locator('.path-panel').boundingBox();
  const titleBox = await page.locator('.scene-caption h2').boundingBox();
  expect(panelBox.y + panelBox.height).toBeLessThan(titleBox.y);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('camera-path-checks.json'), JSON.stringify({
    time: new Date().toISOString(), browser: browser.version(),
    mode: process.env.HEADLESS === '1' ? 'headless' : 'headed',
    scene: 'Actual reconstructed dozer with actual exported camera poses',
    continuity: 'TEST ONLY routed JSON markers; these do not validate capture ordering or physical route quality',
    checks: ['world-coordinate spawn', 'play', 'pause', 'speed selection', 'gap stop both directions', 'explicit checkpoint jumps', 'pointer and keyboard free look keep position', 'reset pose and look', 'orbit switch and zoom', 'one renderer', 'mobile overflow'],
    pathAcceptance: 'NOT RUN: genuine continuity and quality require a separately verified capture sequence.',
    errors,
  }, null, 2));
});
