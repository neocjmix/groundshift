import { test, expect } from '@playwright/test';
import { PNG } from 'pngjs';
import { writeFile } from 'node:fs/promises';
const timeout = process.env.GS_BASE_URL ? 60_000 : 10_000;
const url = '/experiments/panoramic-calibration/';
function visiblePoints(bytes) {
  const png = PNG.sync.read(bytes); let pixels = 0;
  for (let i = png.width * Math.min(64,png.height) * 4; i < png.data.length; i += 4) {
    if (Math.max(png.data[i],png.data[i + 1],png.data[i + 2]) > 65) pixels++;
  } return pixels;
}
const ready = (page,model,fit) => Promise.all([
  expect(page.locator('#cloud-status')).toContainText(model.toUpperCase(),{ timeout }),
  expect(page.locator('#cloud-status')).toContainText(fit === 'common' ? '공통점 보정' : '기존 보정',{ timeout }),
  expect(page.locator('#cloud-status')).toContainText('개 점',{ timeout }),
  expect(page.locator('#reset')).toBeEnabled({ timeout }),
]);

test('real calibration evidence, same-view original/common clouds and diagnostic strata render',async ({ page,browser },info) => {
  const errors = []; page.on('pageerror',error => errors.push(error.message)); await page.goto(url);
  const response = await page.request.get(new URL('summary.json',page.url()).href); expect(response.ok()).toBe(true); const summary = await response.json();
  await expect(page.locator('#status')).toHaveText('로컬 실행 PASS');
  const measurements = [];
  for (const model of summary.models) {
    await page.selectOption('#model-select',model.model);
    for (const direction of model.directions) {
      await page.selectOption('#direction-select',direction.id);
      const rows = page.locator('#comparison tbody tr'); await expect(rows).toHaveCount(4);
      for (const [index,key] of ['sfmPoint','sfmRay','original','common'].entries()) {
        await expect(rows.nth(index).locator('td').nth(1)).toHaveText(String(direction.methods[key].samples));
        await expect(rows.nth(index).locator('td').nth(4)).toHaveText(direction.methods[key].medianPixels.toLocaleString('ko-KR',{ maximumFractionDigits:3 }));
      }
      await expect(page.locator('#features')).toHaveAttribute('src',`${model.model}/${direction.id}-features.png`);
      await expect.poll(() => page.locator('#features').evaluate(i => i.complete && i.naturalWidth === 1536),{ timeout }).toBe(true);
      await expect(page.locator('#perspective-control')).toBeVisible();
      const control = summary.perspective.directions.find(d => d.id === direction.id);
      const controlRows = page.locator('#control-comparison tbody tr'); await expect(controlRows).toHaveCount(4);
      await expect(controlRows.last().locator('td').nth(3)).toHaveText(control.methods.perspective.medianPixels.toLocaleString('ko-KR',{ maximumFractionDigits:3 }));
      await expect.poll(() => page.locator('#control-features').evaluate(i => i.complete && i.naturalWidth === 1536),{ timeout }).toBe(true);
      for (const [group,count] of [['parallax',4],['longitude',12]]) { await page.selectOption('#control-strata-select',group); await expect(page.locator('#control-strata tbody tr')).toHaveCount(count); }
      for (const [group,count] of [['parallax',4],['longitude',12],['region',2]]) {
        await page.selectOption('#strata-select',group); await expect(page.locator('#strata tbody tr')).toHaveCount(count);
      }
    }
    const views = [];
    for (const fit of ['original','common']) {
      await page.selectOption('#fit-select',fit); await ready(page,model.model,fit); await page.selectOption('#view-select','overview');
      await page.locator('#cloud').scrollIntoViewIfNeeded(); await page.selectOption('#color-select','rgb');
      const canvas = page.locator('#cloud canvas'); await expect(canvas).toHaveCount(1);
      const shot = await canvas.screenshot({ path:info.outputPath(`${model.model}-${fit}.png`) }); expect(visiblePoints(shot)).toBeGreaterThan(1_000); views.push(shot);
      await page.selectOption('#color-select','source'); const colors = await canvas.screenshot({ path:info.outputPath(`${model.model}-${fit}-sources.png`) }); expect(colors.equals(shot)).toBe(false);
      for (const view of ['4','5']) { await page.selectOption('#view-select',view); await canvas.screenshot({ path:info.outputPath(`${model.model}-${fit}-view-${view}.png`) }); }
      await page.click('#reset');
    }
    expect(views[0].equals(views[1])).toBe(false); measurements.push({ model:model.model,status:'PASS',points:model.cloudPoints });
  }
  await page.screenshot({ path:info.outputPath('report.png'),fullPage:true }); expect(errors).toEqual([]);
  await writeFile(info.outputPath('render-evidence.json'),JSON.stringify({ status:'PASS',browser:browser.version(),origin:new URL(page.url()).origin,headed:process.env.HEADLESS !== '1',models:measurements,errors },null,2));
});

test('failed cloud recovers and chronological lab retains earlier pair report',async ({ page },info) => {
  await page.goto(url); await ready(page,'da2','original');
  const cloud = new URL('da2/cloud.json',page.url()).href;
  await page.route(cloud,route => route.fulfill({ status:503,body:'deliberate UI error recovery check' })); await page.selectOption('#fit-select','common');
  await expect(page.locator('#cloud-status')).toContainText('점군 불러오기 실패'); await expect(page.locator('#reset')).toBeDisabled();
  await page.screenshot({ path:info.outputPath('simulated-503.png') }); await page.unroute(cloud);
  await page.selectOption('#fit-select','original'); await ready(page,'da2','original'); await page.selectOption('#fit-select','common'); await ready(page,'da2','common');
  await page.goto('/experiments/lab/'); await expect(page.locator('.entry').first()).toHaveAttribute('data-id','report-panoramic-calibration');
  await expect(page.locator('.entry[data-id="report-panoramic-pair"]')).toHaveCount(1); await page.selectOption('#order','oldest');
  const times = await page.locator('.entry[data-created-at]').evaluateAll(nodes => nodes.map(n => Date.parse(n.dataset.createdAt)));
  expect(times.every((t,i) => !i || t >= times[i - 1])).toBe(true);
  await page.locator('.entry[data-id="report-panoramic-calibration"] a').first().click(); await expect(page).toHaveURL(/\/experiments\/panoramic-calibration\/$/);
});
