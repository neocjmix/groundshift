#!/usr/bin/env node
// Curate a static upload, never send the repository/datasets to a hosting service.
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile, readdir, lstat, realpath, link } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseWorldManifest,parseStreamIndex,parsePagedIndex,parseRouteIndex } from '../src/world.ts';
import { parseBackground, parseBackgroundMesh } from '../src/background.ts';
import { parseSceneCatalog } from '../src/catalog.ts';

const worldFiles = {
  sample: { asset: 'plant.splat', format: 'splat', credits: ['ATTRIBUTION.md', 'upstream-LICENSE.txt', 'upstream-meta.json'] },
  reconstructed: { asset: 'scene.ply', format: 'ply', credits: ['SOURCE_LICENSE'] },
  independent: { asset: 'scene.ply', format: 'ply', credits: ['SOURCE_LICENSE'] },
  desk: { asset: 'scene.ply', format: 'ply', credits: ['SOURCE_LICENSE'] },
};
const flags = {
  '--include-reconstruction': 'reconstructed',
  '--include-independent': 'independent',
  '--include-desk': 'desk',
};
const observationReport = 'experiments/mapillary/index.html';

export function selectedWorlds(args) {
  if (args.some(arg => arg !== '--include-experiments' && !Object.hasOwn(flags, arg))) {
    throw new Error('Usage: node scripts/package-viewer.mjs [--include-reconstruction] [--include-independent] [--include-desk] [--include-experiments]');
  }
  return ['sample', ...new Set(args.filter(arg => Object.hasOwn(flags, arg)).map(arg => flags[arg]))];
}

function relativePath(value) {
  if (typeof value !== 'string' || !value.split('/').every(piece => /^[a-zA-Z0-9][a-zA-Z0-9._-]*$/u.test(piece))) {
    throw new Error('Invalid package source path');
  }
  return value;
}

// This is an explicit publication list, not a directory to walk. The source
// records where a world was produced; packaging only reads reviewed dist files.
export function parseObservationSpec(value) {
  if (!value || value.version !== 1 || !Array.isArray(value.worlds) || !Array.isArray(value.files)
    || Object.keys(value).some(key => !['version', 'worlds', 'files'].includes(key))) {
    throw new Error('Invalid observation publication specification');
  }
  const ids = new Set(Object.keys(worldFiles));
  for (const world of value.worlds) {
    if (!world || Object.keys(world).some(key => !['id', 'source', 'asset', 'format', 'credits'].includes(key))
      || typeof world.id !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/u.test(world.id) || ids.has(world.id)) {
      throw new Error('Invalid or duplicate observation world identifier');
    }
    ids.add(world.id);
    relativePath(world.source);
    if (!/^data\/jobs\/.+\/world$/u.test(world.source)) throw new Error('Observation source must identify a local job world');
    relativePath(world.asset);
    if (!['ply', 'splat', 'spz'].includes(world.format) || world.asset.includes('/') || !world.asset.endsWith(`.${world.format}`)) {
      throw new Error('Invalid observation scene asset');
    }
    if (!Array.isArray(world.credits) || new Set(world.credits).size !== world.credits.length) {
      throw new Error('Invalid or duplicate observation credits');
    }
    for (const credit of world.credits) {
      relativePath(credit);
      if (!/^(?:SOURCE_LICENSE|LICENSE|[\w.-]+\.(?:txt|md|json))$/u.test(credit)
        || ['world.json', 'cameras.json'].includes(credit)) throw new Error('Invalid observation credit filename');
    }
  }
  if (new Set(value.files).size !== value.files.length) throw new Error('Duplicate observation report path');
  for (const file of value.files) {
    relativePath(file);
    if (!/^experiments\/[a-z0-9]+(?:-[a-z0-9]+)*\/.+\.(?:html|css|js|json|txt|md|png|jpg|jpeg|webp|svg|mp4|ply)$/u.test(file)) {
      throw new Error('Observation reports must use explicit public experiment files');
    }
  }
  if (value.worlds.length && !value.files.includes(observationReport)) {
    throw new Error('Observation worlds require their linked public report');
  }
  return value;
}

