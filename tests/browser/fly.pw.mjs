import {test,expect} from '@playwright/test';
import {writeFile} from 'node:fs/promises';
const world=process.env.GS_FLY_WORLD??'/worlds/paris-58m-lod/world.json';
const vec=async(page,name)=>((await page.locator('canvas').getAttribute(name))??'').split(',').map(Number);
const position=p=>vec(p,'data-camera-position');
const rotation=p=>vec(p,'data-camera-quaternion');
const distance=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i]));
async function ready(page,which=world){await page.goto('/?world='+which);await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});}
async function settle(page){await page.waitForTimeout(150);}

test('desktop Fly enters actual fullscreen, uses WASD and mouse, resets and returns to Orbit without reloading',async({page,browser},info)=>{
 await page.addInitScript(()=>{const original=Element.prototype.requestPointerLock;window.__pointerDiagnostics=[];Element.prototype.requestPointerLock=function(...args){window.__pointerDiagnostics.push({focus:document.hasFocus(),secure:window.isSecureContext,activation:navigator.userActivation.isActive});try{const result=original.apply(this,args);return result?.catch(e=>{window.__pointerDiagnostics.push({error:String(e)});throw e;});}catch(e){window.__pointerDiagnostics.push({error:String(e)});throw e;}};});
 const errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/\.(rad|radc|spz|ply)$/.test(new URL(r.url()).pathname))requests.push(new URL(r.url()).pathname);});
 await ready(page);const canvas=page.locator('canvas'),start=await position(page),initialRequests=requests.length;
 expect((await page.getByRole('button',{name:'Fly',exact:true}).boundingBox()).height).toBeGreaterThanOrEqual(44);
 await canvas.evaluate(e=>{e.dataset.flyIdentity='retained';});
 await page.getByRole('button',{name:'Fly',exact:true}).click();await expect(canvas).toHaveAttribute('data-navigation-mode','fly');
 await expect.poll(()=>page.evaluate(()=>Boolean(document.fullscreenElement))).toBe(true);
 const box=await page.locator('.scene-shell').boundingBox();expect(box.width).toBeGreaterThan(1000);
 await page.keyboard.down('KeyW');await page.waitForTimeout(400);await page.keyboard.up('KeyW');await expect.poll(async()=>distance(await position(page),start)).toBeGreaterThan(.01);
 const stopped=await position(page);await page.waitForTimeout(150);expect(distance(await position(page),stopped)).toBeLessThan(1e-8);
 await page.bringToFront();await settle(page);
 const beforeLook=await rotation(page);await canvas.click({position:{x:box.width*.5,y:box.height*.5}});await expect.poll(()=>page.evaluate(()=>document.pointerLockElement?.tagName)).toBe('CANVAS').catch(async e=>{await writeFile(info.outputPath('pointer-diagnostic.json'),JSON.stringify(await page.evaluate(()=>window.__pointerDiagnostics),null,2));throw e;});
 await page.mouse.move(box.width*.5+90,box.height*.5+15);await expect.poll(async()=>distance(await rotation(page),beforeLook)).toBeGreaterThan(.02);
 await page.evaluate(()=>document.exitPointerLock());await settle(page);
 await page.getByRole('button',{name:'Fly up',exact:true}).focus();const beforeLift=await position(page);await page.keyboard.down('KeyE');await page.waitForTimeout(200);await page.keyboard.up('KeyE');expect(distance(await position(page),beforeLift)).toBeGreaterThan(.01);
 await page.getByRole('button',{name:'Reset Fly position'}).click();await expect.poll(async()=>distance(await position(page),start)).toBeLessThan(1e-8);
 await page.screenshot({path:info.outputPath('fly-desktop.png')});
 const help=await page.locator('.fly-help').boundingBox(),lift=await page.locator('.fly-lift').boundingBox();expect(help.y+help.height).toBeLessThan(lift.y);
 const beforeExit=await position(page);await page.getByRole('button',{name:'Exit Fly'}).click();await expect(canvas).toHaveAttribute('data-navigation-mode','orbit');await expect.poll(()=>page.evaluate(()=>document.fullscreenElement===null)).toBe(true);
 expect(distance(await position(page),beforeExit)).toBeLessThan(1e-8);await expect(canvas).toHaveCount(1);await expect(canvas).toHaveAttribute('data-fly-identity','retained');
 const paging=JSON.parse(await canvas.getAttribute('data-paging'));expect(paging.pages).toBeLessThanOrEqual(8);expect(paging.errors).toEqual([]);expect(requests.some(p=>p.endsWith('.spz'))).toBe(false);expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',browser:browser.version(),headed:process.env.HEADLESS!=='1',world,nativeFullscreen:true,pointerLock:true,wasd:true,mouseLook:true,lift:true,reset:true,orbitHandoff:true,initialRequests,requestsAfter:requests.length,errors,scope:'Actual desktop input/rendering, no collision or geometry acceptance'},null,2));
});

