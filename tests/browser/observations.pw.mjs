import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';

const catalog = JSON.parse(await readFile('public/worlds/catalog.json', 'utf8'));
const summary = JSON.parse(await readFile('public/experiments/mapillary/summary.json', 'utf8'));

test('observation report shows real comparisons, generation masks and every outcome without hiding failed stages', async ({ page, browser }, info) => {
  const errors = [];
  const gaussianRequests = [];
  const imageChecks = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (/\.(ply|splat|spz|ksplat|sog)$/.test(new URL(request.url()).pathname)) gaussianRequests.push(request.url());
  });
  await page.goto('/');
  await page.getByRole('link', { name: 'Compare source, warp & diffusion' }).click();
  await expect(page).toHaveURL(/\/experiments\/mapillary\/index\.html$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('실제로 본 곳과, 모델이 채운 곳.');

  for (const [key, view, maskFraction] of [['stereo', '04', '75.12%'], ['gs', '02', '2.21%']]) {
    await page.locator(`#${key}`).click();
    await expect(page.locator(`#${key}`)).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator(`#${key === 'stereo' ? 'gs' : 'stereo'}`)).toHaveAttribute('aria-pressed', 'false');
    await expect(page.locator('#description')).toContainText(maskFraction);
    await expect(page.locator('#real')).toHaveAttribute('src', `images/real-${view}.png`);
    for (const role of ['input', 'mask', 'completed']) {
      await expect(page.locator(`#${role}`)).toHaveAttribute('src', `images/${key}-${role}.png`);
    }
    for (const id of ['real', 'input', 'mask', 'completed', 'under', 'over']) {
      const image = page.locator(`#${id}`);
      await image.scrollIntoViewIfNeeded();
      await expect.poll(() => image.evaluate(element => element.complete && element.naturalWidth === 512 && element.naturalHeight === 512)).toBe(true);
      imageChecks.push({ case: key, id, src: await image.getAttribute('src'), width: 512, height: 512 });
    }
    await expect(page.locator('#rows tr')).toHaveCount(3);
    await expect(page.locator('#rows')).toContainText('단순 회색 채우기');
    await expect(page.locator('#grayLink')).toHaveAttribute('href', `images/${key}-gray.png`);
    await page.getByRole('heading', { level: 1 }).scrollIntoViewIfNeeded();
    if (key === 'stereo') await page.screenshot({ path: info.outputPath('observation-overview.png') });
    await page.screenshot({ path: info.outputPath(`${key}-comparison.png`), fullPage: true });
  }

  const slider = page.getByRole('slider', { name: '생성 결과 불투명도' });
  await slider.focus();
  await slider.press('Home');
  await expect(slider).toHaveValue('0');
  await expect(page.locator('#value')).toHaveText('0%');
  await expect(page.locator('#over')).toHaveCSS('opacity', '0');
  await slider.press('End');
  await expect(slider).toHaveValue('100');
  await expect(page.locator('#value')).toHaveText('100%');
  await expect(page.locator('#over')).toHaveCSS('opacity', '1');

  const scenePaths = await page.locator('a[href*="?world="]').evaluateAll(links =>
    [...new Set(links.map(link => new URL(link.href).searchParams.get('world')))].sort());
  expect(scenePaths).toEqual(catalog.scenes.map(scene => scene.manifestPath).sort());
  const history = page.locator('details');
  await history.locator('summary').click();
  await expect(history.locator('tbody tr')).toHaveCount(summary.history.length);
  for (const status of ['PASS', 'FAIL', 'CANCELLED', 'NOT RUN', 'NOT RECORDED']) {
    await expect(history.getByRole('cell', { name: status, exact: true }).first()).toBeVisible();
  }
  await history.locator('summary').click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('heading', { level: 1 }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('observation-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.locator('canvas')).toHaveCount(0);
  expect(gaussianRequests).toEqual([]);
  expect(errors).toEqual([]);
  await page.getByRole('link', { name: '← 모든 장면', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Groundshift observation room.');
  await expect(page.getByRole('region', { name: 'Scene collection' }).getByRole('link')).toHaveCount(catalog.scenes.length);

  await writeFile(info.outputPath('observation-checks.json'), JSON.stringify({
    time: new Date().toISOString(), browser: browser.version(), mode: process.env.HEADLESS === '1' ? 'headless' : 'headed',
    origin: new URL(page.url()).origin, imageChecks, scenePaths, historyRows: summary.history.length,
    checks: ['both comparison cases load actual 512px images and masks', 'gray baseline rows and image links', 'overlay slider endpoints', 'all catalog scene links', 'failed, cancelled and unrun history retained', '390px mobile overflow', 'return to all scenes'],
    gaussianRequests, errors,
    evidenceLimit: 'UI and stored image verification only; this test does not rerun reconstruction or inference, or imply quality acceptance.',
  }, null, 2));
});
