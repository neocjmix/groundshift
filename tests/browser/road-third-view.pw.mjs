import { test, expect } from '@playwright/test';
import { PNG } from 'pngjs';
import { writeFile } from 'node:fs/promises';

const timeout = process.env.GS_BASE_URL ? 60_000 : 10_000;
function visiblePoints(buffer) {
  const p = PNG.sync.read(buffer); let count = 0;
  for (let i = 64*p.width*4; i<p.data.length; i+=4) if (Math.max(p.data[i],p.data[i+1],p.data[i+2])>65) count++;
  return count;
}

test('real third-view evidence, sparse point clouds, shared support comparisons and chronological entry render', async ({ page, browser }, info) => {
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/experiments/road-third-view/');
  const summary=await (await page.request.get(new URL('summary.json',page.url()).href)).json();
  await expect(page.locator('h1')).toHaveText(summary.heading);
  await expect(page.locator('#quality-status')).toContainText('NOT ACCEPTED');
  await expect(page.locator('#conclusion')).toHaveText(summary.conclusion);
  await expect(page.locator('#sources img')).toHaveCount(3);
  await expect.poll(()=>page.locator('#sources img').evaluateAll(nodes=>nodes.every(n=>n.complete&&n.naturalWidth>0)),{timeout}).toBe(true);
  const canvas=page.locator('#cloud canvas');
  await expect(page.locator('#cloud-status')).toContainText('기존 44점 + 새 44점',{timeout});
  await canvas.scrollIntoViewIfNeeded();
  await page.selectOption('#cloud-selection','all');
  await expect(page.locator('#cloud-status')).toContainText('기존 291점 + 새 44점');
  const overview=await canvas.screenshot({path:info.outputPath('all-triangulations.png')});
  expect(visiblePoints(overview)).toBeGreaterThan(500);
  await page.selectOption('#cloud-selection','common');
  await expect(page.locator('#cloud-status')).toContainText('기존 44점 + 새 44점');
  const common=await canvas.screenshot({path:info.outputPath('common-triangulations.png')});
  expect(visiblePoints(common)).toBeGreaterThan(100);expect(common.equals(overview)).toBe(false);
  await page.selectOption('#cloud-color','rgb');
  const rgb=await canvas.screenshot({path:info.outputPath('observed-rgb.png')});expect(rgb.equals(common)).toBe(false);
  await page.selectOption('#cloud-selection','third');
  await expect(page.locator('#cloud-status')).toContainText('기존 0점 + 새 44점');
  const third=await canvas.screenshot();
  const bounds=await canvas.boundingBox();
  await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);await page.mouse.down();await page.mouse.move(bounds.x+bounds.width/2+100,bounds.y+bounds.height/2+50,{steps:10});await page.mouse.up();
  const rotated=await canvas.screenshot({path:info.outputPath('rotated.png')});expect(rotated.equals(third)).toBe(false);
  await page.click('#cloud-reset');
  for (const subset of ['all','previous-held','previous-training']) {
    await page.selectOption('#subset',subset);
    for (const id of ['baseline','augmented','new-only']) {
      const result=summary.evaluation.results[id][subset];const row=page.locator(`tr[data-variant="${id}"] td`);
      await expect(row.nth(1)).toHaveText(String(result.total));await expect(row.nth(2)).toHaveText(String(result.valid));await expect(row.nth(3)).toHaveText(String(result.invalid));
    }
  }
  await page.selectOption('#subset','all');
  await page.locator('#third-overlay').scrollIntoViewIfNeeded();
  await expect.poll(()=>page.locator('#third-overlay').evaluate(n=>n.complete&&n.naturalWidth>0),{timeout}).toBe(true);
  await page.locator('#third-overlay').screenshot({path:info.outputPath('third-observed-overlay.png')});
  await page.locator('#examples summary').click();const examples=page.locator('#examples img');await examples.scrollIntoViewIfNeeded();
  await expect.poll(()=>examples.evaluate(n=>n.complete&&n.naturalWidth>0),{timeout}).toBe(true);
  await examples.screenshot({path:info.outputPath('deterministic-patches.png')});
  await page.locator('#examples summary').click();await page.screenshot({path:info.outputPath('report.png'),fullPage:true});
  for (const file of ['previous45.ply','observed56.ply']) {
    const response=await page.request.get(new URL(file,page.url()).href);expect(response.ok()).toBe(true);
    expect((await response.body()).subarray(0,3).toString()).toBe('ply');
  }
  await page.goto('/experiments/lab/');await expect(page.locator('.entry[data-id="report-road-third-view"]')).toBeVisible();
  const dates=await page.locator('.entry[data-created-at]').evaluateAll(nodes=>nodes.map(n=>Date.parse(n.dataset.createdAt)));expect(dates).toEqual([...dates].sort((a,b)=>b-a));
  expect(errors).toEqual([]);
  await writeFile(info.outputPath('render-checks.json'),JSON.stringify({status:'PASS',origin:new URL(page.url()).origin,browser:browser.version(),headed:process.env.HEADLESS!=='1',coloredPixels:visiblePoints(overview),supportedTracks:44,totalTracks:291,errors,limitation:'Actual sparse stereo clouds and observed RGB evidence; no claim of street geometric accuracy.'},null,2));
});

test('a missing point-cloud asset reports FAIL instead of claiming rendering succeeded', async ({ page }) => {
  await page.route('**/road-third-view/cloud.json',route=>route.fulfill({status:503,body:'fixture: unavailable'}));
  await page.goto('/experiments/road-third-view/');
  await expect(page.locator('#execution-status')).toContainText('불러오기 FAIL');
  await expect(page.locator('#cloud-status')).toContainText('표시 FAIL');
  await expect(page.locator('#cloud canvas')).toHaveCount(0);await expect(page.locator('#cloud-selection')).toBeDisabled();
});
