# Architecture

```text
Original video/images
  -> preprocessing (FFmpeg)
  -> reconstruction backend (camera estimation, training, export)
  -> validated world artifact
  -> browser viewer (scene loader + navigation)
```

Initial implementation is a local CLI and static web app, not a service.

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
This is an example, not actual reconstructed data. Define and validate camera-forward direction, world/asset transform and spawn from real reconstruction. Never assume the origin is a safe spawn.

## Viewer
Three.js + Spark candidate. First load a licensed sample splat with orbit controls, then path-constrained movement with free look. Gaussian splats do not inherently contain collision or floor geometry. Free walking needs explicit movement bounds, floor estimation or collision representation.

## Migration
Optimize the local backend for Metal without compromise. A future CUDA worker can use completely different tools and intermediates while respecting the reconstruction job boundary and artifact contract. Do not implement a speculative CUDA adapter now.

## Privacy and licensing
Never commit raw footage or large outputs. Record sample-data provenance and upstream license compatibility. Public availability of street imagery does not imply permission to reconstruct or redistribute it. Public sharing needs privacy review for faces and license plates.
