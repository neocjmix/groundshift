# Architecture

```text
Original video/images
  -> preprocessing (FFmpeg)
  -> reconstruction backend (camera estimation, training, export)
  -> validated world artifact
  -> browser viewer (scene loader + navigation)
```

Initial implementation is a local CLI and static web app, not a service.

The subsequent user-requested Railway deployment packages the already built static viewer and authorized world artifacts and experiment observations. It adds a static file server only. Native reconstruction, private datasets and model weights remain local; no cloud worker or reconstruction API is introduced. See [deployment](DEPLOYMENT.md).

## Implemented boundaries (2026-11-04)

`scripts/reconstruct.py` invokes pinned Brush 0.3.0 as a local process. It accepts a local posed, undistorted image directory and a new output directory, owns process cancellation/logging, checks the export and writes the portable artifact. GPU kernels and optimization remain inside Brush. The official arm64 release uses Metal on this Mac; no Rust build or general backend/plugin framework is introduced.

For unposed images, the separate `scripts/estimate-poses.py` uses official PyCOLMAP on CPU and emits a compatible dataset. Both supplied-pose and locally estimated-pose paths have now been validated. The latter registered all 120 raw sample photographs using actual supplied lens calibration, without supplied camera positions or sparse points. The Homebrew executable was blocked by the existing Xcode-license configuration; using the official arm64 Python wheel avoided that dependency obstacle. See [CPU results and preserved earlier failures](COLMAP.md).

The browser never starts native processes. React owns the interface; Three.js, OrbitControls and Spark own one live renderer and scene. Local folder selection loads assets with browser object URLs, without upload. HTTP manifests resolve asset paths relative to the manifest, and scene replacement guards against stale asynchronous completion. Loading/error UI and GPU-context recovery are tested independently of visual acceptance.

`scripts/build-world.py` now chains `prepare-video.py` (optional), CPU estimation,
a registration coverage gate and `reconstruct.py`. Each stage remains a local
process with its own logs. Source sequence order is separate from camera
geometry; omitted registered views become playback gaps. The command does not
claim visual acceptance or original-video success merely because export passed.

For tagged phone HDR, preparation uses an explicitly selected FFmpeg with zimg:
CPU transfer/gamut conversion and a recorded reference tone map produce SDR
training images. Missing filters or unsupported base-layer metadata fail before
extraction. This remains preprocessing within the local reconstruction boundary;
the viewer consumes the same world format. A private original indoor video has
now passed the full command and separate browser inspection without supplied
lens calibration or poses. See [actual evidence](ORIGINAL_VIDEO.md).

The strict schema in `src/world.ts` and [world format reference](WORLD_FORMAT.md) replace the illustrative shape below for real artifacts. Version 1 supports one Gaussian asset, orbit and optional camera-path navigation. The viewer world is right-handed, +Y-up with arbitrary or meter units, an explicit uniform asset transform and camera position/target/up/clipping. Three.js cameras look along local −Z. The manifest never silently assumes an asset's up-axis or invents a safe origin. Native exports retain genuine world-space camera matrices in `cameras.json`; the viewer must not apply the asset transform to them again. Explicit sequence edges permit interpolated movement; unknown edges and different components stop it. Free look changes orientation without moving off the selected camera route.

## Reconstruction backend boundary
The [observed-correspondence experiment](STEREO_ANCHORS.md) reuses fixed camera
poses and the existing OpenCV stereo functions as local CPU processes. It adds
calibration evidence and diagnostic point clouds, not a new service or GPU
abstraction. Panorama crop cameras remain analytically co-located with their
physical panorama; actual RGB matches do not add camera centers.

The [one-panorama P1 experiment](PANORAMIC_DEPTH_P1.md) adds a pinned local depth
process plus explicitly calibrated spherical projection. Raw prediction semantics,
SfM radial calibration and measured-by-image-estimation pose metadata stay separate.
The [adjacent-pair follow-up](PANORAMIC_PAIR_P1.md) adds bidirectional radial/RGB projection without pose refinement or fusion, preserving source IDs and explicit uncertainty. Its point-cloud report uses the existing static viewer infrastructure; a colored
PLY is not passed off as a trained Gaussian world. The [calibration control](PANORAMIC_CALIBRATION.md) reuses these outputs and the existing local MPS perspective-depth CLI, with explicit camera-Z/radial conversion and fixed observed-feature evaluation. No backend framework is added.


The public-panorama experiment adds an input preparation step: verified licensed
equirectangular photos are reprojected to overlapping pinhole crops with known
projection intrinsics. Crop rotations are relative to an individual panorama;
they do not establish camera translations, compass orientation, metric scale,
or a new measured baseline. World poses still need reconstruction. The prototype
does not pretend that ordinary perspective trainers understand an equirectangular
image directly.

The current object experiment uses whole-frame img2img diffusion only to add
input images. Camera estimation follows generation; relative depth is calibrated
to neighboring feature correspondences and fused to initialize Brush. Earlier
masked completion remains historical evidence rather than the current workflow.
See [object experiment](OBJECT_FOCUS_EXPERIMENT.md). The latest
[no-depth ablation](OBJECT_NO_DEPTH.md) bypasses both generation and learned
depth, reuses the exact nine-image camera dataset, and initializes from
triangulated SfM points within the same object selection. It keeps the existing
local process and portable artifact boundaries.

Diffusion is an experimental local preprocessing process,
not part of the viewer or a cloud worker. Keep source images, generated pixels,
mask semantics, model revision/seed and camera evidence distinct. Evaluate
against real withheld views and distinguish experimental publication from quality
acceptance. Railway displays failed and successful experiments alike, including
explicitly licensed public comparison crops. [Experiment and status](MAPILLARY_EXPERIMENT.md).

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
