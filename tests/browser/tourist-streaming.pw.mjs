import { test,expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';

test('real tourist source route, photograph switching and honest stage boundaries',async({page,browser},info)=>{
  const errors=[],sceneRequests=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/\.(ply|spz|splat|ksplat|sog)$/.test(new URL(r.url()).pathname))sceneRequests.push(r.url());});
  await page.goto('/experiments/tourist-streaming/');
  await expect(page.locator('#summary')).toContainText('2.19km');
  await expect(page.locator('#metrics')).toContainText('876장');
  await expect.poll(()=>page.locator('#route polyline').getAttribute('points').then(v=>v?.trim().split(' ').length)).toBe(876);
  const photo=page.locator('#photo');await expect(photo).toHaveAttribute('data-rank','1008');
  await expect.poll(()=>photo.evaluate(img=>img.complete&&img.naturalWidth===2048&&img.naturalHeight===1024)).toBe(true);
  await page.locator('#preview-index').focus();await page.locator('#preview-index').press('End');await expect(photo).toHaveAttribute('data-rank','1683');
  await expect.poll(()=>photo.evaluate(img=>img.complete&&img.naturalWidth===2048)).toBe(true);
  await expect(page.locator('#selected')).toContainText('2.19km');
  await page.locator('#preview-index').press('Home');await expect(photo).toHaveAttribute('data-rank','808');
  await expect.poll(()=>photo.evaluate(img=>img.complete&&img.naturalWidth===2048)).toBe(true);
  await expect(page.locator('#selected')).toContainText('0.00km');
  const summary=await (await page.request.get('/experiments/tourist-streaming/summary.json')).json();
  for(const title of ['새 관광지 GS 재구성','SPZ 구간 스트리밍·레이지로딩'])await expect(page.locator('.street-stage').filter({has:page.getByText(title,{exact:true})})).toContainText(summary.stages.find(s=>s.title===title).status);
  if(summary.result){await expect(page.locator('#result-links a').first()).toHaveAttribute('href','/?world='+summary.result.worldPath);await expect.poll(()=>page.locator('#result-poster').evaluate(i=>i.complete&&i.naturalWidth>=256)).toBe(true);}
  if(summary.measurements){await expect(page.locator('#result-metrics .metric')).toHaveCount(summary.measurements.length);await expect(page.locator('#result-metrics')).toContainText('8페이지');}
  if(summary.comparisons){const images=page.locator('#result-comparisons img');await expect(images).toHaveCount(summary.comparisons.length);for(const image of await images.all()){await image.scrollIntoViewIfNeeded();await expect.poll(()=>image.evaluate(i=>i.complete&&i.naturalWidth>256)).toBe(true);}}
  const route=await page.request.get('/experiments/tourist-streaming/route.json');expect(route.ok()).toBe(true);const data=await route.json();
  expect(data.images).toHaveLength(876);expect(data.images.every(i=>i.license==='etalab-2.0'&&i.dimensions[0]===12288&&i.dimensions[1]===6144)).toBe(true);
  await expect(page.locator('#metrics')).toContainText('24장 · 202.5MB');
  const acquisition=await page.request.get('/experiments/tourist-streaming/acquisition.json');expect(acquisition.ok()).toBe(true);const a=await acquisition.json();
  expect(a.status).toBe('PASS');expect(a.frames).toHaveLength(24);expect(a.fullRouteAcquired).toBe(false);expect(a.totalBytes).toBe(202545787);
  expect(data.images.filter(i=>i.hdSha256)).toHaveLength(24);
  const missing=await page.request.get('/experiments/tourist-streaming/images/00988_'+a.frames[0].id+'.jpg');
  // Vite preview falls back to index.html; the deployed static server returns 404.
  expect(missing.status()).toBe(process.env.GS_BASE_URL?404:200);
  expect(missing.headers()['content-type']||'').not.toMatch(/^image\//i);
  const missingBody=await missing.body();expect(missingBody.subarray(0,3).equals(Buffer.from([0xff,0xd8,0xff]))).toBe(false);
  await page.screenshot({path:info.outputPath('source-report.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await expect(page.locator('canvas')).toHaveCount(0);expect(sceneRequests).toEqual([]);expect(errors).toEqual([]);
  await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',browser:browser.version(),headed:process.env.HEADLESS!=='1',observations:876,polylinePoints:876,realSdImageDecode:true,selectedRanks:[1008,1683,808],mobileOverflow:false,sceneRequests,errors,
    privateHdResponseStatus:missing.status(),privateHdImageReturned:false,
    scope:'Source-scoping page, not Gaussian reconstruction or streaming acceptance'},null,2));
});

test('new tourist report is discoverable in chronological lab',async({page})=>{
  await page.goto('/experiments/lab/');await expect(page.locator('a[href="/experiments/tourist-streaming/"]').first()).toBeVisible();
  await page.locator('a[href="/experiments/tourist-streaming/"]').first().click();await expect(page.locator('#summary')).toContainText('2.19km');
});