// World metadata must be publication-ready before packaging. This catches common
// accidental local references; it does not replace reviewing the selected scene.
function assertPublicMetadata(text, worldName) {
  if (/file:\/\/|\/(?:Users|home|private|Volumes|tmp)\/|\bdata\/jobs\/|[a-z]:\\|https?:\/\/(?:localhost|127\.0\.0\.1|\[::1\])(?=[/:]|$)|https?:\/\/(?:[a-z0-9-]+\.)*icloud\.com(?:[/:]|$)/iu.test(text)) {
    throw new Error(`Private source reference in public world metadata: ${worldName}`);
  }
}

export async function packageViewer({ root, output, worlds = ['sample'], includeExperiments = false, observationSpec, reuseInventory }) {
  if (worlds.length === 0 || new Set(worlds).size !== worlds.length || worlds.some(name => !Object.hasOwn(worldFiles, name))) {
    throw new Error('Select only the explicitly curated worlds');
  }
  const sourceRoot = await realpath(root);
  const reuse = reuseInventory ? JSON.parse(await readFile(reuseInventory, 'utf8')) : null;
  const reusable = new Map((reuse?.files ?? []).map(item => [item.path, item]));
  const planned = [];
  // Weak keys do not retain input buffers. After preflight, keep only the source
  // path/content pin; reread one file at a time when writing the frozen package.
  const readSources = new WeakMap();
  const destinations = new Set();
  function plan(destination, bytes) {
    if (destinations.has(destination)) throw new Error(`Duplicate package destination: ${destination}`);
    destinations.add(destination);
    const record = { path: destination, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
    const source = readSources.get(bytes);
    planned.push({ destination, record, ...(source ? { source } : { bytes }) });
  }

  // Reject both file and parent-directory symlinks; a safe-looking manifest path
  // must not escape into a dataset or another local directory through a symlink.
  async function ordinaryPath(relative, file = true) {
    relativePath(relative);
    const pieces = relative.split('/');
    if (pieces.some(piece => !piece || piece === '.' || piece === '..')) throw new Error('Invalid package source path');
    let current = sourceRoot;
    for (const [index, piece] of pieces.entries()) {
      current = path.join(current, piece);
      const stat = await lstat(current);
      const expectedFile = file && index === pieces.length - 1;
      if (stat.isSymbolicLink() || (expectedFile ? !stat.isFile() : !stat.isDirectory())) {
        throw new Error(`Only ordinary files and directories may be deployed: ${relative}`);
      }
    }
    return current;
  }

  async function read(relative) {
    const bytes = await readFile(await ordinaryPath(relative));
    readSources.set(bytes, relative);
    return bytes;
  }

  async function add(source, destination = source.replace(/^dist\//u, 'www/')) {
    plan(destination, await read(source));
  }

  const observations = includeExperiments
    ? parseObservationSpec(observationSpec ?? JSON.parse((await read('scripts/observation-worlds.json')).toString('utf8')))
    : { worlds: [], files: [] };
  const definitions = { ...worldFiles, ...Object.fromEntries(observations.worlds.map(world => [world.id, world])) };
  const selected = [...worlds, ...observations.worlds.map(world => world.id)];

  for (const name of ['index.html', 'favicon.svg', 'THIRD_PARTY_NOTICES.txt']) await add(`dist/${name}`);
  for (const name of (await readdir(await ordinaryPath('dist/assets', false))).sort()) {
    if (!/^[\w.-]+\.(js|css|wasm)$/u.test(name)) throw new Error(`Unexpected build asset: ${name}`);
    await add(`dist/assets/${name}`);
  }

  const catalog = parseSceneCatalog(JSON.parse((await read('dist/worlds/catalog.json')).toString('utf8')));
  const scenes = catalog.scenes.filter(scene => selected.includes(scene.manifestPath.split('/')[2]));
  assertPublicMetadata(JSON.stringify(scenes), 'scene catalog');
  for (const worldName of selected) {
    const entry = scenes.find(scene => scene.manifestPath === `/worlds/${worldName}/world.json`);
    if (!entry || entry.id !== worldName) throw new Error(`Missing matching catalog entry: ${worldName}`);
    if (!Object.hasOwn(worldFiles, worldName) && entry.category !== 'experiment') {
      throw new Error(`Observation world must be labeled as an experiment: ${worldName}`);
    }
    const definition = definitions[worldName];
    const prefix = `dist/worlds/${worldName}`;
    const manifestText = (await read(`${prefix}/world.json`)).toString('utf8');
    const manifest = parseWorldManifest(JSON.parse(manifestText));
    if ([manifest.provenance.sourceUrl, manifest.provenance.licenseUrl].some(url => new URL(url).protocol !== 'https:')) {
      throw new Error(`Public deployment requires public HTTPS provenance: ${worldName}`);
    }
    assertPublicMetadata(manifestText, worldName);
    if (manifest.assets[0].path !== definition.asset || manifest.assets[0].format !== definition.format) {
      throw new Error(`Unexpected scene asset for curated world: ${worldName}`);
    }
    if (manifest.navigation.camerasPath && manifest.navigation.camerasPath !== 'cameras.json') {
      throw new Error(`Unexpected camera metadata filename: ${worldName}`);
    }
    const metadata = ['world.json', ...definition.credits];
    if (manifest.navigation.camerasPath) metadata.push('cameras.json');
    for (const name of metadata) {
      const bytes = await read(`${prefix}/${name}`);
      assertPublicMetadata(bytes.toString('utf8'), worldName);
      plan(`www/worlds/${worldName}/${name}`, bytes);
    }
    if (manifest.background) {
      const name = manifest.background.path;
      relativePath(name);
      const backgroundBytes = await read(`${prefix}/${name}`);
      assertPublicMetadata(backgroundBytes.toString('utf8'), worldName);
      const background = parseBackground(JSON.parse(backgroundBytes.toString('utf8')));
      plan(`www/worlds/${worldName}/${name}`, backgroundBytes);
      const base = path.posix.dirname(name);
      const selectedBackgrounds = new Set();
      for (const view of background.views) for (const key of ['imagePath', 'meshPath']) {
        if (!view[key]) continue;
        const file = path.posix.join(base, relativePath(view[key]));
        if (selectedBackgrounds.has(file)) continue;
        selectedBackgrounds.add(file);
        if (key === 'imagePath' && !/\.(?:png|jpg|jpeg|webp)$/u.test(file)) throw new Error('Unexpected public background image');
        if (key === 'meshPath' && !file.endsWith('.json')) throw new Error('Unexpected public background mesh');
        const bytes = await read(`${prefix}/${file}`);
        if (key === 'meshPath') {
          assertPublicMetadata(bytes.toString('utf8'), worldName);
          parseBackgroundMesh(JSON.parse(bytes.toString('utf8')));
        }
        plan(`www/worlds/${worldName}/${file}`, bytes);
      }
    }
    for (const name of [definition.asset, 'preview.jpg']) await add(`${prefix}/${name}`);
    if(manifest.streaming){
      const name=relativePath(manifest.streaming.path),bytes=await read(`${prefix}/${name}`);
      assertPublicMetadata(bytes.toString('utf8'),worldName);
      const index=parseStreamIndex(JSON.parse(bytes.toString('utf8'))),base=path.posix.dirname(name);
      if(manifest.assets[0].format!=='spz')throw new Error('Spatial chunks require an SPZ control');
      plan(`www/worlds/${worldName}/${name}`,bytes);
      for(const chunk of index.chunks){
        const file=path.posix.join(base,relativePath(chunk.path));
        if(!file.endsWith('.spz'))throw new Error('Only declared SPZ chunks can be packaged');
        const data=await read(`${prefix}/${file}`);
        if(data.length!==chunk.bytes||createHash('sha256').update(data).digest('hex')!==chunk.sha256)throw new Error('Spatial chunk integrity mismatch');
        plan(`www/worlds/${worldName}/${file}`,data);
      }
    }
    if(manifest.paging){
      const name=relativePath(manifest.paging.path),bytes=await read(`${prefix}/${name}`);assertPublicMetadata(bytes.toString('utf8'),worldName);
      const index=parsePagedIndex(JSON.parse(bytes.toString('utf8'))),base=path.posix.dirname(name);plan(`www/worlds/${worldName}/${name}`,bytes);
      for(const f of index.files){const file=path.posix.join(base,relativePath(f.path));if(!/\.(rad|radc)$/.test(file))throw new Error('Unexpected native LoD asset');const data=await read(`${prefix}/${file}`);if(data.length!==f.bytes||createHash('sha256').update(data).digest('hex')!==f.sha256)throw new Error('Native LoD integrity mismatch');plan(`www/worlds/${worldName}/${file}`,data);}
    }
    if(manifest.route){
      const name=relativePath(manifest.route.path),bytes=await read(`${prefix}/${name}`);
      assertPublicMetadata(bytes.toString('utf8'),worldName);
      const index=parseRouteIndex(JSON.parse(bytes.toString('utf8'))),base=path.posix.dirname(name);
      plan(`www/worlds/${worldName}/${name}`,bytes);
      for(const segment of index.segments){
        const segmentFile=path.posix.join(base,relativePath(segment.world)),segmentBase=path.posix.dirname(segmentFile);
        const manifestBytes=await read(`${prefix}/${segmentFile}`);assertPublicMetadata(manifestBytes.toString('utf8'),segment.id);
        const child=parseWorldManifest(JSON.parse(manifestBytes.toString('utf8')));
        if(child.route||child.streaming||!child.paging||child.assets[0].format!=='spz'||child.coordinates.unit!==manifest.coordinates.unit)throw new Error('Route segments require standalone RAD/SPZ worlds in matching units');
        if([child.provenance.sourceUrl,child.provenance.licenseUrl].some(url=>new URL(url).protocol!=='https:'))throw new Error('Route segment provenance must use public HTTPS');
        plan(`www/worlds/${worldName}/${segmentFile}`,manifestBytes);
        const metadata=['SOURCE_LICENSE',...(child.navigation.camerasPath?[relativePath(child.navigation.camerasPath)]:[])];
        for(const file of metadata){const data=await read(`${prefix}/${segmentBase}/${file}`);assertPublicMetadata(data.toString('utf8'),segment.id);plan(`www/worlds/${worldName}/${segmentBase}/${file}`,data);}
        const asset=path.posix.join(segmentBase,relativePath(child.assets[0].path));
        if(!asset.endsWith('.spz'))throw new Error('Route segment control must be SPZ');
        const assetBytes=await read(`${prefix}/${asset}`),destination=`www/worlds/${worldName}/${asset}`;
        if(destinations.has(destination)){if(planned.find(p=>p.destination===destination)?.record.sha256!==createHash('sha256').update(assetBytes).digest('hex'))throw new Error('Conflicting route control asset');}
        else plan(destination,assetBytes);
        const pagedFile=path.posix.join(segmentBase,relativePath(child.paging.path)),pagedBytes=await read(`${prefix}/${pagedFile}`);
        assertPublicMetadata(pagedBytes.toString('utf8'),segment.id);
        const paged=parsePagedIndex(JSON.parse(pagedBytes.toString('utf8')));plan(`www/worlds/${worldName}/${pagedFile}`,pagedBytes);
        for(const file of paged.files){
          const relative=path.posix.join(path.posix.dirname(pagedFile),relativePath(file.path));
          if(!/\.(rad|radc)$/.test(relative))throw new Error('Unexpected route LoD asset');
          const data=await read(`${prefix}/${relative}`);
          if(data.length!==file.bytes||createHash('sha256').update(data).digest('hex')!==file.sha256)throw new Error('Route LoD integrity mismatch');
          plan(`www/worlds/${worldName}/${relative}`,data);
        }
      }
    }
  }
  for (const file of observations.files) {
    const bytes = await read(`dist/${file}`);
    if (/\.(?:html|css|js|json|txt|md|svg)$/u.test(file)) assertPublicMetadata(bytes.toString('utf8'), file);
    plan(`www/${file}`, bytes);
  }
  const filteredCatalog = parseSceneCatalog({ version: 1, scenes });
  plan('www/worlds/catalog.json', Buffer.from(JSON.stringify(filteredCatalog, null, 2) + '\n'));
  for (const name of ['Dockerfile', 'Caddyfile']) await add(`deploy/${name}`, name);
  plan('.dockerignore', Buffer.from('*\n!Dockerfile\n!Caddyfile\n!www\n!www/**\n'));

  // Preflight every input before creating a new, non-overwriting output directory.
  await mkdir(path.dirname(output), { recursive: true });
  await mkdir(output);
  const files = [];
  let reusedFiles = 0;
  let reusedBytes = 0;
  for (const { destination, record, source, bytes: generatedBytes } of planned) {
    const target = path.join(output, destination);
    await mkdir(path.dirname(target), { recursive: true });
    const old = reusable.get(destination);
    if (old?.bytes === record.bytes && old.sha256 === record.sha256) {
      const previous = path.join(reuse.output, destination);
      const actual = await realpath(previous);
      const base = await realpath(reuse.output);
      if (!actual.startsWith(base + path.sep) || !(await lstat(previous)).isFile()
        || (await lstat(previous)).isSymbolicLink()
        || createHash('sha256').update(await readFile(previous)).digest('hex') !== record.sha256) {
        throw new Error('Reusable package integrity mismatch');
      }
      await link(previous, target);
      reusedFiles++;
      reusedBytes += record.bytes;
    } else {
      const bytes = source ? await read(source) : generatedBytes;
      if (bytes.length !== record.bytes || createHash('sha256').update(bytes).digest('hex') !== record.sha256) {
        throw new Error('Package source changed after preflight');
      }
      await writeFile(target, bytes, { flag: 'wx' });
    }
    files.push(record);
  }
  const totalBytes = files.reduce((sum, file) => sum + file.bytes, 0);
  const result = { output, fileCount: files.length, totalBytes, worlds: scenes.map(scene => scene.id), reusedFiles, reusedBytes,
    retainedGeneratedBufferBytes: planned.reduce((sum, item) => sum + (item.bytes?.length ?? 0), 0),
    sourceFilesPinnedWithoutRetainedBuffers: planned.filter(item => item.source).length };
  // Inventory stays local, outside the directory sent to Railway.
  await writeFile(`${output}.inventory.json`, JSON.stringify({ ...result, files }, null, 2) + '\n', { flag: 'wx' });
  return result;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const reuseIndex = args.indexOf('--reuse-inventory');
  const reuseInventory = reuseIndex < 0 ? undefined : args.splice(reuseIndex, 2)[1];
  if (reuseIndex >= 0 && !reuseInventory) throw new Error('Missing reuse inventory path');
  const root = fileURLToPath(new URL('../', import.meta.url));
  const result = await packageViewer({
    root,
    output: path.join(root, 'data', 'deploy', `viewer-${Date.now()}`),
    worlds: selectedWorlds(args),
    includeExperiments: args.includes('--include-experiments'),
    reuseInventory,
  });
  console.log(JSON.stringify(result, null, 2));
}
