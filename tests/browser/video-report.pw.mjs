import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';

const summary = JSON.parse(await readFile('public/experiments/video-4to6/summary.json', 'utf8'));

test('65-frame panorama video plays in Chrome and opens the actual Gaussian scene', async ({ page, browser }, info) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/experiments/video-4to6/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('65개의 구면 프레임');
  const images = page.locator('figure img');
  await expect(images).toHaveCount(10);
  for (let index = 0; index < 10; index++) {
    await images.nth(index).scrollIntoViewIfNeeded();
    const edge = index < 7 ? [1024, 512] : [512, 512];
    await expect.poll(() => images.nth(index).evaluate((image, size) => image.complete && image.naturalWidth === size[0] && image.naturalHeight === size[1], edge)).toBe(true);
  }
  const video = page.locator('video');
  await expect.poll(() => video.evaluate(element => element.readyState >= HTMLMediaElement.HAVE_METADATA), { timeout: 60_000 }).toBe(true);
  const metadata = await video.evaluate(element => ({ width: element.videoWidth, height: element.videoHeight, duration: element.duration }));
  expect(metadata.width).toBe(2048);
  expect(metadata.height).toBe(1024);
  expect(metadata.duration).toBeGreaterThan(2.6);
  expect(metadata.duration).toBeLessThan(2.8);
  await video.evaluate(element => element.play());
  await expect.poll(() => video.evaluate(element => element.currentTime), { timeout: 30_000 }).toBeGreaterThan(0.2);
  await video.evaluate(element => { element.pause(); element.currentTime = 1.3; });
  await expect.poll(() => video.evaluate(element => element.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA), { timeout: 30_000 }).toBe(true);
  await page.screenshot({ path: info.outputPath('video-report.png'), fullPage: true });
  expect(summary.generation.videoSha256).toMatch(/^[a-f0-9]{64}$/);
  expect(summary.status.frameGeneration).toBe('PASS');
  expect(summary.status.LTXVideoDiffusion).toBe('NOT RUN');
  await page.locator('a[href="/?world=/worlds/beijing-video-rife/world.json"]').last().click();
  await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase', 'ready', { timeout: process.env.GS_BASE_URL ? 90_000 : 60_000 });
  await expect(page.locator('canvas')).toHaveCount(1);
  await expect.poll(() => page.locator('canvas').getAttribute('data-frame-count').then(Number)).toBeGreaterThan(5);
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('video-report-checks.json'), JSON.stringify({
    browser: browser.version(), mode: process.env.HEADLESS === '1' ? 'headless' : 'headed',
    origin: new URL(page.url()).origin, metadata, scene: 'beijing-video-rife', errors,
    checks: ['seven decoded 1024x512 stills and three 512x512 inpaint crops', '2048x1024 MP4 metadata and real playback',
      'seek and decoded video frame', 'linked Gaussian PLY actual canvas render'],
    evidenceLimit: 'Browser playback/rendering does not establish true 3D geometry or street fidelity.',
  }, null, 2));
});
