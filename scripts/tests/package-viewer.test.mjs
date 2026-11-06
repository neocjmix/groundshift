import { afterEach, describe, expect, it } from 'vitest';
import { mkdtemp, mkdir, readFile, writeFile, rm, symlink, rename, access } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { packageViewer, selectedWorlds, parseObservationSpec } from '../package-viewer.mjs';

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

async function observationFixture() {
  const setup = await fixture();
  const { put, catalog, manifests } = setup;
  const world = 'observed-trial';
  const spec = {
    version: 1,
    worlds: [{ id: world, source: 'data/jobs/observed-trial/world', asset: 'scene.ply', format: 'ply', credits: ['SOURCE_LICENSE'] }],
    files: ['experiments/mapillary/index.html', 'experiments/mapillary/comparison.png', 'experiments/mapillary/results.json', 'experiments/mapillary/clip.mp4'],
  };
  const manifest = structuredClone(manifests.independent);
  manifest.id = world;
  manifest.title = 'Observation fixture';
  catalog.scenes.push({ ...catalog.scenes[1], id: world, title: 'Observation fixture', category: 'experiment', manifestPath: `/worlds/${world}/world.json`, thumbnailPath: `/worlds/${world}/preview.jpg` });
  await put(`dist/worlds/${world}/world.json`, manifest);
  for (const name of ['scene.ply', 'cameras.json', 'preview.jpg', 'SOURCE_LICENSE']) await put(`dist/worlds/${world}/${name}`, `synthetic ${name}`);
  await put('dist/worlds/catalog.json', catalog);
  await put('dist/experiments/mapillary/index.html', '<html><img src="comparison.png"><p>Quality FAIL; execution PASS.</p></html>');
  await put('dist/experiments/mapillary/comparison.png', 'synthetic comparison image, not pixel evidence');
  await put('dist/experiments/mapillary/results.json', { status: 'FAIL', notes: 'Fixture status only' });
  await put('dist/experiments/mapillary/clip.mp4', 'synthetic media fixture');
  await put('dist/experiments/mapillary/private.log', 'do not publish');
  await put('dist/experiments/mapillary/unlisted.png', 'do not publish');
  await put(`dist/worlds/${world}/job.json`, { source: '/Users/person/private.mov' });
  await put('scripts/observation-worlds.json', spec);
  return { ...setup, spec, manifest, world };
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
    expect(selectedWorlds(['--include-experiments', '--include-desk'])).toEqual(['sample', 'desk']);
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

describe('explicit observation packaging', () => {
  it('packages only explicitly allowed point-cloud downloads without treating them as GS worlds', async () => {
    const { root, output, spec, put } = await observationFixture();
    const name = 'experiments/panoramic-depth/cloud.ply';
    spec.files.push(name);
    await put('dist/' + name, 'ply\nformat ascii 1.0\nelement vertex 0\nend_header\n');
    await put('dist/experiments/panoramic-depth/unlisted.ply', 'private unlisted fixture');
    await packageViewer({ root, output, includeExperiments: true, observationSpec: spec });
    expect(await readFile(path.join(output, 'www', name), 'utf8')).toContain('element vertex 0');
    await expect(access(path.join(output, 'www/experiments/panoramic-depth/unlisted.ply'))).rejects.toThrow();
  });

  it('adds all listed experimental worlds and only explicitly listed comparison files', async () => {
    const { root, output, world } = await observationFixture();
    const result = await packageViewer({ root, output, includeExperiments: true });
    expect(result.worlds).toEqual(['sample', world]);
    const inventory = JSON.parse(await readFile(`${output}.inventory.json`, 'utf8'));
    const paths = inventory.files.map(file => file.path);
    expect(paths).toContain(`www/worlds/${world}/scene.ply`);
    expect(paths).toContain('www/experiments/mapillary/index.html');
    expect(paths).toContain('www/experiments/mapillary/comparison.png');
    expect(paths).toContain('www/experiments/mapillary/results.json');
    expect(paths).toContain('www/experiments/mapillary/clip.mp4');
    expect(paths.some(file => /private|job\.json|unlisted|data\/jobs|observation-worlds\.json/u.test(file))).toBe(false);
    const catalog = JSON.parse(await readFile(path.join(output, 'www/worlds/catalog.json'), 'utf8'));
    expect(catalog.scenes.some(scene => scene.category === 'experiment')).toBe(true);
  });

  it('omits experimental discovery and reports from a reduced package', async () => {
    const { root, output } = await observationFixture();
    const result = await packageViewer({ root, output });
    expect(result.worlds).toEqual(['sample']);
    const catalog = JSON.parse(await readFile(path.join(output, 'www/worlds/catalog.json'), 'utf8'));
    expect(catalog.scenes.some(scene => scene.category === 'experiment')).toBe(false);
    await expect(access(path.join(output, 'www/experiments'))).rejects.toThrow();
  });

  it('requires the report linked by experimental catalog entries', async () => {
    const { root, output, spec } = await observationFixture();
    spec.files = spec.files.filter(file => !file.endsWith('/index.html'));
    await expect(packageViewer({ root, output, includeExperiments: true, observationSpec: spec })).rejects.toThrow('linked public report');
  });

  it('requires explicit experimental labeling for observation worlds', async () => {
    const { root, output, catalog, put } = await observationFixture();
    catalog.scenes.at(-1).category = 'reconstruction';
    await put('dist/worlds/catalog.json', catalog);
    await expect(packageViewer({ root, output, includeExperiments: true })).rejects.toThrow('labeled as an experiment');
  });

  it('supports an injected specification without reading a job source', async () => {
    const { root, output, spec } = await observationFixture();
    await rm(path.join(root, 'scripts/observation-worlds.json'));
    await expect(packageViewer({ root, output, includeExperiments: true, observationSpec: spec })).resolves.toMatchObject({ worlds: ['sample', 'observed-trial'] });
  });

  it.each([
    '/experiments/mapillary/index.html',
    'experiments/mapillary/../private.json',
    'experiments/mapillary/./index.html',
    'experiments/mapillary/secret.log',
    'experiments/mapillary/footage.mov',
    'experiments/mapillary/%2e%2e/private.json',
    'experiments/mapillary\\private.json',
    'worlds/sample/world.json',
  ])('rejects unsafe or out-of-scope report path %s', async file => {
    const { root, output, spec } = await observationFixture();
    spec.files = [file];
    await expect(packageViewer({ root, output, includeExperiments: true, observationSpec: spec })).rejects.toThrow();
    await expect(access(output)).rejects.toThrow();
  });

  it('rejects duplicate report paths and duplicate or reserved world identifiers', async () => {
    const { spec } = await observationFixture();
    expect(() => parseObservationSpec({ ...spec, files: [...spec.files, spec.files[0]] })).toThrow('Duplicate observation report path');
    expect(() => parseObservationSpec({ ...spec, worlds: [...spec.worlds, spec.worlds[0]] })).toThrow('duplicate observation world identifier');
    expect(() => parseObservationSpec({ ...spec, worlds: [{ ...spec.worlds[0], id: 'sample' }] })).toThrow('duplicate observation world identifier');
    expect(() => parseObservationSpec({ ...spec, worlds: [{ ...spec.worlds[0], id: '../escape' }] })).toThrow('world identifier');
  });

  it('rejects source traversal, unsupported assets and duplicate metadata names', async () => {
    const { spec } = await observationFixture();
    const altered = patch => ({ ...spec, worlds: [{ ...spec.worlds[0], ...patch }] });
    expect(() => parseObservationSpec(altered({ source: 'data/jobs/../private/world' }))).toThrow('Invalid package source path');
    expect(() => parseObservationSpec(altered({ source: 'dist/worlds/private' }))).toThrow('local job world');
    expect(() => parseObservationSpec(altered({ asset: 'private.mov' }))).toThrow('scene asset');
    expect(() => parseObservationSpec(altered({ credits: ['SOURCE_LICENSE', 'SOURCE_LICENSE'] }))).toThrow('duplicate observation credits');
    expect(() => parseObservationSpec(altered({ credits: ['world.json'] }))).toThrow('credit filename');
    expect(() => parseObservationSpec(altered({ credits: ['training.log'] }))).toThrow('credit filename');
  });

  it.each(['html', 'json'])('rejects private references in public %s report text', async extension => {
    const { root, output, spec, put } = await observationFixture();
    const file = spec.files.find(name => name.endsWith(`.${extension}`));
    await put(`dist/${file}`, extension === 'json' ? { source: '/Users/person/private.mov' } : '<a href="http://127.0.0.1:4317/data/jobs/private/world/world.json">local source</a>');
    await expect(packageViewer({ root, output, includeExperiments: true })).rejects.toThrow('Private source reference');
    await expect(access(output)).rejects.toThrow();
  });

  it('checks catalog publication text as well as world metadata', async () => {
    const { root, output, catalog, put } = await observationFixture();
    catalog.scenes.at(-1).detail = 'Source is /Users/person/private.mov';
    await put('dist/worlds/catalog.json', catalog);
    await expect(packageViewer({ root, output, includeExperiments: true })).rejects.toThrow('Private source reference');
  });

  it.each(['file', 'directory'])('rejects report %s symlinks', async kind => {
    const { root, output } = await observationFixture();
    const target = path.join(root, kind === 'file' ? 'dist/experiments/mapillary/index.html' : 'dist/experiments/mapillary');
    const saved = path.join(root, `saved-report-${kind}`);
    await rename(target, saved);
    await symlink(saved, target, kind === 'file' ? 'file' : 'dir');
    await expect(packageViewer({ root, output, includeExperiments: true })).rejects.toThrow('Only ordinary');
    await expect(access(output)).rejects.toThrow();
  });

  it('preflights every report before making a package', async () => {
    const { root, output } = await observationFixture();
    await rm(path.join(root, 'dist/experiments/mapillary/comparison.png'));
    await expect(packageViewer({ root, output, includeExperiments: true })).rejects.toThrow();
    await expect(access(output)).rejects.toThrow();
  });
});

it('packages only explicitly referenced background files and validates mesh indices', async () => {
  const setup = await fixture(); const { manifests, put, root, output } = setup;
  manifests.sample.background = { path: 'background/background.json' };
  const background = { schemaVersion:1, views:[{ id:'synthetic', center:[0,0,0], panoramaToWorld:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], imagePath:'photo.jpg',meshPath:'shell.json' }] };
  await put('dist/worlds/sample/world.json',manifests.sample);
  await put('dist/worlds/sample/background/background.json',background);
  await put('dist/worlds/sample/background/photo.jpg','synthetic image');
  await put('dist/worlds/sample/background/private-original.jpg','must not publish');
  await put('dist/worlds/sample/background/shell.json',{schemaVersion:1,positions:[0,0,0,1,0,0,0,1,0],uvs:[0,0,1,0,0,1],indices:[0,1,2]});
  await packageViewer({root,output});
  await expect(access(path.join(output,'www/worlds/sample/background/photo.jpg'))).resolves.toBeUndefined();
  await expect(access(path.join(output,'www/worlds/sample/background/private-original.jpg'))).rejects.toThrow();
});
