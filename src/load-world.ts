import {
  parseWorldManifest,
  resolveAssetUrl,
  type WorldManifest,
  parsePagedIndex,type PagedIndex,
} from "./world";
import { parseCameraPath, type CameraPath } from "./camera-path";
import { parseStreamIndex,type LoadedStream } from './streaming';

export interface LoadedWorld {
  instanceId: string;
  manifest: WorldManifest;
  assetUrl: string;
  location: string;
  cameraPath?: CameraPath;
  cameraPathError?: string;
  streaming?: LoadedStream;
  paging?: {index:PagedIndex;baseUrl:string};
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
  // Retired panorama/shell references remain parseable in archived manifests,
  // but the viewer never fetches them: translated backgrounds degraded UX.
  signal.throwIfAborted();
  let streaming:LoadedStream|undefined;
  if(manifest.streaming){
    const indexResponse=await fetch(resolveAssetUrl(response.url,manifest.streaming.path),{signal});
    if(!indexResponse.ok)throw new Error(`Stream index: HTTP ${indexResponse.status}`);
    const index=parseStreamIndex(await indexResponse.json());
    streaming={index,urls:new Map(index.chunks.map(c=>[c.id,resolveAssetUrl(indexResponse.url,c.path)]))};
  }
  signal.throwIfAborted();
  let paging:LoadedWorld['paging'];
  if(manifest.paging){
    if(manifest.streaming)throw new Error('Choose one spatial delivery representation');
    const r=await fetch(resolveAssetUrl(response.url,manifest.paging.path),{signal});
    if(!r.ok)throw new Error(`RAD index: HTTP ${r.status}`);
    paging={index:parsePagedIndex(await r.json()),baseUrl:r.url};
  }
  signal.throwIfAborted();
  return {
    instanceId: crypto.randomUUID(),
    manifest,
    assetUrl: resolveAssetUrl(response.url, manifest.assets[0].path),
    location: url.pathname,
    ...cameras,
    streaming,
    paging,
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
  if(manifest.paging)throw new Error('Paged RAD worlds currently require HTTP(S). Serve this folder with the local viewer or use the whole SPZ control world.');
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
  signal?.throwIfAborted();
  const assetUrl = URL.createObjectURL(asset);
  const urls:string[]=[assetUrl];
  let streaming:LoadedStream|undefined;
  try{
    if(manifest.streaming){
      const indexFile=files.find(c=>(c.webkitRelativePath||c.name)===base+manifest.streaming!.path);
      if(!indexFile)throw new Error('The selected folder is missing its stream index');
      const index=parseStreamIndex(JSON.parse(await indexFile.text())),indexBase=manifest.streaming.path.slice(0,manifest.streaming.path.lastIndexOf('/')+1);
      streaming={index,urls:new Map(index.chunks.map(c=>{const file=files.find(f=>(f.webkitRelativePath||f.name)===base+indexBase+c.path);if(!file)throw new Error(`Missing stream chunk ${c.path}`);const url=URL.createObjectURL(file);urls.push(url);return[c.id,url];}))};
    }
    signal?.throwIfAborted();
  }catch(error){urls.forEach(u=>URL.revokeObjectURL(u));throw error;}
  return {
    instanceId: crypto.randomUUID(),
    manifest,
    assetUrl,
    location: file.webkitRelativePath,
    ...cameras,
    streaming,
    release: () => urls.forEach(u=>URL.revokeObjectURL(u)),
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
