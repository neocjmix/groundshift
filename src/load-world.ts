import {
  parseWorldManifest,
  resolveAssetUrl,
  type WorldManifest,
} from "./world";

export interface LoadedWorld {
  instanceId: string;
  manifest: WorldManifest;
  assetUrl: string;
  location: string;
  release?: () => void;
}

export async function loadWorld(
  path: string,
  signal: AbortSignal,
): Promise<LoadedWorld> {
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
  } catch {
    throw new Error(
      "This URL did not return a JSON world manifest. Check the world.json path.",
    );
  }
  const manifest = parseWorldManifest(json);
  return {
    instanceId: crypto.randomUUID(),
    manifest,
    assetUrl: resolveAssetUrl(response.url, manifest.assets[0].path),
    location: url.pathname,
  };
}

export async function loadLocalWorld(files: File[]): Promise<LoadedWorld> {
  const manifests = files.filter((file) => file.name === "world.json");
  if (manifests.length !== 1)
    throw new Error(
      "Choose one world folder containing exactly one world.json and its scene asset.",
    );
  const file = manifests[0];
  const manifest = parseWorldManifest(JSON.parse(await file.text()));
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
  const assetUrl = URL.createObjectURL(asset);
  return {
    instanceId: crypto.randomUUID(),
    manifest,
    assetUrl,
    location: file.webkitRelativePath,
    release: () => URL.revokeObjectURL(assetUrl),
  };
}
