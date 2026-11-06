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

function cameraFile() {
  return {
    schemaVersion: 1,
    cameraConvention: 'OpenGL: +X right, +Y up, -Z forward',
    worldConvention: 'right-handed Y-up, arbitrary units',
    frames: [{ image: 'synthetic.png', cameraToWorld: [[1, 0, 0, 6], [0, 1, 0, 7], [0, 0, 1, 8], [0, 0, 0, 1]] }],
  };
}

function pathManifest(): WorldManifest {
  const input = manifest();
  input.navigation.mode = 'camera-path';
  input.navigation.camerasPath = 'metadata/cameras.json';
  return input;
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

  it('loads camera metadata beside the redirected manifest without applying the asset transform again', async () => {
    const input = pathManifest();
    input.coordinates.assetToWorld = { position: [9, 8, 7], quaternion: [1, 0, 0, 0], scale: 3 };
    vi.stubGlobal('window', { location: { href: browserUrl } });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse(input, 'https://example.com/redirected/world.json'))
      .mockResolvedValueOnce(Response.json(cameraFile()));
    vi.stubGlobal('fetch', fetchMock);
    const controller = new AbortController();
    const loaded = await loadWorld('/world.json', controller.signal);
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'https://example.com/redirected/metadata/cameras.json', { signal: controller.signal });
    expect(loaded.cameraPath?.poses[0].position.toArray()).toEqual([6, 7, 8]);
    expect(loaded.cameraPathError).toBeUndefined();
  });

  it.each([
    { response: () => new Response('missing', { status: 404 }), message: 'HTTP 404' },
    { response: () => new Response('<html>fallback</html>'), message: 'Camera path unavailable' },
    { response: () => Response.json({ ...cameraFile(), cameraConvention: 'unconverted axes' }), message: 'Camera path unavailable' },
  ])('retains orbit when optional camera metadata fails: $message', async ({ response, message }) => {
    vi.stubGlobal('window', { location: { href: browserUrl } });
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(jsonResponse(pathManifest(), 'https://example.com/world.json'))
      .mockResolvedValueOnce(response()));
    const loaded = await loadWorld('/world.json', new AbortController().signal);
    expect(loaded.cameraPath).toBeUndefined();
    expect(loaded.cameraPathError).toContain(message);
    expect(loaded.assetUrl).toBe('https://example.com/assets/scene.ply');
  });

  it('propagates camera-fetch abort rather than downgrading it to an optional warning', async () => {
    vi.stubGlobal('window', { location: { href: browserUrl } });
    const aborted = new DOMException('cancelled', 'AbortError');
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(jsonResponse(pathManifest(), 'https://example.com/world.json'))
      .mockRejectedValueOnce(aborted));
    await expect(loadWorld('/world.json', new AbortController().signal)).rejects.toBe(aborted);
  });

  it('rejects stale completion when cancellation occurs during camera JSON decoding', async () => {
    vi.stubGlobal('window', { location: { href: browserUrl } });
    const controller = new AbortController();
    const response = Response.json(cameraFile());
    vi.spyOn(response, 'json').mockImplementation(async () => {
      controller.abort();
      return cameraFile();
    });
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(jsonResponse(pathManifest(), 'https://example.com/world.json'))
      .mockResolvedValueOnce(response));
    await expect(loadWorld('/world.json', controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
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

  it('reads only the referenced local camera file and keeps world coordinates', async () => {
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:local-path');
    const loaded = await loadLocalWorld([
      localFile('capture/world.json', JSON.stringify(pathManifest())),
      localFile('capture/assets/scene.ply', 'synthetic bytes'),
      localFile('capture/cameras.json', 'wrong file with the same basename'),
      localFile('capture/metadata/cameras.json', JSON.stringify(cameraFile())),
    ]);
    expect(loaded.cameraPath?.poses[0].position.toArray()).toEqual([6, 7, 8]);
    loaded.release?.();
  });

  it('offers orbit when the selected folder has no referenced camera file', async () => {
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:local-path');
    const loaded = await loadLocalWorld([
      localFile('capture/world.json', JSON.stringify(pathManifest())),
      localFile('capture/assets/scene.ply', 'synthetic bytes'),
    ]);
    expect(loaded.cameraPathError).toContain('missing metadata/cameras.json');
    expect(loaded.cameraPath).toBeUndefined();
    loaded.release?.();
  });

  it('does not create a scene blob when cancelled during local camera decoding', async () => {
    const create = vi.spyOn(URL, 'createObjectURL');
    const controller = new AbortController();
    const cameras = localFile('capture/metadata/cameras.json', JSON.stringify(cameraFile()));
    vi.spyOn(cameras, 'text').mockImplementation(async () => {
      controller.abort();
      return JSON.stringify(cameraFile());
    });
    await expect(loadLocalWorld([
      localFile('capture/world.json', JSON.stringify(pathManifest())),
      localFile('capture/assets/scene.ply', 'synthetic bytes'), cameras,
    ], controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
    expect(create).not.toHaveBeenCalled();
  });
});

const backgroundFile = () => ({ schemaVersion: 1, views: [{ id: 'synthetic-background', center: [0,0,0], panoramaToWorld: [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], imagePath: 'photo.jpg', meshPath: 'mesh.json' }] });
describe('optional background metadata and local lifecycle (synthetic fixtures)', () => {
  it('resolves background files beside redirected metadata and does not fetch texture/mesh during GS load', async () => {
    const input = manifest(); input.background = { path: 'background/background.json' };
    vi.stubGlobal('window', { location: { href: 'http://127.0.0.1:5173/' } });
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse(input, 'https://example.com/world.json'))
      .mockResolvedValueOnce(jsonResponse(backgroundFile(), 'https://example.com/redirected/background.json'));
    vi.stubGlobal('fetch', fetchMock);
    const result = await loadWorld('/world.json', new AbortController().signal);
    expect(result.background?.views[0].imageUrl).toBe('https://example.com/redirected/photo.jpg');
    expect(result.background?.views[0].meshUrl).toBe('https://example.com/redirected/mesh.json');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
  it('preserves GS if optional background fails and propagates cancellation', async () => {
    const input = manifest(); input.background = { path: 'background.json' };
    vi.stubGlobal('window', { location: { href: 'http://127.0.0.1:5173/' } });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(jsonResponse(input, 'https://example.com/world.json')).mockResolvedValueOnce(new Response('', { status: 404 })));
    expect((await loadWorld('/world.json', new AbortController().signal)).backgroundError).toContain('HTTP 404');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(jsonResponse(input, 'https://example.com/world.json')).mockRejectedValueOnce(new DOMException('cancelled', 'AbortError')));
    await expect(loadWorld('/world.json', new AbortController().signal)).rejects.toMatchObject({ name: 'AbortError' });
  });
  it('resolves exact nested local background files and releases every object URL', async () => {
    const input = manifest(); input.background = { path: 'background/background.json' };
    const create = vi.spyOn(URL, 'createObjectURL').mockImplementation(f => 'blob:'+((f as File).webkitRelativePath));
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const result = await loadLocalWorld([localFile('capture/world.json', JSON.stringify(input)), localFile('capture/assets/scene.ply','fixture'),
      localFile('capture/background/background.json',JSON.stringify(backgroundFile())), localFile('capture/background/photo.jpg','fixture'), localFile('capture/background/mesh.json','fixture')]);
    expect(result.background?.views[0].imageUrl).toBe('blob:capture/background/photo.jpg');
    expect(create).toHaveBeenCalledTimes(3); result.release?.(); expect(revoke).toHaveBeenCalledTimes(3);
  });
});
