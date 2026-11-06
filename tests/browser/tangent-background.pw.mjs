import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {PNG} from 'pngjs';
const summary=JSON.parse(await readFile('public/experiments/tangent-background/summary.json','utf8'));

test('tangent observation shows actual phase, selected inputs, pending stages and retained history',async({page},info)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/experiments/tangent-background/');
  await expect(page.locator('#status')).toHaveText('공개 단계 · '+summary.phase);
  await expect(page.locator('#title')).toHaveText(summary.title);
  await expect(page.locator('#stages .street-stage')).toHaveCount(summary.stages.length);
  const images=page.locator('#samples img');await expect(images).toHaveCount(summary.samples.reduce((n,s)=>n+1+Number(Boolean(s.baseline)),0));
  for(const img of await images.all())await img.scrollIntoViewIfNeeded();
  await expect.poll(()=>images.evaluateAll(imgs=>imgs.every(i=>i.complete&&i.naturalWidth>0)),{timeout:30000}).toBe(true);
  for(const img of await page.locator('#comparisons img').all()){await img.scrollIntoViewIfNeeded();await expect.poll(()=>img.evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);}
  if(summary.run?.world)await expect(page.locator('#new-world')).toHaveAttribute('href','/?world='+summary.run.world);else await expect(page.locator('#new-world')).toBeHidden();
  await expect(page.locator('canvas,iframe')).toHaveCount(0);
  await page.screenshot({path:info.outputPath('report.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test('tangent report errors remain explicit and previous observations remain discoverable',async({page})=>{
  await page.route('**/experiments/tangent-background/summary.json',r=>r.fulfill({status:503,body:'SYNTHETIC ERROR'}));
  await page.goto('/experiments/tangent-background/');await expect(page.locator('#status')).toContainText('불러오기 FAIL');
  await page.goto('/experiments/lab/');for(const id of ['report-tangent-background','report-final-quality','report-model-selection'])await expect(page.locator(`.entry[data-id="${id}"]`)).toHaveCount(1);
  await page.goto('/');await expect(page.getByRole('link',{name:'최신 · 이십면체 방향과 배경 보완',exact:true})).toHaveAttribute('href','/experiments/tangent-background/');
});

function colored(png){let n=0;for(let i=0;i<png.data.length;i+=4)if(Math.max(...png.data.subarray(i,i+3))>65)n++;return n;}
function backdropPixels(png){let n=0;for(let i=0;i<png.data.length;i+=4)if(Math.abs(png.data[i]-17)<=3&&Math.abs(png.data[i+1]-22)<=3&&Math.abs(png.data[i+2]-20)<=3)n++;return {width:png.width,height:png.height,clearColorLikePixels:n,clearColorLikeFraction:n/(png.width*png.height)};}
async function captureCanvas(page,canvas,path){const style=await page.addStyleTag({content:'.scene-shell > :not(.canvas-mount){visibility:hidden!important}'});try{return PNG.sync.read(await canvas.screenshot({path}));}finally{await style.evaluate(e=>e.remove());}}

test('actual tangent GS renders independently before optional photo and depth backgrounds',async({page,browser},info)=>{
  test.skip(!summary.run?.world,'New native scene has not exported; actual GS/background rendering NOT RUN.');
  const errors=[],backgroundRequests=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/\/background\/.*\.(jpg|png|json)/.test(r.url())&&!r.url().endsWith('/background.json'))backgroundRequests.push(r.url());});
  await page.goto('/?world='+encodeURIComponent(summary.run.world));
  await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});
  await expect(page.getByRole('link',{name:'Comparison & stage history ↗'})).toHaveAttribute('href','/experiments/tangent-background/');
  const canvas=page.locator('canvas');await expect(canvas).toHaveAttribute('data-background-mode','gs');expect(backgroundRequests).toEqual([]);
  await expect.poll(()=>canvas.getAttribute('data-frame-count').then(Number)).toBeGreaterThan(12);
  const gsOnly=await captureCanvas(page,canvas,info.outputPath('gs-only.png'));const gsColored=colored(gsOnly);expect(gsColored).toBeGreaterThan(10000);const modePixels={gs:backdropPixels(gsOnly)};
  const control=page.getByRole('combobox',{name:'Background completion'});await expect(control).toHaveValue('gs');
  await control.selectOption('panorama');await expect(canvas).toHaveAttribute('data-background-mode','panorama');
  await expect.poll(()=>canvas.getAttribute('data-background-source'),{timeout:60000}).not.toBe('');
  await expect(page.locator('.background-panel [role="status"]')).toContainText('presentation only');
  modePixels.panorama=backdropPixels(await captureCanvas(page,canvas,info.outputPath('panorama.png')));
  await control.selectOption('depth-shell');await expect(canvas).toHaveAttribute('data-background-mode','depth-shell');
  modePixels.depthShell=backdropPixels(await captureCanvas(page,canvas,info.outputPath('depth-shell.png')));
  await page.getByRole('button',{name:'Play path',exact:true}).click();await expect.poll(()=>canvas.getAttribute('data-path-progress').then(Number)).toBeGreaterThan(.05);await page.getByRole('button',{name:'Pause path',exact:true}).click();
  await control.selectOption('gs');await expect(canvas).toHaveAttribute('data-background-mode','gs');await expect(canvas).toHaveAttribute('data-background-source','');
  expect(errors).toEqual([]);await writeFile(info.outputPath('evidence.json'),JSON.stringify({browser:browser.version(),world:summary.run.world,gsOnlyColoredPixels:gsColored,modePixels,pixelMeaning:'Clear-color-like display pixels only; neither geometric completeness nor accuracy. All three mode captures use the same camera before path movement.',backgroundRequests,errors,geometryAccuracy:'NOT RUN'},null,2));
});
