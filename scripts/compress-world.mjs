#!/usr/bin/env node
// Local CPU/WASM format conversion; no retraining, filtering, recentering or pose changes.
import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gzipSync, gunzipSync } from 'node:zlib';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');

// Deliberately bounded to the actual Brush binary float-only export, not a general PLY parser.
export function inspectPly(bytes) {
  const marker = Buffer.from('end_header\n');
  const end = bytes.indexOf(marker);
  if (end < 0 || end > 65536) throw new Error('Missing bounded PLY header');
  const offset = end + marker.length, header = bytes.subarray(0, offset).toString('ascii');
  if (!header.startsWith('ply\nformat binary_little_endian 1.0\n')) throw new Error('Require binary little-endian PLY');
  const elements = [...header.matchAll(/^element (\w+) (\d+)$/gm)];
  if (elements.length !== 1 || elements[0][1] !== 'vertex') throw new Error('Require vertex-only PLY');
  const count = Number(elements[0][2]);
  const properties = [...header.matchAll(/^property (.+)$/gm)].map(m => m[1]);
  if (!properties.length || properties.some(p => !/^float \w+$/.test(p))) throw new Error('Require float32 properties');
  const names = properties.map(p => p.slice(6)), stride = 4 * names.length;
  if (!count || new Set(names).size !== names.length || bytes.length !== offset + count * stride) throw new Error('PLY count/length/property mismatch');
  for (const name of ['x','y','z','opacity','rot_0','rot_1','rot_2','rot_3','scale_0','scale_1','scale_2','f_dc_0','f_dc_1','f_dc_2']) {
    if (!names.includes(name)) throw new Error('Missing Gaussian property: ' + name);
  }
  const rest = names.filter(n => n.startsWith('f_rest_')).length;
  const shDegree = [0,9,24,45].indexOf(rest);
  if (shDegree < 0 || Array.from({length:rest},(_,i)=>`f_rest_${i}`).some(n=>!names.includes(n))) throw new Error('Invalid SH coefficients');
  const axes = ['x','y','z'].map(n => names.indexOf(n) * 4);
  const min = [Infinity,Infinity,Infinity], max = [-Infinity,-Infinity,-Infinity];
  for (let i = 0; i < count; i++) {
    const base = offset + i * stride;
    for (let p = 0; p < names.length; p++) if (!Number.isFinite(bytes.readFloatLE(base+p*4))) throw new Error('Nonfinite Gaussian property');
    for (let k = 0; k < 3; k++) {
      const value = bytes.readFloatLE(base+axes[k]);
      min[k] = Math.min(min[k],value); max[k] = Math.max(max[k],value);
    }
  }
  return { count, shDegree, offset, stride, axes, min, max };
}

export function fractionalBitsFor(bounds) {
  const maximum = Math.max(...bounds.min.map(Math.abs),...bounds.max.map(Math.abs));
  // Highest position precision fitting signed 24-bit, leaving one integer of headroom.
  const bits = Math.min(20, Math.floor(Math.log2(8388606 / Math.max(maximum, 1e-20))));
  if (bits < 0) throw new Error('Coordinates exceed SPZ fixed-point range; do not silently rescale');
  return bits;
}

export function inspectSpz(bytes) {
  const raw = gunzipSync(bytes);
  if (raw.length < 16 || raw.readUInt32LE(0) !== 0x5053474e || raw.readUInt32LE(4) !== 3) throw new Error('Require SPZ v3 NGSP header');
  const count = raw.readUInt32LE(8), shDegree = raw[12], fractionalBits = raw[13], flags = raw[14];
  const rest = [0,9,24,45][shDegree];
  if (!count || rest === undefined || fractionalBits > 24 || (flags & ~1) !== 0 || raw[15] !== 0 || raw.length !== 16 + count * (20 + rest)) throw new Error('SPZ header/payload mismatch: '+JSON.stringify({count,shDegree,fractionalBits,flags,reserved:raw[15],length:raw.length,expected:16+count*(20+rest)}));
  return { count, shDegree, fractionalBits, flags, raw };
}

export function positionError(ply, source, target) {
  if (source.count !== target.count || source.shDegree !== target.shDegree) throw new Error('Gaussian count or SH degree changed');
  let maximum = 0, sum = 0;
  const step = 2 ** -target.fractionalBits;
  for (let i = 0; i < source.count; i++) for (let k = 0; k < 3; k++) {
    const j = 16 + (i * 3 + k) * 3;
    const value = target.raw.readIntLE(j,3) * step;
    const delta = Math.abs(value - ply.readFloatLE(source.offset+i*source.stride+source.axes[k]));
    maximum = Math.max(maximum,delta); sum += delta;
  }
  // Same ordering, axes, scale and translation. Quantization only, no coordinate conversion.
  if (maximum > step * 0.501 + 1e-7) throw new Error('Position quantization/coordinate preservation failed: ' + maximum);
  return { maxAbsoluteError:maximum, meanAbsoluteError:sum/(source.count*3), step, units:'arbitrary SfM units, not meters' };
}