test('Fly is available without camera metadata and drag look survives denied pointer lock',async({page},info)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.addInitScript(()=>{Element.prototype.requestPointerLock=function(){return Promise.reject(new Error('Test-only lock denial'));};});
 await ready(page,'/worlds/sample/world.json');await page.getByRole('button',{name:'Fly',exact:true}).click();await expect(page.locator('canvas')).toHaveAttribute('data-navigation-mode','fly');
 const canvas=page.locator('canvas'),box=await canvas.boundingBox(),start=await position(page),q=await rotation(page);
 await page.mouse.move(box.width*.5,box.height*.45);await page.mouse.down();await page.mouse.move(box.width*.6,box.height*.5,{steps:8});await page.mouse.up();await expect.poll(async()=>distance(await rotation(page),q)).toBeGreaterThan(.05);expect(distance(await position(page),start)).toBeLessThan(1e-8);
 await page.keyboard.press('Escape');await expect(canvas).toHaveAttribute('data-navigation-mode','orbit');await expect.poll(()=>page.evaluate(()=>document.fullscreenElement===null)).toBe(true);expect(errors).toEqual([]);
 await page.getByRole('button',{name:'Fly',exact:true}).click();await expect(canvas).toHaveAttribute('data-navigation-mode','fly');
 await canvas.evaluate(c=>c.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','error');
 await page.getByRole('button',{name:'Exit Fly'}).click();await expect(page.locator('.scene-shell')).not.toHaveClass(/is-fly/);await expect.poll(()=>page.evaluate(()=>document.fullscreenElement===null)).toBe(true);
 await page.getByRole('button',{name:'Retry scene',exact:true}).click();await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready');expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',scene:'Actual Houseplant without camera metadata',pointerLock:'Test-only denied API; actual fallback drag exercised',escape:true,forcedWebglContextLoss:true,exitWhileRendererFailed:true,retryRendering:true,errors},null,2));
});

test('two simultaneous mobile touch sticks move and look, release safely and support viewport fullscreen fallback',async({browser},info)=>{
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:1,baseURL:process.env.GS_BASE_URL||'http://127.0.0.1:4318'}),page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 // This specifically exercises the fallback. It is not an iPhone/Safari hardware claim.
 await page.addInitScript(()=>{Element.prototype.requestFullscreen=function(){return Promise.reject(new Error('Test-only denied native fullscreen'));};});
 try{
 await ready(page);await page.getByRole('button',{name:'Fly',exact:true}).click();await expect(page.locator('canvas')).toHaveAttribute('data-navigation-mode','fly');
 const shell=await page.locator('.scene-shell').boundingBox();expect(shell.x).toBe(0);expect(shell.y).toBe(0);expect(shell.width).toBe(390);expect(shell.height).toBe(844);
 const a=await page.getByRole('group',{name:'이동 joystick',exact:true}).boundingBox(),b=await page.getByRole('group',{name:'시선 joystick',exact:true}).boundingBox();
 const center=box=>({x:box.x+box.width/2,y:box.y+box.height/2}),left=center(a),right=center(b),cdp=await context.newCDPSession(page);
 const touch=(id,p)=>({id,x:p.x,y:p.y,radiusX:4,radiusY:4,force:1});
 const start=await position(page),look=await rotation(page);
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[touch(1,left),touch(2,right)]});
 await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[touch(1,{x:left.x,y:left.y-34}),touch(2,{x:right.x+28,y:right.y})]});
 await page.waitForTimeout(450);await expect.poll(async()=>distance(await position(page),start)).toBeGreaterThan(.01);await expect.poll(async()=>distance(await rotation(page),look)).toBeGreaterThan(.05);
 await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await settle(page);const stopped=await position(page),stoppedLook=await rotation(page);await page.waitForTimeout(200);expect(distance(await position(page),stopped)).toBeLessThan(1e-8);expect(distance(await rotation(page),stoppedLook)).toBeLessThan(1e-8);
 await page.screenshot({path:info.outputPath('fly-mobile.png')});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.setViewportSize({width:844,height:390});await settle(page);await page.screenshot({path:info.outputPath('fly-mobile-landscape.png')});
 const landscape=await page.locator('.scene-shell').boundingBox();expect(landscape.height).toBe(390);
 await page.getByRole('button',{name:'Exit Fly'}).tap();await expect(page.locator('canvas')).toHaveAttribute('data-navigation-mode','orbit');expect(await page.evaluate(()=>document.body.style.overflow)).not.toBe('hidden');expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',browser:browser.version(),headed:process.env.HEADLESS!=='1',world,viewportFallback:'PASS with test-only native fullscreen denial',dualTouch:'PASS actual CDP multi-touch input',portrait:[390,844],landscape:[844,390],releaseStops:true,errors,physicalIos:'NOT RUN'},null,2));
 }finally{await context.close();}
});
