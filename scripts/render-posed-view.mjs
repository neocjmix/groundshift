#!/usr/bin/env node
// Experimental offscreen-data capture in a real headed Chrome WebGL context.
// Uses an explicitly supplied reconstructed camera; no pose is fabricated.
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { createReadStream } from 'node:fs';
import { createHash } from 'node:crypto';
import { parseArgs } from 'node:util';
import { createServer } from 'vite';
import { chromium } from '@playwright/test';
import { PNG } from 'pngjs';

const { values } = parseArgs({ options: {
  dataset: { type: 'string' }, ply: { type: 'string' }, frame: { type: 'string' },
  output: { type: 'string' }, 'alpha-threshold': { type: 'string', default: '240' },
} });
if (!values.dataset || !values.ply || !values.frame || !values.output) {
  throw new Error('Require --dataset DIR --ply FILE --frame images/NAME --output NEW_DIR');
}
const output = path.resolve(values.output);
await mkdir(path.dirname(output), { recursive: true });
await mkdir(output, { recursive: false });
const started = performance.now();
const report = { status: 'RUNNING', frame: values.frame,
  renderKind: 'gaussian-reconstruction', diffusionUsed: false,
  poseSource: 'Existing dataset camera-to-world matrix; this render does not estimate poses',
  maskMeaning: 'Rendered accumulated opacity below threshold; not a validated geometry/disocclusion mask',
  imageIsSynthetic: true, novelViewQuality: 'NOT RUN' };