export async function compressWorld(sourceDir, outputDir) {
  await mkdir(path.dirname(outputDir),{recursive:true});
  await mkdir(outputDir,{recursive:false});
  const report = { status:'RUNNING', startedAt:new Date().toISOString(), codec:'Spark 2.4.0 transcodeSpz CPU/WASM', visualQuality:'NOT RUN', browserRendering:'NOT RUN', retraining:false };
  const start = performance.now();
  try {
    const manifest = JSON.parse(await readFile(path.join(sourceDir,'world.json'),'utf8'));
    const asset = manifest.assets[0];
    if (asset.format !== 'ply' || asset.path !== path.basename(asset.path)) throw new Error('Require a local PLY asset');
    if (manifest.background) throw new Error('Require GS-only source');
    const ply = await readFile(path.join(sourceDir,asset.path)), source = inspectPly(ply);
    const fractionalBits = fractionalBitsFor(source);
    const { transcodeSpz } = await import('@sparkjsdev/spark');
    const before = performance.now();
    const result = await transcodeSpz({ inputs:[{fileBytes:new Uint8Array(ply),fileType:'ply',pathOrUrl:'scene.ply'}], maxSh:source.shDegree, fractionalBits, opacityThreshold:0, version:3 });
    const conversionSeconds = (performance.now()-before)/1000;
    const bytes = Buffer.from(result.fileBytes);
    await writeFile(path.join(outputDir,'scene.spz'),bytes,{flag:'wx'});
    const target = inspectSpz(bytes);
    if (target.fractionalBits !== fractionalBits) throw new Error('Position precision changed');
    const positions = positionError(ply,source,target);
    // Do not use Spark's clippedCount: this version returns a hard-coded zero.
    const converted = structuredClone(manifest);
    converted.id += '-spz'; converted.title += ' · SPZ';
    converted.assets[0] = {...asset,format:'spz',path:'scene.spz'};
    converted.provenance.notes += ' Storage-only SPZ v3 quantization with Spark 2.4.0; same Gaussian count and SH degree, identity raw-asset conversion, original coordinate transform and camera metadata retained. No retraining/pruning/background. Visual equivalence requires separate rendered comparison.';
    await writeFile(path.join(outputDir,'world.json'),JSON.stringify(converted,null,2)+'\n',{flag:'wx'});
    if (manifest.navigation.camerasPath) {
      if (manifest.navigation.camerasPath !== 'cameras.json') throw new Error('Require explicit cameras.json');
      await copyFile(path.join(sourceDir,'cameras.json'),path.join(outputDir,'cameras.json'));
    }
    await copyFile(path.join(sourceDir,'SOURCE_LICENSE'),path.join(outputDir,'SOURCE_LICENSE'));
    const gzipStart = performance.now(), gzip = gzipSync(ply,{level:6}), gzipSeconds = (performance.now()-gzipStart)/1000;
    Object.assign(report,{status:'PASS',source:{sha256:sha256(ply),bytes:ply.length,count:source.count,shDegree:source.shDegree,bounds:{min:source.min,max:source.max}},
      output:{sha256:sha256(bytes),bytes:bytes.length,count:target.count,shDegree:target.shDegree,version:3,fractionalBits,flags:target.flags},
      conversionSeconds,positions,reductionPercent:100*(1-bytes.length/ply.length),
      gzipControl:{bytes:gzip.length,seconds:gzipSeconds,roundtripSha256Matches:sha256(gunzipSync(gzip))===sha256(ply)},
      maxRssBytes:process.resourceUsage().maxRSS*1024,memoryMeaning:'Node process high-water RSS, includes runtime/validation/gzip; not GPU memory',
      coordinateMetadataUnchanged:JSON.stringify(manifest.coordinates)===JSON.stringify(converted.coordinates),
      navigationUnchanged:JSON.stringify(manifest.navigation)===JSON.stringify(converted.navigation)});
  } catch(error) { report.status='FAIL'; report.error=String(error.stack??error); }
  report.elapsedSeconds=(performance.now()-start)/1000; report.finishedAt=new Date().toISOString();
  await writeFile(path.join(outputDir,'compression.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  return report;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [source,output] = process.argv.slice(2);
  if (!source || !output) throw new Error('Usage: node scripts/compress-world.mjs SOURCE_WORLD NEW_WORLD');
  const report = await compressWorld(path.resolve(source),path.resolve(output));
  console.log(JSON.stringify(report,null,2)); if(report.status!=='PASS') process.exitCode=1;
}
