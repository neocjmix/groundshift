import { test, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { PNG } from 'pngjs';

const timeout = process.env.GS_BASE_URL ? 60_000 : 10_000;
function colored(buffer) {
  const png = PNG.sync.read(buffer); let count = 0;
  for (let i = 64 * png.width * 4; i < png.data.length; i += 4) {
    if (Math.max(png.data[i], png.data[i+1], png.data[i+2]) > 65) count++;
  }
  return count;
}

test('actual correspondence controls, invalid-depth evidence, match gallery and chronological report render', async ({ page, browser }, info) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto('/experiments/stereo-anchors/');
  const response = await page.request.get(new URL('summary.json', page.url()).href);
  expect(response.ok()).toBe(true); const summary = await response.json();
  expect(summary.models.map(model => model.id)).toEqual(['augmented','baseline','new-only','sift-augmented','sift-only']);
  await expect(page.locator('h1')).toHaveText(summary.heading);
  await expect(page.locator('#quality-status')).toContainText('NOT ACCEPTED');
  await expect(page.locator('#conclusion')).toHaveText(summary.conclusion);
  const observations = [];
  for (const model of summary.models) {
    await page.selectOption('#model-select', model.id);
    await expect(page.locator('#cloud-status')).toContainText(model.title, { timeout });
    await expect(page.locator('#capture-4')).toBeEnabled({ timeout });
    await page.click('#overview-view'); const canvas = page.locator('#cloud canvas');
    const overview = await canvas.screenshot({ path: info.outputPath(`${model.id}-overview.png`) });
    expect(colored(overview)).toBeGreaterThan(1000);
    await page.selectOption('#color-mode','source');
    const colors = await canvas.screenshot({ path: info.outputPath(`${model.id}-sources.png`) });
    expect(colors.equals(overview)).toBe(false);
    await page.selectOption('#source-select','0'); await expect(page.locator('#cloud-status')).toContainText('4번 출처만');
    expect((await canvas.screenshot()).equals(colors)).toBe(false);
    await page.selectOption('#source-select','both'); await page.selectOption('#color-mode','rgb');
    const views = [];
    for (const source of ['4','5']) {
      await page.click(`#capture-${source}`);
      views.push(await canvas.screenshot({ path: info.outputPath(`${model.id}-capture-${source}.png`) }));
    }
    expect(views[0].equals(views[1])).toBe(false);
    for (const direction of model.directions) {
      await page.selectOption('#direction-select',direction.id);
      await expect(page.locator('#direction-metrics')).toContainText('이전217개 검사점 중 무효');
      for (const key of ['source','target','depth','warp','residual','overlap']) await expect(page.locator(`#direction-${key}`)).toHaveAttribute('src',direction[key]);
      await expect.poll(() => page.locator('img[id^="direction-"][src]').evaluateAll(images => images.every(image => image.complete && image.naturalWidth>0)), { timeout }).toBe(true);
    }
    observations.push({ id:model.id,coloredPixels:colored(overview),status:await page.locator('#cloud-status').innerText() });
  }
  await page.locator('#matching-evidence summary').click();
  await expect(page.locator('#evidence-images img')).toHaveCount(20);
  const evidence = page.locator('#evidence-images img').nth(6); await evidence.scrollIntoViewIfNeeded();
  await expect.poll(() => evidence.evaluate(image => image.complete && image.naturalWidth>0), { timeout }).toBe(true);
  await evidence.screenshot({ path:info.outputPath('down-000-correspondences.png') });
  await page.locator('#matching-evidence summary').click();
  await page.screenshot({ path:info.outputPath('report.png'),fullPage:true });
  await page.goto('/experiments/lab/'); await expect(page.locator('.entry[data-id="report-stereo-anchors"]')).toBeVisible();
  const times = await page.locator('.entry[data-created-at]').evaluateAll(nodes => nodes.map(n => Date.parse(n.dataset.createdAt)));
  expect(times).toEqual([...times].sort((a,b) => b-a)); expect(errors).toEqual([]);
  await writeFile(info.outputPath('render-checks.json'),JSON.stringify({ status:'PASS',time:new Date().toISOString(),origin:new URL(page.url()).origin,browser:browser.version(),headed:process.env.HEADLESS!=='1',observations,errors,limitation:'Actual rendered diagnostic clouds; geometric accuracy remains NOT ACCEPTED. Gallery lines are algorithmic correspondences, not proven identity.' },null,2));
});