let server, browser;
try {
  const transforms = JSON.parse(await readFile(path.join(values.dataset, 'transforms.json'), 'utf8'));
  const selected = transforms.frames.find(f => f.file_path === values.frame);
  if (!selected) throw new Error('Requested frame is absent from transforms.json');
  const camera = { ...transforms, ...selected }; delete camera.frames;
  if (camera.camera_model && !['PINHOLE', 'OPENCV'].includes(camera.camera_model)) throw new Error('Pinhole data required');
  for (const k of ['k1', 'k2', 'k3', 'k4', 'p1', 'p2']) {
    if (Math.abs(camera[k] ?? 0) > 1e-12) throw new Error('Undistorted image required');
  }
  for (const k of ['w', 'h', 'fl_x', 'fl_y']) {
    if (!Number.isFinite(camera[k]) || camera[k] <= 0) throw new Error(`Invalid camera ${k}`);
  }
  if (camera.w > 2048 || camera.h > 2048) throw new Error('Experiment bounded to 2048px; provide matching resized calibration');
  if (![camera.cx, camera.cy, ...camera.transform_matrix.flat()].every(Number.isFinite)) throw new Error('Nonfinite camera');
  const threshold = Number(values['alpha-threshold']);
  if (!Number.isInteger(threshold) || threshold < 1 || threshold > 254) throw new Error('Alpha threshold must be 1..254');
  const ply = path.resolve(values.ply);
  const plyInfo = await stat(ply);
  report.assetSha256 = createHash('sha256').update(await readFile(ply)).digest('hex');
  const html = `<!doctype html><html><body style="margin:0"><script type="module">
    import * as THREE from 'three';
    import { SparkRenderer, SplatMesh } from '@sparkjsdev/spark';
    window.renderPose = async (c) => {
      const r = new THREE.WebGLRenderer({alpha:true, premultipliedAlpha:true, antialias:false, preserveDrawingBuffer:true});
      r.setPixelRatio(1); r.setSize(c.w,c.h); r.setClearColor(0x000000,0);
      document.body.append(r.domElement);
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera();
      const near=0.01, far=10000;
      camera.near=near; camera.far=far;
      camera.projectionMatrix.makePerspective(-c.cx*near/c.fl_x,(c.w-c.cx)*near/c.fl_x,c.cy*near/c.fl_y,-(c.h-c.cy)*near/c.fl_y,near,far);
      camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
      camera.matrix.fromArray(c.transform_matrix[0].map((_,i)=>c.transform_matrix.map(row=>row[i])).flat());
      camera.matrix.decompose(camera.position,camera.quaternion,camera.scale); camera.updateMatrixWorld(true);
      const spark=new SparkRenderer({renderer:r}); scene.add(spark);
      const mesh=new SplatMesh({url:'/__gs_experiment/scene.ply'}); scene.add(mesh); await mesh.initialized;
      for(let i=0;i<90;i++){r.render(scene,camera); await new Promise(requestAnimationFrame);}
      const gl=r.getContext(); const ext=gl.getExtension('WEBGL_debug_renderer_info');
      const result={png:r.domElement.toDataURL('image/png'),splats:mesh.numSplats,gpu:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER)};
      mesh.dispose(); spark.dispose(); r.dispose(); return result;
    };
  </script></body></html>`;
  const browserSource = html.match(/<script type="module">([\s\S]*)<\/script>/)[1];
  const serveExperiment = (req, res, next) => {
    if (req.url === '/__gs_experiment/scene.ply') {
      res.setHeader('Content-Type', 'application/octet-stream'); res.setHeader('Content-Length', plyInfo.size);
      createReadStream(ply).pipe(res);
    } else if (req.url === '/__gs_experiment/') { res.setHeader('Content-Type', 'text/html');
      res.end('<!doctype html><body style="margin:0"><script type="module" src="/__gs_experiment/main.js"></script>'); }
    else next();
  };
  server = await createServer({ configFile: false, root: process.cwd(),
    plugins: [{name:'gs-experiment', configureServer(s) { s.middlewares.use(serveExperiment); },
      resolveId(id) { if (id === '/__gs_experiment/main.js') return '\0gs-experiment'; },
      load(id) { if (id === '\0gs-experiment') return browserSource; } }],
    optimizeDeps: {include:['three','@sparkjsdev/spark']},
    server: { host: '127.0.0.1', port: 4326, strictPort: true } });
  await server.listen();
  browser = await chromium.launch({ channel: 'chrome', headless: false });
  const page = await browser.newPage({ viewport: { width: camera.w, height: camera.h }, deviceScaleFactor: 1 });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:4326/__gs_experiment/');
  await page.waitForFunction(() => typeof window.renderPose === 'function', undefined, { timeout: 30000 });
  const result = await page.evaluate(c => Promise.race([window.renderPose(c),
    new Promise((_, reject) => setTimeout(() => reject(new Error('Rendering exceeded 60 seconds')), 60000))]), camera);
  if (errors.length) throw new Error(errors.join('\n'));
  const bytes = Buffer.from(result.png.split(',')[1], 'base64');
  await writeFile(path.join(output, 'rgba.png'), bytes);
  const rgba = PNG.sync.read(bytes), rgb = new PNG({ width: rgba.width, height: rgba.height });
  const mask = new PNG({ width: rgba.width, height: rgba.height });
  let masked = 0, alphaSum = 0;
  for (let i = 0; i < rgba.data.length; i += 4) {
    const alpha = rgba.data[i + 3], hole = alpha < threshold; masked += Number(hole); alphaSum += alpha;
    // Grey composite is an input convenience, not observed scene content.
    for (let k = 0; k < 3; k++) {
      rgb.data[i+k] = Math.round(rgba.data[i+k]*alpha/255 + 127*(1-alpha/255));
      mask.data[i+k] = hole ? 255 : 0;
    }
    rgb.data[i+3] = mask.data[i+3] = 255;
  }
  await writeFile(path.join(output, 'input.png'), PNG.sync.write(rgb));
  await writeFile(path.join(output, 'mask.png'), PNG.sync.write(mask, { colorType: 0, inputColorType: 6 }));
  if (!result.splats || alphaSum === 0) throw new Error('No nontransparent Gaussian pixels were rendered');
  Object.assign(report, { status: 'PASS', gpu: result.gpu, splats: result.splats, camera,
    alphaThreshold: threshold, maskedFraction: masked/(rgba.width*rgba.height),
    meanAlpha: alphaSum/(255*rgba.width*rgba.height), pngSha256: createHash('sha256').update(bytes).digest('hex') });
} catch (error) {
  report.status = 'FAIL'; report.error = String(error.stack ?? error); process.exitCode = 1;
} finally {
  await browser?.close(); await server?.close();
  report.elapsedSeconds = (performance.now()-started)/1000;
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status, output, error:report.error, maskedFraction:report.maskedFraction}));
}
