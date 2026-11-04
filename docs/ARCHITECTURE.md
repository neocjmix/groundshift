# Architecture

```text
Original video/images
  -> preprocessing (FFmpeg)
  -> reconstruction backend (camera estimation, training, export)
  -> validated world artifact
  -> browser viewer (scene loader + navigation)
```

Initial implementation is a local CLI and static web app, not a service.

## Implemented boundaries (2026-11-04)

`scripts/reconstruct.py` invokes pinned Brush 0.3.0 as a local process. It accepts a local posed, undistorted image directory and a new output directory, owns process cancellation/logging, checks the export and writes the portable artifact. GPU kernels and optimization remain inside Brush. The official arm64 release uses Metal on this Mac; no Rust build or general backend/plugin framework is introduced.

For unposed images, the separate `scripts/estimate-poses.py` uses official PyCOLMAP on CPU and emits a compatible dataset. COLMAP is optional: the validated main run uses supplied camera poses. The Homebrew executable was blocked by the existing Xcode-license configuration; using the official arm64 Python wheel avoided that dependency obstacle. See [the CPU result and incomplete registration](COLMAP.md).

The browser never starts native processes. React owns the interface; Three.js, OrbitControls and Spark own one live renderer and scene. Local folder selection loads assets with browser object URLs, without upload. HTTP manifests resolve asset paths relative to the manifest, and scene replacement guards against stale asynchronous completion. Loading/error UI and GPU-context recovery are tested independently of visual acceptance.

The strict schema in `src/world.ts` and [world format reference](WORLD_FORMAT.md) replace the illustrative shape below for real artifacts. Version 1 supports one Gaussian asset and orbit navigation. The viewer world is right-handed, +Y-up with arbitrary or meter units, an explicit uniform asset transform and camera position/target/up/clipping. Three.js cameras look along local −Z. The manifest never silently assumes an asset's up-axis or invents a safe origin. Native exports retain genuine camera matrices in `cameras.json`; path movement is not implemented yet.

## Reconstruction backend boundary
Treat the reconstruction tool as a process invoked with input path, output directory and backend-specific options. Capture exit code, logs, elapsed time and cancellation. The backend owns its internal steps: COLMAP is not a universal requirement and future neural reconstruction may estimate camera poses itself. Do not abstract Metal/CUDA kernels, training hyperparameters or internal cache.

Conceptual contract:
```ts
interface ReconstructionBackend {
  reconstruct(
    request: {
      sourcePath: string;
      sourceType: "video" | "images";
      outputDirectory: string;
      options?: Record<string, unknown>;
    },
    signal?: AbortSignal
  ): Promise<{ manifestPath: string; logsPath?: string }>;
}
```

## Portable world artifact
A directory containing a versioned manifest, renderable assets and optional camera trajectory. The asset format may be PLY, SPZ, GLB or future formats; don't force every backend to export the same internal representation.

Illustrative manifest:
```json
{
  "schemaVersion": 1,
  "id": "first-walk",
  "assets": [{"kind": "gaussian-splat", "format": "ply", "path": "scene.ply"}],
  "coordinates": {"upAxis": "z", "unit": "arbitrary"},
  "navigation": {"mode": "camera-path", "path": "camera-path.json"},
  "provenance": {"backend": "brush", "sourceType": "video"}
}
```
This is the original design example, not a valid implementation-v1 manifest or actual reconstructed data. Use [WORLD_FORMAT.md](WORLD_FORMAT.md) and `public/worlds/sample/world.json` for the current contract. Define and validate camera-forward direction, world/asset transform and spawn from real reconstruction. Never assume the origin is a safe spawn.

## Viewer
Three.js + Spark candidate. First load a licensed sample splat with orbit controls, then path-constrained movement with free look. Gaussian splats do not inherently contain collision or floor geometry. Free walking needs explicit movement bounds, floor estimation or collision representation.

## Migration
Optimize the local backend for Metal without compromise. A future CUDA worker can use completely different tools and intermediates while respecting the reconstruction job boundary and artifact contract. Do not implement a speculative CUDA adapter now.

## Privacy and licensing
Never commit raw footage or large outputs. Record sample-data provenance and upstream license compatibility. Public availability of street imagery does not imply permission to reconstruct or redistribute it. Public sharing needs privacy review for faces and license plates.
