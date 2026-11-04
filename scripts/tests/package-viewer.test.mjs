import { afterEach, describe, expect, it } from 'vitest';
import { mkdtemp, mkdir, readFile, writeFile, rm, symlink, rename, access } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { packageViewer, selectedWorlds } from '../package-viewer.mjs';

const temporary = [];
afterEach(async () => { await Promise.all(temporary.splice(0).map(root => rm(root, { recursive: true, force: true }))); });

// Synthetic packaging inputs prove only the filesystem publication boundary.
async function fixture() {
  const root = await mkdtemp(path.join(os.tmpdir(), 'groundshift-package-test-'));
  temporary.push(root);
  async function put(name, value) {
    await mkdir(path.dirname(path.join(root, name)), { recursive: true });
    await writeFile(path.join(root, name), typeof value === 'object' ? JSON.stringify(value) : value);
  }
  for (const name of ['index.html', 'favicon.svg', 'THIRD_PARTY_NOTICES.txt', 'assets/index-abc.js', 'assets/index-abc.css']) await put(`dist/${name}`, 'synthetic build');
  for (const name of ['Dockerfile', 'Caddyfile']) await put(`deploy/${name}`, 'synthetic config');
  const catalog = { version: 1, scenes: [] };
  const manifests = {};
  for (const world of ['desk', 'independent', 'reconstructed', 'sample']) {
    catalog.scenes.push({ id: world, title: world, description: 'Synthetic fixture', category: world === 'sample' ? 'sample' : 'reconstruction', manifestPath: `/worlds/${world}/world.json`, thumbnailPath: `/worlds/${world}/preview.jpg`, detail: 'No rendering claim' });
    const asset = world === 'sample' ? 'plant.splat' : 'scene.ply';
    manifests[world] = {
      schemaVersion: 1, id: world, title: world,
      assets: [{ kind: 'gaussian-splat', format: world === 'sample' ? 'splat' : 'ply', path: asset }],
      coordinates: { handedness: 'right', upAxis: 'y', unit: 'arbitrary', assetToWorld: { position: [0, 0, 0], quaternion: [0, 0, 0, 1], scale: 1 } },
      navigation: { mode: 'orbit', camera: { position: [0, 0, 2], target: [0, 0, 0], up: [0, 1, 0], fov: 50, near: 0.01, far: 100 } },
      provenance: { sourceType: 'sample', sourceUrl: 'https://example.com/source', license: 'Synthetic test only', licenseUrl: 'https://example.com/license', attribution: 'Test fixture', backend: 'none' },
    };
    if (world !== 'sample') manifests[world].navigation.camerasPath = 'cameras.json';
    await put(`dist/worlds/${world}/world.json`, manifests[world]);
    const names = [asset, 'preview.jpg', ...(world === 'sample' ? ['ATTRIBUTION.md', 'upstream-LICENSE.txt', 'upstream-meta.json'] : ['SOURCE_LICENSE', 'cameras.json'])];
    for (const name of names) await put(`dist/worlds/${world}/${name}`, `synthetic ${name}`);
    await put(`dist/worlds/${world}/private-source.mov`, 'must never be deployed');
  }
  await put('dist/worlds/catalog.json', catalog);
  await put('dist/unrelated-private.txt', 'must never be deployed');
  const output = path.join(root, 'output');
  return { root, output, put, catalog, manifests };
}

