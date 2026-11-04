#!/usr/bin/env node
// Curate a static upload, never send the repository/datasets to a hosting service.
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile, copyFile, readdir, lstat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseWorldManifest } from '../src/world.ts';

const root = fileURLToPath(new URL('../', import.meta.url));
const includeReconstruction = process.argv.includes('--include-reconstruction');
if (process.argv.slice(2).some(arg => arg !== '--include-reconstruction')) {
  throw new Error('Usage: node scripts/package-viewer.mjs [--include-reconstruction]');
}
const output = path.join(root, 'data', 'deploy', `viewer-${Date.now()}`);
const www = path.join(output, 'www');
const files = [];
await mkdir(www, { recursive: true });

async function copy(source, destination) {
  if (!(await lstat(source)).isFile()) throw new Error(`Only ordinary files may be deployed: ${source}`);
  const bytes = await readFile(source);
  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(source, destination);
  files.push({ path: path.relative(output, destination), bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') });
}

for (const filename of ['index.html', 'favicon.svg', 'THIRD_PARTY_NOTICES.txt']) {
  await copy(path.join(root, 'dist', filename), path.join(www, filename));
}
for (const filename of await readdir(path.join(root, 'dist/assets'))) {
  if (!/^[\w.-]+\.(js|css|wasm)$/.test(filename)) throw new Error(`Unexpected build asset: ${filename}`);
  await copy(path.join(root, 'dist/assets', filename), path.join(www, 'assets', filename));
}

for (const worldName of includeReconstruction ? ['sample', 'reconstructed'] : ['sample']) {
  const source = path.join(root, 'dist/worlds', worldName);
  const manifest = parseWorldManifest(JSON.parse(await readFile(path.join(source, 'world.json'), 'utf8')));
  if ([manifest.provenance.sourceUrl, manifest.provenance.licenseUrl].some(url => !url.startsWith('https://'))) {
    throw new Error(`Public deployment requires public HTTPS provenance: ${worldName}`);
  }
  const names = new Set(['world.json', manifest.assets[0].path]);
  if (manifest.navigation.camerasPath) names.add(manifest.navigation.camerasPath);
  const credits = worldName === 'sample' ? ['ATTRIBUTION.md', 'upstream-LICENSE.txt', 'upstream-meta.json'] : ['SOURCE_LICENSE'];
  for (const name of [...names, ...credits]) await copy(path.join(source, name), path.join(www, 'worlds', worldName, name));
}
// Configure the Railway service directly; legacy railway.json/toml is deprecated.
for (const name of ['Dockerfile', 'Caddyfile']) {
  await copy(path.join(root, 'deploy', name), path.join(output, name));
}
await writeFile(path.join(output, '.dockerignore'), '*\n!Dockerfile\n!Caddyfile\n!www\n!www/**\n');
// Inventory stays local; Railway needs only the curated files in this directory.
await writeFile(`${output}.inventory.json`, JSON.stringify({ output, files, totalBytes: files.reduce((sum, file) => sum + file.bytes, 0) }, null, 2) + '\n');
console.log(JSON.stringify({ output, fileCount: files.length, totalBytes: files.reduce((sum, file) => sum + file.bytes, 0), worlds: includeReconstruction ? ['sample', 'reconstructed'] : ['sample'] }, null, 2));
