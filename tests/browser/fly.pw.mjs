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
 const paging=JSON.parse(await canvas.getAttribute('data-paging'));expect(paging.pages).toBeLessThanOrEqual(paging.capacity/65536);expect(paging.errors).toEqual([]);expect(requests.some(p=>p.endsWith('.spz'))).toBe(false);expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',browser:browser.version(),headed:process.env.HEADLESS!=='1',world,nativeFullscreen:true,pointerLock:true,wasd:true,mouseLook:true,lift:true,reset:true,orbitHandoff:true,initialRequests,requestsAfter:requests.length,errors,scope:'Actual desktop input/rendering, no collision or geometry acceptance'},null,2));
});

test('Fly is available without camera metadata and drag look survives denied pointer lock',async({page},info)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.addInitScript(()=>{
   Element.prototype.requestPointerLock=function(){return Promise.reject(new Error('Test-only lock denial'));};
   // Timing fixture: lose the REAL GPU context while its readback is pending,
   // before contextlost can dispatch. No fabricated rejection or error handler.
   window.__loseAtReadback=false;window.__readbackLossTriggered=false;
   const wait=WebGL2RenderingContext.prototype.clientWaitSync;
   WebGL2RenderingContext.prototype.clientWaitSync=function(...args){
     if(window.__loseAtReadback&&!this.isContextLost()){
       window.__loseAtReadback=false;window.__readbackLossTriggered=true;
       this.getExtension('WEBGL_lose_context').loseContext();
     }
     return wait.apply(this,args);
   };
 });
 await ready(page,'/worlds/sample/world.json');await page.getByRole('button',{name:'Fly',exact:true}).click();await expect(page.locator('canvas')).toHaveAttribute('data-navigation-mode','fly');
 const canvas=page.locator('canvas'),box=await canvas.boundingBox(),start=await position(page),q=await rotation(page);
 await page.mouse.move(box.width*.5,box.height*.45);await page.mouse.down();await page.mouse.move(box.width*.6,box.height*.5,{steps:8});await page.mouse.up();await expect.poll(async()=>distance(await rotation(page),q)).toBeGreaterThan(.05);expect(distance(await position(page),start)).toBeLessThan(1e-8);
 await page.keyboard.press('Escape');await expect(canvas).toHaveAttribute('data-navigation-mode','orbit');await expect.poll(()=>page.evaluate(()=>document.fullscreenElement===null)).toBe(true);expect(errors).toEqual([]);
 await page.getByRole('button',{name:'Fly',exact:true}).click();await expect(canvas).toHaveAttribute('data-navigation-mode','fly');
 await page.evaluate(()=>{window.__loseAtReadback=true;});
 await page.mouse.move(box.width*.5,box.height*.45);await page.mouse.down();await page.mouse.move(box.width*.6,box.height*.5,{steps:8});await page.mouse.up();
 await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','error');expect(await page.evaluate(()=>window.__readbackLossTriggered)).toBe(true);
 await page.getByRole('button',{name:'Exit Fly'}).click();await expect(page.locator('.scene-shell')).not.toHaveClass(/is-fly/);await expect.poll(()=>page.evaluate(()=>document.fullscreenElement===null)).toBe(true);
 await page.getByRole('button',{name:'Retry scene',exact:true}).click();await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready');expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',scene:'Actual Houseplant without camera metadata',pointerLock:'Test-only denied API; actual fallback drag exercised',escape:true,forcedWebglContextLoss:true,faultFixture:'Real context loss immediately before pending clientWaitSync, before contextlost event',exitWhileRendererFailed:true,retryRendering:true,errors},null,2));
});

