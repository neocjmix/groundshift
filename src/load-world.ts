import {
  parseWorldManifest,
  resolveAssetUrl,
  type WorldManifest,
} from "./world";
import { parseBackground, type LoadedBackground } from "./background";
import { parseCameraPath, type CameraPath } from "./camera-path";

export interface LoadedWorld {
  instanceId: string;
  manifest: WorldManifest;
  assetUrl: string;
  location: string;
  cameraPath?: CameraPath;
  cameraPathError?: string;
  background?: LoadedBackground;
  backgroundError?: string;
  release?: () => void;
}

export async function loadWorld(
  path: string,
  signal: AbortSignal,
): Promise<LoadedWorld> {
  signal.throwIfAborted();
  const url = new URL(path, window.location.href);
  if (!["http:", "https:"].includes(url.protocol))
    throw new Error(
      "Use an HTTP(S) world.json URL or open a local world folder.",
    );
  const response = await fetch(url, { signal });
  if (!response.ok)
    throw new Error(
      `World manifest: HTTP ${response.status}. Check the path and run npm run sample for the example.`,
    );
  let json: unknown;
  try {
    json = await response.json();
  } catch (error) {
    signal.throwIfAborted();
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new Error(
      "This URL did not return a JSON world manifest. Check the world.json path.",
      { cause: error },
    );
  }
  signal.throwIfAborted();
  const manifest = parseWorldManifest(json);
  const cameras = await loadOptionalCameras(manifest, signal, async (cameraPath) => {
    const cameraResponse = await fetch(resolveAssetUrl(response.url, cameraPath), { signal });
    if (!cameraResponse.ok) throw new Error(`Camera metadata: HTTP ${cameraResponse.status}`);
    return cameraResponse.json();
  });
  const backgrounds = await loadOptionalBackground(manifest, signal, async (path) => {
    const backgroundResponse = await fetch(resolveAssetUrl(response.url, path), { signal });
    if (!backgroundResponse.ok) throw new Error(`Background metadata: HTTP ${backgroundResponse.status}`);
    const parsed = parseBackground(await backgroundResponse.json());
    const base = backgroundResponse.url || resolveAssetUrl(response.url, path);
    return { ...parsed, views: parsed.views.map(v => ({ ...v, imageUrl: resolveAssetUrl(base, v.imagePath),
      meshUrl: v.meshPath ? resolveAssetUrl(base, v.meshPath) : undefined })) };
  });
  signal.throwIfAborted();
  return {
    instanceId: crypto.randomUUID(),
    manifest,
    assetUrl: resolveAssetUrl(response.url, manifest.assets[0].path),
    location: url.pathname,
    ...cameras,
    ...backgrounds,
  };
}

export async function loadLocalWorld(files: File[], signal?: AbortSignal): Promise<LoadedWorld> {
  signal?.throwIfAborted();
  const manifests = files.filter((file) => file.name === "world.json");
  if (manifests.length !== 1)
    throw new Error(
      "Choose one world folder containing exactly one world.json and its scene asset.",
    );
  const file = manifests[0];
  const manifest = parseWorldManifest(JSON.parse(await file.text()));
  signal?.throwIfAborted();
  const base = file.webkitRelativePath.slice(0, -file.name.length);
  const asset = files.find(
    (candidate) =>
      (candidate.webkitRelativePath || candidate.name) ===
      base + manifest.assets[0].path,
  );
  if (!asset)
    throw new Error(
      `The selected folder is missing ${manifest.assets[0].path}.`,
    );
  const cameras = await loadOptionalCameras(manifest, signal, async (cameraPath) => {
    const cameraFile = files.find((candidate) => (candidate.webkitRelativePath || candidate.name) === base + cameraPath);
    if (!cameraFile) throw new Error(`The selected folder is missing ${cameraPath}`);
    return JSON.parse(await cameraFile.text()) as unknown;
  });
  const backgroundUrls: string[] = [];
  const backgrounds = await loadOptionalBackground(manifest, signal, async (path) => {
    const metadataFile = files.find(f => (f.webkitRelativePath || f.name) === base + path);
    if (!metadataFile) throw new Error(`Missing ${path}`);
    const parsed = parseBackground(JSON.parse(await metadataFile.text()));
    signal?.throwIfAborted();
    const directory = path.slice(0, path.lastIndexOf('/') + 1);
    const selected = parsed.views.map(v => {
      const find = (p: string) => {
        const f = files.find(f => (f.webkitRelativePath || f.name) === base + directory + p);
        if (!f) throw new Error(`Missing background file ${p}`);
        return f;
      };
      return { view: v, image: find(v.imagePath), mesh: v.meshPath ? find(v.meshPath) : undefined };
    });
    const objectUrl = (f: File) => { const url = URL.createObjectURL(f); backgroundUrls.push(url); return url; };
    return { ...parsed, views: selected.map(v => ({ ...v.view, imageUrl: objectUrl(v.image), meshUrl: v.mesh ? objectUrl(v.mesh) : undefined })) };
  });
  if (signal?.aborted) { backgroundUrls.forEach(url => URL.revokeObjectURL(url)); signal.throwIfAborted(); }
  const assetUrl = URL.createObjectURL(asset);
  return {
    instanceId: crypto.randomUUID(),
    manifest,
    assetUrl,
    location: file.webkitRelativePath,
    ...cameras,
    ...backgrounds,
    release: () => [assetUrl, ...backgroundUrls].forEach(url => URL.revokeObjectURL(url)),
  };
}

async function loadOptionalCameras(
  manifest: WorldManifest,
  signal: AbortSignal | undefined,
  read: (path: string) => Promise<unknown>,
): Promise<Pick<LoadedWorld, 'cameraPath' | 'cameraPathError'>> {
  if (!manifest.navigation.camerasPath) return {};
  try {
    const input = await read(manifest.navigation.camerasPath);
    signal?.throwIfAborted();
    return { cameraPath: parseCameraPath(input, manifest.coordinates.unit) };
  } catch (error) {
    signal?.throwIfAborted();
    if (error instanceof Error && error.name === 'AbortError') throw error;
    return { cameraPathError: `Camera path unavailable. Orbit remains available. ${error instanceof Error ? error.message : String(error)}` };
  }
}

async function loadOptionalBackground(manifest: WorldManifest, signal: AbortSignal | undefined,
  read: (path: string) => Promise<LoadedBackground>): Promise<Pick<LoadedWorld, 'background' | 'backgroundError'>> {
  if (!manifest.background) return {};
  try {
    const background = await read(manifest.background.path);
    signal?.throwIfAborted();
    return { background };
  } catch (error) {
    signal?.throwIfAborted();
    if (error instanceof Error && error.name === 'AbortError') throw error;
    return { backgroundError: `Background unavailable; GS remains unchanged. ${error instanceof Error ? error.message : String(error)}` };
  }
}
