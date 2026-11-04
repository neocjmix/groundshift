#!/usr/bin/env node
// Curate a static upload, never send the repository/datasets to a hosting service.
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile, readdir, lstat, realpath } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseWorldManifest } from '../src/world.ts';
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

export function selectedWorlds(args) {
  if (args.some(arg => !Object.hasOwn(flags, arg))) {
    throw new Error('Usage: node scripts/package-viewer.mjs [--include-reconstruction] [--include-independent] [--include-desk]');
  }
  return ['sample', ...new Set(args.map(arg => flags[arg]))];
}

// World metadata must be publication-ready before packaging. This catches common
// accidental local references; it does not replace reviewing the selected scene.
function assertPublicMetadata(text, worldName) {
  if (/file:\/\/|\/Users\/|\/home\/|https?:\/\/(?:[a-z0-9-]+\.)*icloud\.com(?:[/:]|$)/iu.test(text)) {
    throw new Error(`Private source reference in public world metadata: ${worldName}`);
  }
}

export async function packageViewer({ root, output, worlds = ['sample'] }) {
  if (worlds.length === 0 || new Set(worlds).size !== worlds.length || worlds.some(name => !Object.hasOwn(worldFiles, name))) {
    throw new Error('Select only the explicitly curated worlds');
  }
  const sourceRoot = await realpath(root);
  const planned = [];

  // Reject both file and parent-directory symlinks; a safe-looking manifest path
  // must not escape into a dataset or another local directory through a symlink.
  async function ordinaryPath(relative, file = true) {
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
    return readFile(await ordinaryPath(relative));
  }

  async function add(source, destination = source.replace(/^dist\//u, 'www/')) {
    planned.push({ destination, bytes: await read(source) });
  }

  for (const name of ['index.html', 'favicon.svg', 'THIRD_PARTY_NOTICES.txt']) await add(`dist/${name}`);
  for (const name of (await readdir(await ordinaryPath('dist/assets', false))).sort()) {
    if (!/^[\w.-]+\.(js|css|wasm)$/u.test(name)) throw new Error(`Unexpected build asset: ${name}`);
    await add(`dist/assets/${name}`);
  }

  const catalog = parseSceneCatalog(JSON.parse((await read('dist/worlds/catalog.json')).toString('utf8')));
  const scenes = catalog.scenes.filter(scene => worlds.includes(scene.manifestPath.split('/')[2]));
  for (const worldName of worlds) {
    const entry = scenes.find(scene => scene.manifestPath === `/worlds/${worldName}/world.json`);
    if (!entry || entry.id !== worldName) throw new Error(`Missing matching catalog entry: ${worldName}`);
    const definition = worldFiles[worldName];
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
      planned.push({ destination: `www/worlds/${worldName}/${name}`, bytes });
    }
    for (const name of [definition.asset, 'preview.jpg']) await add(`${prefix}/${name}`);
  }
  const filteredCatalog = parseSceneCatalog({ version: 1, scenes });
  planned.push({ destination: 'www/worlds/catalog.json', bytes: Buffer.from(JSON.stringify(filteredCatalog, null, 2) + '\n') });
  for (const name of ['Dockerfile', 'Caddyfile']) await add(`deploy/${name}`, name);
  planned.push({ destination: '.dockerignore', bytes: Buffer.from('*\n!Dockerfile\n!Caddyfile\n!www\n!www/**\n') });

  // Preflight every input before creating a new, non-overwriting output directory.
  await mkdir(path.dirname(output), { recursive: true });
  await mkdir(output);
  const files = [];
  for (const { destination, bytes } of planned) {
    const target = path.join(output, destination);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, bytes, { flag: 'wx' });
    files.push({ path: destination, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') });
  }
  const totalBytes = files.reduce((sum, file) => sum + file.bytes, 0);
  const result = { output, fileCount: files.length, totalBytes, worlds: scenes.map(scene => scene.id) };
  // Inventory stays local, outside the directory sent to Railway.
  await writeFile(`${output}.inventory.json`, JSON.stringify({ ...result, files }, null, 2) + '\n', { flag: 'wx' });
  return result;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const result = await packageViewer({
    root,
    output: path.join(root, 'data', 'deploy', `viewer-${Date.now()}`),
    worlds: selectedWorlds(process.argv.slice(2)),
  });
  console.log(JSON.stringify(result, null, 2));
}
