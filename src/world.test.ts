import { describe, expect, it } from 'vitest';
import { parseWorldManifest, resolveAssetUrl, type WorldManifest } from './world';

// Deliberately synthetic parser fixture, not a measured scene or recovered pose.
function fixture(): WorldManifest {
  return {
    schemaVersion: 1,
    id: 'synthetic-parser-fixture',
    title: 'Synthetic parser fixture',
    assets: [{ kind: 'gaussian-splat', format: 'ply', path: 'assets/scene.ply' }],
    coordinates: {
      handedness: 'right', upAxis: 'y', unit: 'arbitrary',
      assetToWorld: { position: [1, 2, 3], quaternion: [0, 0, 0, 1], scale: 1 },
    },
    navigation: {
      mode: 'orbit',
      camera: { position: [2, 3, 4], target: [0, 0, 0], up: [0, 1, 0], fov: 60, near: 0.01, far: 1000 },
      camerasPath: 'cameras.json',
    },
    provenance: {
      sourceType: 'sample', sourceUrl: 'https://example.com/fixture',
      license: 'CC0-1.0', licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
      attribution: 'Synthetic test fixture', backend: 'none; parser test only',
    },
  };
}

describe('parseWorldManifest', () => {
  it('preserves explicit coordinates and accepts the complete v1 contract', () => {
    const manifest = fixture();
    expect(parseWorldManifest(manifest)).toEqual(manifest);
  });

  it('accepts a normalized nonidentity rotation without altering it', () => {
    const manifest = fixture();
    manifest.coordinates.assetToWorld.quaternion = [Math.SQRT1_2, 0, 0, Math.SQRT1_2];
    manifest.coordinates.assetToWorld.scale = 2;
    expect(parseWorldManifest(manifest)).toEqual(manifest);
  });

  it('accepts local source provenance and optional fields being absent', () => {
    const manifest = fixture();
    manifest.provenance.sourceType = 'images';
    manifest.provenance.sourceUrl = 'file:///tmp/licensed-images';
    delete manifest.navigation.camerasPath;
    expect(parseWorldManifest(manifest)).toEqual(manifest);
  });

  it.each(['ply', 'spz', 'splat', 'ksplat', 'sog'] as const)('accepts the %s format', (format) => {
    const manifest = fixture();
    manifest.assets[0]!.format = format;
    expect(parseWorldManifest(manifest).assets[0]!.format).toBe(format);
  });

  it.each([null, {}, [], 'not an object', { ...fixture(), schemaVersion: 2 }].map((input) => ({ input })))('rejects a missing or unsupported contract: %j', ({ input }) => {
    expect(() => parseWorldManifest(input)).toThrow();
  });

  it('rejects unknown fields instead of silently discarding potentially important metadata', () => {
    expect(() => parseWorldManifest({ ...fixture(), collision: 'guessed' })).toThrow();
    const manifest = fixture();
    expect(() => parseWorldManifest({
      ...manifest,
      coordinates: { ...manifest.coordinates, assumedFloor: 0 },
    })).toThrow();
  });

  it.each([[], [...fixture().assets, ...fixture().assets]].map((assets) => ({ assets })))('requires exactly one scene asset', ({ assets }) => {
    expect(() => parseWorldManifest({ ...fixture(), assets })).toThrow();
  });

  it.each([
    '', '/scene.ply', '../scene.ply', 'assets/../scene.ply', './scene.ply',
    'assets//scene.ply', 'assets/', 'https://example.com/scene.ply', '//example.com/scene.ply',
    'scene.ply?download=1', 'scene.ply#part', 'assets\\scene.ply', '%2e%2e/scene.ply',
    'assets/%2fscene.ply', ' scene.ply', 'scene.ply ', 'scene\n.ply', 'scene\u0000.ply',
  ])('rejects unsafe asset and camera paths: %j', (path) => {
    const manifest = fixture();
    manifest.assets[0]!.path = path;
    expect(() => parseWorldManifest(manifest)).toThrow();
    const cameraManifest = fixture();
    cameraManifest.navigation.camerasPath = path;
    expect(() => parseWorldManifest(cameraManifest)).toThrow();
  });

  it.each([NaN, Infinity, -Infinity])('rejects nonfinite numeric metadata: %s', (value) => {
    const manifest = fixture();
    manifest.coordinates.assetToWorld.position[0] = value;
    expect(() => parseWorldManifest(manifest)).toThrow();
  });

  it.each([0, -1, Infinity])('rejects invalid asset scale: %s', (scale) => {
    const manifest = fixture();
    manifest.coordinates.assetToWorld.scale = scale;
    expect(() => parseWorldManifest(manifest)).toThrow();
  });

  it.each([[0, 0, 0, 0], [0, 0, 0, 2], [0, 0, 0, 0.99]].map((quaternion) => ({ quaternion })))('rejects an unnormalized quaternion: %j', ({ quaternion }) => {
    const manifest = fixture();
    expect(() => parseWorldManifest({
      ...manifest,
      coordinates: { ...manifest.coordinates, assetToWorld: { ...manifest.coordinates.assetToWorld, quaternion } },
    })).toThrow();
  });

  it.each([{ upAxis: 'z' }, { handedness: 'left' }, { unit: 'unknown' }])('requires declared supported world coordinates: %j', (coordinates) => {
    const manifest = fixture();
    expect(() => parseWorldManifest({ ...manifest, coordinates: { ...manifest.coordinates, ...coordinates } })).toThrow();
  });

  it.each([
    { fov: 0 }, { fov: 180 }, { near: 0 }, { near: -1 }, { far: 0.01 }, { far: -1 },
    { position: [0, 0, 0] }, { up: [0, 0, 0] }, { up: [2, 3, 4] }, { up: [-2, -3, -4] },
    { position: [1e308, 0, 0], target: [-1e308, 0, 0] },
    { position: [0, 0], target: [0, 0, 0] },
  ])('rejects invalid camera projection or basis: %j', (camera) => {
    const manifest = fixture();
    expect(() => parseWorldManifest({
      ...manifest, navigation: { ...manifest.navigation, camera: { ...manifest.navigation.camera, ...camera } },
    })).toThrow();
  });

  it.each(['javascript:alert(1)', 'data:text/html,hello', 'relative/source', 'https://user:password@example.com/'])('rejects unsafe provenance URLs: %j', (sourceUrl) => {
    const manifest = fixture();
    expect(() => parseWorldManifest({ ...manifest, provenance: { ...manifest.provenance, sourceUrl } })).toThrow();
  });
});

describe('resolveAssetUrl', () => {
  it('resolves relative to the artifact manifest, retaining nested paths', () => {
    expect(resolveAssetUrl('http://127.0.0.1:5173/worlds/scene/world.json', 'assets/scene.ply'))
      .toBe('http://127.0.0.1:5173/worlds/scene/assets/scene.ply');
  });

  it('encodes plain filenames and does not inherit manifest query or fragment', () => {
    expect(resolveAssetUrl('https://example.com/world/world.json?fresh=1#top', 'my scene.ply'))
      .toBe('https://example.com/world/my%20scene.ply');
  });

  it('rejects traversal even when called without parsing a manifest', () => {
    expect(() => resolveAssetUrl('https://example.com/world/world.json', '../private.ply')).toThrow();
  });

  it.each(['file:///tmp/world.json', 'data:application/json,{}', '/world.json', 'https://user:password@example.com/world.json'])('rejects unsuitable manifest base URLs: %j', (manifestUrl) => {
    expect(() => resolveAssetUrl(manifestUrl, 'scene.ply')).toThrow();
  });
});
