import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadLocalWorld, loadWorld } from './load-world';
import type { WorldManifest } from './world';

function manifest(): WorldManifest {
  return {
    schemaVersion: 1,
    id: 'synthetic-loader-fixture',
    title: 'Synthetic loader fixture',
    assets: [{ kind: 'gaussian-splat', format: 'ply', path: 'assets/scene.ply' }],
    coordinates: {
      handedness: 'right', upAxis: 'y', unit: 'arbitrary',
      assetToWorld: { position: [0, 0, 0], quaternion: [0, 0, 0, 1], scale: 1 },
    },
    navigation: {
      mode: 'orbit',
      camera: { position: [0, 0, 3], target: [0, 0, 0], up: [0, 1, 0], fov: 60, near: 0.01, far: 100 },
    },
    provenance: {
      sourceType: 'sample', sourceUrl: 'https://example.com/synthetic',
      license: 'CC0-1.0', licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
      attribution: 'Synthetic loader fixture only', backend: 'none',
    },
  };
}

function localFile(relativePath: string, contents: string): File {
  const file = new File([contents], relativePath.split('/').at(-1)!);
  Object.defineProperty(file, 'webkitRelativePath', { value: relativePath });
  return file;
}

function jsonResponse(body: unknown, url: string): Response {
  const response = Response.json(body);
  Object.defineProperty(response, 'url', { value: url });
  return response;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('HTTP world loading', () => {
  const browserUrl = 'http://127.0.0.1:5173/viewer/?world=old';

  function setup(response: Response) {
    vi.stubGlobal('window', { location: { href: browserUrl } });
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal('fetch', fetchMock);
    return fetchMock;
  }

  it('passes cancellation to fetch and resolves assets beside the final manifest URL', async () => {
    const fetchMock = setup(jsonResponse(manifest(), 'http://127.0.0.1:8000/redirected/world.json'));
    const controller = new AbortController();
    const loaded = await loadWorld('/worlds/example/world.json', controller.signal);

    expect(fetchMock).toHaveBeenCalledWith(
      new URL('http://127.0.0.1:5173/worlds/example/world.json'), { signal: controller.signal },
    );
    expect(loaded.assetUrl).toBe('http://127.0.0.1:8000/redirected/assets/scene.ply');
    expect(loaded.manifest).toEqual(manifest());
    expect(loaded.location).toBe('/worlds/example/world.json');
    expect(loaded.release).toBeUndefined();
  });

  it('gives repeated loads distinct renderer instance IDs', async () => {
    vi.stubGlobal('window', { location: { href: browserUrl } });
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => Promise.resolve(
      jsonResponse(manifest(), 'http://127.0.0.1:5173/world.json'),
    )));
    const signal = new AbortController().signal;
    const first = await loadWorld('/world.json', signal);
    const second = await loadWorld('/world.json', signal);
    expect(first.instanceId).not.toBe(second.instanceId);
  });

  it.each(['file:///tmp/world.json', 'data:application/json,{}', 'javascript:alert(1)'])(
    'rejects an unsupported manifest scheme before fetching: %s', async (url) => {
      const fetchMock = setup(jsonResponse(manifest(), 'http://127.0.0.1:5173/world.json'));
      await expect(loadWorld(url, new AbortController().signal)).rejects.toThrow('HTTP(S)');
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it('reports the actual HTTP error status', async () => {
    setup(new Response('Missing', { status: 404 }));
    await expect(loadWorld('/missing/world.json', new AbortController().signal)).rejects.toThrow('HTTP 404');
  });

  it('distinguishes a static-server HTML fallback from a JSON world', async () => {
    setup(new Response('<!doctype html><title>Vite fallback</title>'));
    await expect(loadWorld('/typo', new AbortController().signal)).rejects.toThrow('did not return a JSON world manifest');
  });

  it('validates HTTP metadata before returning a renderable asset URL', async () => {
    setup(jsonResponse({ ...manifest(), schemaVersion: 99 }, 'http://127.0.0.1:5173/world.json'));
    await expect(loadWorld('/world.json', new AbortController().signal)).rejects.toThrow();
  });

  it('propagates fetch cancellation without manufacturing a successful world', async () => {
    vi.stubGlobal('window', { location: { href: browserUrl } });
    const aborted = new DOMException('The operation was aborted', 'AbortError');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(aborted));
    await expect(loadWorld('/world.json', new AbortController().signal)).rejects.toBe(aborted);
  });
});

describe('local world folder loading', () => {
  it('loads the exact nested asset beside the selected manifest and releases its blob URL', async () => {
    const chosenAsset = localFile('capture/assets/scene.ply', 'synthetic bytes, not a real splat');
    const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:synthetic-scene');
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const loaded = await loadLocalWorld([
      localFile('capture/world.json', JSON.stringify(manifest())),
      localFile('capture/unrelated/scene.ply', 'wrong file with same basename'),
      chosenAsset,
    ]);

    expect(create).toHaveBeenCalledExactlyOnceWith(chosenAsset);
    expect(loaded.assetUrl).toBe('blob:synthetic-scene');
    expect(loaded.location).toBe('capture/world.json');
    expect(loaded.manifest).toEqual(manifest());
    expect(revoke).not.toHaveBeenCalled();
    loaded.release?.();
    expect(revoke).toHaveBeenCalledExactlyOnceWith('blob:synthetic-scene');
  });

  it('supports a manifest inside a nested selected directory', async () => {
    const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:nested-scene');
    const scene = localFile('collection/one/assets/scene.ply', 'synthetic bytes');
    const loaded = await loadLocalWorld([
      localFile('collection/one/world.json', JSON.stringify(manifest())), scene,
    ]);
    expect(create).toHaveBeenCalledExactlyOnceWith(scene);
    expect(loaded.assetUrl).toBe('blob:nested-scene');
  });

  it.each([
    { files: [] },
    { files: [localFile('capture/readme.txt', 'No manifest')] },
    { files: [localFile('one/world.json', '{}'), localFile('two/world.json', '{}')] },
  ])('rejects missing or ambiguous world manifests', async ({ files }) => {
    const create = vi.spyOn(URL, 'createObjectURL');
    await expect(loadLocalWorld(files)).rejects.toThrow('exactly one world.json');
    expect(create).not.toHaveBeenCalled();
  });

  it('reports the exact missing asset path and does not select a basename lookalike', async () => {
    const create = vi.spyOn(URL, 'createObjectURL');
    await expect(loadLocalWorld([
      localFile('capture/world.json', JSON.stringify(manifest())),
      localFile('capture/scene.ply', 'wrong location'),
    ])).rejects.toThrow('missing assets/scene.ply');
    expect(create).not.toHaveBeenCalled();
  });

  it('rejects invalid local JSON before creating resource URLs', async () => {
    const create = vi.spyOn(URL, 'createObjectURL');
    await expect(loadLocalWorld([localFile('capture/world.json', '{')])).rejects.toThrow();
    expect(create).not.toHaveBeenCalled();
  });

  it('rejects traversal in local manifests before selecting files', async () => {
    const create = vi.spyOn(URL, 'createObjectURL');
    const invalid = manifest();
    invalid.assets[0].path = '../scene.ply';
    await expect(loadLocalWorld([
      localFile('capture/world.json', JSON.stringify(invalid)),
      localFile('scene.ply', 'outside artifact'),
    ])).rejects.toThrow();
    expect(create).not.toHaveBeenCalled();
  });
});