describe('curated viewer packaging', () => {
  it('defaults to only the sample, filters discovery and excludes arbitrary files', async () => {
    const { root, output } = await fixture();
    const result = await packageViewer({ root, output });
    expect(result.worlds).toEqual(['sample']);
    const catalog = JSON.parse(await readFile(path.join(output, 'www/worlds/catalog.json'), 'utf8'));
    expect(catalog.scenes.map(scene => scene.id)).toEqual(['sample']);
    const inventory = JSON.parse(await readFile(`${output}.inventory.json`, 'utf8'));
    expect(inventory.files.some(file => file.path.endsWith('preview.jpg'))).toBe(true);
    expect(inventory.files.some(file => /private|desk|independent|reconstructed/.test(file.path))).toBe(false);
    expect(inventory.files.every(file => /^[a-f0-9]{64}$/.test(file.sha256))).toBe(true);
    await expect(access(path.join(output, 'www/unrelated-private.txt'))).rejects.toThrow();
  });

  it('includes explicitly selected worlds, previews and credits in catalog order', async () => {
    const { root, output } = await fixture();
    const result = await packageViewer({ root, output, worlds: selectedWorlds(['--include-reconstruction', '--include-independent', '--include-desk']) });
    expect(result.worlds).toEqual(['desk', 'independent', 'reconstructed', 'sample']);
    for (const world of result.worlds) {
      expect(await readFile(path.join(output, `www/worlds/${world}/preview.jpg`), 'utf8')).toBe('synthetic preview.jpg');
      if (world !== 'sample') expect(await readFile(path.join(output, `www/worlds/${world}/SOURCE_LICENSE`), 'utf8')).toBe('synthetic SOURCE_LICENSE');
    }
  });

  it('rejects unknown selection and flags', () => {
    expect(() => selectedWorlds(['--include-everything'])).toThrow('Usage');
    expect(selectedWorlds(['--include-desk', '--include-desk'])).toEqual(['sample', 'desk']);
  });

  it('requires a real preview before creating output', async () => {
    const { root, output } = await fixture();
    await rm(path.join(root, 'dist/worlds/sample/preview.jpg'));
    await expect(packageViewer({ root, output })).rejects.toThrow();
    await expect(access(output)).rejects.toThrow();
  });

  it('rejects manifest references to arbitrary files even within a selected world', async () => {
    const { root, output, put, manifests } = await fixture();
    manifests.sample.assets[0].path = 'private-source.mov';
    await put('dist/worlds/sample/world.json', manifests.sample);
    await expect(packageViewer({ root, output })).rejects.toThrow('Unexpected scene asset');
  });

  it('rejects local provenance and accidental local references in metadata', async () => {
    const { root, output, put, manifests } = await fixture();
    manifests.sample.provenance.sourceUrl = 'file:///private/capture.mov';
    await put('dist/worlds/sample/world.json', manifests.sample);
    await expect(packageViewer({ root, output })).rejects.toThrow('public HTTPS');
    manifests.sample.provenance.sourceUrl = 'https://example.com/source';
    manifests.sample.provenance.notes = 'Source at /Users/person/private/capture.mov';
    await put('dist/worlds/sample/world.json', manifests.sample);
    await expect(packageViewer({ root, output })).rejects.toThrow('Private source reference');
    manifests.sample.provenance.notes = 'Shared capture: https://share.icloud.com/photos/synthetic-private-reference';
    await put('dist/worlds/sample/world.json', manifests.sample);
    await expect(packageViewer({ root, output })).rejects.toThrow('Private source reference');
  });

  it.each(['file', 'directory'])('rejects %s symlinks within a selected world', async kind => {
    const { root, output } = await fixture();
    const target = path.join(root, kind === 'file' ? 'dist/worlds/sample/plant.splat' : 'dist/worlds/sample');
    const saved = path.join(root, `saved-${kind}`);
    await rename(target, saved);
    await symlink(saved, target, kind === 'file' ? 'file' : 'dir');
    await expect(packageViewer({ root, output })).rejects.toThrow('Only ordinary');
  });

  it('rejects an absent catalog entry and an unexpected build asset', async () => {
    const { root, output, put, catalog } = await fixture();
    catalog.scenes = catalog.scenes.filter(scene => scene.id !== 'sample');
    await put('dist/worlds/catalog.json', catalog);
    await expect(packageViewer({ root, output })).rejects.toThrow('Missing matching catalog entry');
    await put('dist/assets/source.mov', 'not a build asset');
    await expect(packageViewer({ root, output })).rejects.toThrow('Unexpected build asset');
  });

  it('never overwrites an existing package', async () => {
    const { root, output } = await fixture();
    await mkdir(output);
    await writeFile(path.join(output, 'keep.txt'), 'preserve');
    await expect(packageViewer({ root, output })).rejects.toThrow();
    expect(await readFile(path.join(output, 'keep.txt'), 'utf8')).toBe('preserve');
  });
});
