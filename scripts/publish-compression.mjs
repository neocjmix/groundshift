#!/usr/bin/env node
// Publish only the selected derivative and sanitized measurements, never raw inputs/logs.
import { readFile, writeFile, mkdir, copyFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { inspectSpz, sha256 } from './compress-world.mjs';

const [worldDir, evidencePath] = process.argv.slice(2);
if (!worldDir) throw new Error('Usage: publish-compression.mjs CONVERTED_WORLD [PUBLIC_EVIDENCE.json]');
const read = async p => JSON.parse(await readFile(p,'utf8'));
const write = async (p,v) => writeFile(p,JSON.stringify(v,null,2)+'\n');
const id='street-tangent20-spz', reportDir='experiments/compression';
const measurement=await read(path.join(worldDir,'compression.json'));
if (measurement.status!=='PASS') throw new Error('Require validated conversion');
const bytes=await readFile(path.join(worldDir,'scene.spz')), header=inspectSpz(bytes);
if (sha256(bytes)!==measurement.output.sha256 || header.count!==measurement.source.count || header.shDegree!==measurement.source.shDegree) throw new Error('Derivative integrity mismatch');
const manifest=await read(path.join(worldDir,'world.json'));
if (manifest.id!==id || manifest.background) throw new Error('Unexpected world or background');
const extra=evidencePath?await read(evidencePath):{};
// Retain local timing measurements without publishing loopback URLs/host paths.
if(extra.localBrowser)extra.localBrowser=extra.localBrowser.map(record=>({...record,origin:'local production preview; loopback address redacted'}));
const summary={schemaVersion:1,updatedAt:new Date().toISOString(),phase:evidencePath?'measured':'export',
  title:'같은 장면, 더 작은 파일',
  summary:`점 ${header.count.toLocaleString()}개와 SH${header.shDegree}를 유지한 저장 형식 비교. PLY ${(measurement.source.bytes/1e6).toFixed(2)}MB → SPZ ${(bytes.length/1e6).toFixed(2)}MB (${measurement.reductionPercent.toFixed(1)}% 절약). 재학습·점 제거·배경 보완 없음.`,
  measurement,...extra};
const serialized=JSON.stringify({manifest,summary});
if (/\/(?:Users|home|private|Volumes|tmp)\/|data\/jobs\/|file:\/\/|icloud\.com|https?:\/\/(?:localhost|127\.0\.0\.1)(?=[:/]|$)/i.test(serialized)) throw new Error('Private path or source in publication');
const dest=`public/worlds/${id}`, report=`public/${reportDir}`;
await mkdir(dest,{recursive:true});await mkdir(report,{recursive:true});
for (const name of ['world.json','cameras.json','SOURCE_LICENSE','scene.spz','preview.jpg']) {
  if (name==='scene.spz') {
    try {if(sha256(await readFile(path.join(dest,name)))!==measurement.output.sha256)throw new Error('Existing derivative would change');}
    catch(e){if(e.code!=='ENOENT')throw e;}
  }
  await copyFile(path.join(worldDir,name),path.join(dest,name));
}
await write(`${report}/summary.json`,summary);
await writeFile(`${report}/ATTRIBUTION.txt`,'Source photographs: Cicero101 / Mapillary via Wikimedia Commons, CC BY-SA 4.0. https://creativecommons.org/licenses/by-sa/4.0/\nDerivative: existing local Brush/Metal tangent20 Gaussian world, storage-only quantization to SPZ v3 by Spark 2.4.0. Comparative images are actual renders of this derivative and the preserved PLY, not new photographs. No original footage, panoramas, weights or raw logs published. SPZ and Spark upstream code: MIT.\n');
const quality=extra.conclusion??'변환·점 개수·SH·좌표 검사 PASS. 실제 브라우저 렌더·화질 비교 NOT RUN. 카드 그림은 임시 상태 표시.';
const catalog=await read('public/worlds/catalog.json');
const entry={id,title:'Street · SPZ 압축 비교',description:'같은 전방위 GS · 점 80만 개 · SH1 유지 · 파일 크기 78.3% 절약',category:'experiment',
  manifestPath:`/worlds/${id}/world.json`,thumbnailPath:`/worlds/${id}/preview.jpg`,createdAt:measurement.finishedAt,detail:quality};
catalog.scenes=catalog.scenes.filter(e=>e.id!==id);catalog.scenes.push(entry);await write('public/worlds/catalog.json',catalog);
const timeline=await read('public/experiments/lab/timeline.json');
const entries=[{id,kind:'scene',title:entry.title,description:entry.description,image:entry.thumbnailPath,href:'/?world='+entry.manifestPath,createdAt:entry.createdAt,detail:quality},
  {id:'report-compression',kind:'report',title:'SPZ · 같은 장면의 용량과 화질 비교',description:summary.summary,image:entry.thumbnailPath,href:'/experiments/compression/',createdAt:summary.updatedAt,detail:quality}];
timeline.entries=timeline.entries.filter(e=>!entries.some(n=>n.id===e.id));timeline.entries.push(...entries);await write('public/experiments/lab/timeline.json',timeline);
const allow=await read('scripts/observation-worlds.json');
allow.worlds=allow.worlds.filter(e=>e.id!==id);allow.worlds.push({id,source:path.relative(process.cwd(),path.resolve(worldDir)).replaceAll(path.sep,'/'),asset:'scene.spz',format:'spz',credits:['SOURCE_LICENSE']});
const reportFiles=(await readdir(report,{recursive:true})).filter(n=>/\.(json|txt|jpg|png|mp4)$/.test(n)).map(n=>`${reportDir}/${n}`);
allow.files=[...new Set([...allow.files,reportDir+'/index.html',...reportFiles])];await write('scripts/observation-worlds.json',allow);
console.log(JSON.stringify({world:dest,report,measurement:measurement.output,quality}));