test('mobile floating movement, swipe look and right lift support independent touch and safe release',async({browser},info)=>{
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:1,baseURL:process.env.GS_BASE_URL||'http://127.0.0.1:4318'}),page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 // Explicit denial fixture exercises viewport fallback; this is not iPhone/Safari evidence.
 await page.addInitScript(()=>{Element.prototype.requestFullscreen=function(){return Promise.reject(new Error('Test-only denied native fullscreen'));};});
 try{
 await ready(page);await page.getByRole('button',{name:'Fly',exact:true}).click();await expect(page.locator('canvas')).toHaveAttribute('data-navigation-mode','fly');
 const shell=await page.locator('.scene-shell').boundingBox();expect(shell.x).toBe(0);expect(shell.y).toBe(0);expect(shell.width).toBe(390);expect(shell.height).toBe(844);
 await expect(page.locator('.fly-stick-look')).toHaveCount(0);
 const area=page.getByRole('group',{name:'Move joystick area',exact:true}),a=await area.boundingBox(),pad=page.locator('.fly-pad'),knob=page.locator('.fly-knob');
 const cdp=await context.newCDPSession(page),touch=(id,p)=>({id,x:p.x,y:p.y,radiusX:4,radiusY:4,force:1});
 const send=(type,points=[])=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points.map(([id,p])=>touch(id,p))});
 const center=box=>({x:box.x+box.width/2,y:box.y+box.height/2}),subtract=(a,b)=>a.map((v,i)=>v-b[i]),dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0);
 const checkCenter=async(origin)=>{
   const base=center(await pad.boundingBox()),handle=center(await knob.boundingBox());
   expect(Math.hypot(base.x-origin.x,base.y-origin.y)).toBeLessThan(1);
   expect(Math.hypot(handle.x-origin.x,handle.y-origin.y)).toBeLessThan(1);
   return{origin,base,handle};
 };
 // Place the origin low in the zone, then drag below the zone: capture must retain backward control.
 const low={x:a.x+a.width*.5,y:a.y+a.height-8},start=await position(page);
 await expect(pad).toBeHidden();await send('touchStart',[[1,low]]);await expect(pad).toBeVisible();const firstCenter=await checkCenter(low);
 await page.waitForTimeout(200);expect(distance(await position(page),start)).toBeLessThan(1e-8);
 await send('touchMove',[[1,{x:low.x,y:low.y+36}]]);await page.waitForTimeout(220);await expect.poll(async()=>distance(await position(page),start)).toBeGreaterThan(.01);
 await send('touchEnd');await settle(page);const backward=subtract(await position(page),start);
 await page.getByRole('button',{name:'Reset Fly position'}).tap();await expect.poll(async()=>distance(await position(page),start)).toBeLessThan(1e-8);
 await send('touchStart',[[1,low]]);await send('touchMove',[[1,{x:low.x,y:low.y-36}]]);await page.waitForTimeout(220);await send('touchEnd');await settle(page);
 const forward=subtract(await position(page),start),directionDot=dot(forward,backward)/(Math.hypot(...forward)*Math.hypot(...backward));expect(directionDot).toBeLessThan(-.99);
 const relocated={x:low.x+20,y:low.y-90};await send('touchStart',[[1,relocated]]);const relocatedCenter=await checkCenter(relocated);await send('touchMove',[[1,{x:relocated.x,y:relocated.y-30}]]);await page.waitForTimeout(150);await send('touchCancel');await expect(pad).toBeHidden();await settle(page);
 const cancelled=await position(page);await page.waitForTimeout(180);expect(distance(await position(page),cancelled)).toBeLessThan(1e-8);
 // Touch 1 owns movement; touch 2 owns canvas look. Releasing either must not disturb the other.
 const left={x:low.x,y:a.y+a.height*.5},right={x:280,y:380},rightMoved={x:320,y:366};
 const beforeDual=await position(page),look=await rotation(page);
 await send('touchStart',[[1,left],[2,right]]);await send('touchMove',[[1,{x:left.x,y:left.y-34}],[2,rightMoved]]);
 await page.waitForTimeout(300);await expect.poll(async()=>distance(await position(page),beforeDual)).toBeGreaterThan(.01);await expect.poll(async()=>distance(await rotation(page),look)).toBeGreaterThan(.05);
 await page.screenshot({path:info.outputPath('fly-mobile.png')});
 // CDP touchEnd lists the points being ended, not the remaining fingers.
 await send('touchEnd',[[1,{x:left.x,y:left.y-34}]]);await settle(page);const stopped=await position(page),lookBeforeContinuation=await rotation(page);
 await send('touchMove',[[2,{x:350,y:370}]]);await settle(page);expect(distance(await position(page),stopped)).toBeLessThan(1e-8);expect(distance(await rotation(page),lookBeforeContinuation)).toBeGreaterThan(.02);
 await send('touchEnd');await settle(page);const stoppedLook=await rotation(page);await page.waitForTimeout(150);expect(distance(await rotation(page),stoppedLook)).toBeLessThan(1e-8);
 const lift=await page.getByRole('button',{name:'Fly up',exact:true}).boundingBox();expect(lift.x).toBeGreaterThan(390*.75);expect(lift.width).toBeGreaterThanOrEqual(44);expect(lift.height).toBeGreaterThanOrEqual(44);
 const beforeLift=await position(page);await send('touchStart',[[3,center(lift)]]);await page.waitForTimeout(220);await send('touchEnd');await settle(page);const liftDisplacement=subtract(await position(page),beforeLift);expect(Math.hypot(...liftDisplacement)).toBeGreaterThan(.01);
 const liftStopped=await position(page);await page.waitForTimeout(150);expect(distance(await position(page),liftStopped)).toBeLessThan(1e-8);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 // Orientation change clears a held stick before placing the next origin in the resized viewport.
 await send('touchStart',[[1,left]]);await send('touchMove',[[1,{x:left.x,y:left.y-34}]]);await page.waitForTimeout(150);
 await page.setViewportSize({width:844,height:390});await settle(page);await expect(area).toHaveAttribute('data-active','false');const resized=await position(page);await page.waitForTimeout(200);expect(distance(await position(page),resized)).toBeLessThan(1e-8);await send('touchCancel');
 const landscape=await page.locator('.scene-shell').boundingBox();expect(landscape.height).toBe(390);
 const landscapeOrigin=center(await area.boundingBox());await send('touchStart',[[1,landscapeOrigin]]);const landscapeCenter=await checkCenter(landscapeOrigin);await send('touchMove',[[1,{x:landscapeOrigin.x+24,y:landscapeOrigin.y-20}]]);await settle(page);await page.screenshot({path:info.outputPath('fly-mobile-landscape.png')});await send('touchEnd');
 await page.getByRole('button',{name:'Exit Fly'}).tap();await expect(page.locator('canvas')).toHaveAttribute('data-navigation-mode','orbit');expect(await page.evaluate(()=>document.body.style.overflow)).not.toBe('hidden');expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',browser:browser.version(),headed:process.env.HEADLESS!=='1',world,viewportFallback:'PASS with test-only native fullscreen denial',input:'Actual CDP touch input',floatingOrigin:{firstCenter,relocatedCenter,landscapeCenter},neutralDrift:false,backward,forward,directionDot,simultaneousMovementSwipe:true,releaseLeftContinuesLook:true,cancelStops:true,resizeStops:true,liftDisplacement,portrait:[390,844],landscape:[844,390],errors,physicalIos:'NOT RUN'},null,2));
 }finally{await context.close();}
});
