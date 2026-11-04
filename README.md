# Groundshift (GS)

Revisit real places as explorable 3D worlds.

**Live demo:** [Browse all four worlds](https://groundshift-viewer-production.up.railway.app/) · [Open my desk](https://groundshift-viewer-production.up.railway.app/?world=/worlds/desk/world.json). Choose **Camera path → Play path** to revisit reconstructed views. [Deployment and public-browser verification](docs/DEPLOYMENT.md).

The catalog makes four usable worlds easy to select: **My desk**, **Dozer · estimated cameras**, **Dozer · supplied cameras**, and **Houseplant**. The desk is a newly reconstructed user recording; the two dozer scenes remain separately identified by their camera inputs, and Houseplant is the licensed viewer sample. Deployment, the complete public file inventory, all four actual scene renders, gallery filters/search and desk path playback have been verified. Superseded low-quality trials remain local.

## Vision
Anyone can record a memorable walk, reconstruct an explorable place, and revisit it later. Eventually separately recorded places can connect into a growing shared world. Pedestrian paths, alleys, corners and stairs matter more than driving routes. Recognizability and spatial continuity matter more than survey accuracy or geometric precision.

## First goal
On a 2022 M2 MacBook Air (16 GB), transform a short original walking video into a locally reconstructed 3D scene and revisit it in a browser. Start with path-constrained movement and free look; unrestricted movement comes later.

## Current experiment: public 360° sequences

The next user-directed experiment uses a small licensed Mapillary panorama
sequence, tests an observed-image Gaussian baseline, and then evaluates local
diffusion-assisted gap completion. Generated views are hypotheses, not new
measurements. Acquisition, actual hardware results, limits and reproducible
commands are recorded in [MAPILLARY_EXPERIMENT.md](docs/MAPILLARY_EXPERIMENT.md).
The original-video path and the four accepted public worlds remain available.
Actual fixed-rig SfM, Metal Gaussian training, local MPS inpainting and generated-
image retraining have executed. The resulting Mapillary scenes remain local
experiments: the new gap-filled world has **not passed visual-quality acceptance**.

## Constraints
- Free and open-source tools; no paid API or cloud GPU.
- Optimize for Apple Silicon and Metal today, not hypothetical CUDA parity.
- Avoid coupling application code to a particular reconstruction engine. Preserve an input/job boundary and a portable world artifact for a future CUDA worker.
- Do not prematurely build cloud services, user accounts, GIS, social features or automatic scene stitching.
- No fabricated benchmarks, camera poses, collision geometry or hardware test results.

## Run the M0 viewer

Requires Node.js 24+ and a WebGL2-capable browser. The validation machine uses Node 25.6.1 and Chrome 156 on Apple M2.

For the complete four-world gallery, first [restore the scene assets and previews from the pinned release](docs/DEPLOYMENT.md#restore-scene-assets-in-a-fresh-checkout). The catalog is tracked; generated assets are ignored. Then run:

```sh
npm ci
npm run dev
```

Open **http://127.0.0.1:4317** and select a scene card. The gallery loads previews; the 3D viewer starts only after selection. For a minimal Houseplant-only M0 check, `npm run sample` supplies that splat and `http://127.0.0.1:4317/?world=/worlds/sample/world.json` opens it directly; this does not restore the full gallery. Once inside a scene, drag to orbit, scroll or use the buttons to zoom, right-drag to pan, and use **Reset view** to return to the manifest camera. The Houseplant example is a real captured Gaussian scene, licensed CC-BY-4.0; its downloader pins and checks the exact asset. See [sample provenance](docs/SAMPLES.md).

To replace the scene, choose **Open world folder** and select a folder containing `world.json` and its asset. Nothing is uploaded. Alternatively put an artifact under `public/worlds/my-world/` and open `/?world=/worlds/my-world/world.json`. See the [world format](docs/WORLD_FORMAT.md) for explicit axes, transform, orbit camera and attribution. No floor, collision or safe walking spawn is inferred.

Worlds with camera metadata also offer **Camera path**: play/pause, forward/backward, speed, checkpoint jumps and free look. Playback stops at unverified gaps; it interpolates recorded views without inventing a walking surface. See [revisit behavior and actual browser evidence](docs/REVISIT.md).

The viewer uses React, TypeScript, Vite, Three.js 0.180.0 and Spark 2.4.0. Loading, download progress, missing or corrupt files, invalid manifests, and graphics-context loss have visible states. Scene switches cancel fetches and release rendering resources. Local development serves code and scenes from this Mac. The [Railway deployment](docs/DEPLOYMENT.md) hosts a curated static viewer; reconstruction remains local. Verified changes and authorized usable scenes are packaged and deployed in the same workflow under the user’s standing instruction.

## Checks

```sh
npm run typecheck
npm run lint
npm test
npm run test:native
npm run build
npm run test:browser
```

Browser tests launch installed **Google Chrome with a visible window**, serve the production build on `127.0.0.1:4318`, and save screenshots/measurements in ignored `test-results/`. Restore the four-world assets and previews above for the complete gallery suite. Optional native-scene checks are explicitly skipped when their artifacts are absent; `npm run sample` alone supplies only the original sample splat. `HEADLESS=1 npm run test:browser` is available for automation but is not equivalent to the recorded headed hardware result. Automated pixel checks are supplemented by actual screenshot inspection.

The catalog release passed TypeScript, lint, **143 viewer/packager tests**, **47 Python tests** including actual HDR pixels, the production build, and **11 headed Chrome tests**. Manual desktop/mobile inspection supplemented the automated checks. These checks reuse measured scene artifacts and do not rerun Metal training. The hosted release was separately verified through all 31 public file hashes and actual public rendering of every selected scene.

## Native reconstruction (M1)

The first local reconstruction is working: **40 licensed images + supplied measured camera poses and sparse point initialization → Brush on M2 Metal → PLY → this viewer**. A 1,500-step run took 80.35 seconds and exported 194,789 Gaussians (17.92 MB). The actual result was visually inspected in Chrome. See [installation, dataset acquisition and exact commands](docs/M1.md).

The backend is a local Python process adapter; the portable output is a directory of scene, manifest, camera metadata and provenance. No server, database or GPU abstraction is involved. The follow-up [CPU PyCOLMAP path](docs/COLMAP.md) now registers **120/120 raw photographs**, using only supplied lens calibration. All camera positions and sparse points are newly estimated locally. A separate 3,000-step Metal run produced 75,397 Gaussians in 155.06 seconds, and its browser result was visually verified. [Independent reconstruction evidence](docs/INDEPENDENT_RECONSTRUCTION.md). The original 16/40 failure and supplied-pose result remain preserved separately.

**M0: PASS. M1: PASS for both the supplied-pose and newly estimated-pose samples.** The latter requires actual lens calibration; calibration-free fisheye reconstruction remains unvalidated. See [validation and remaining limitations](docs/VALIDATION.md) for hardware evidence, screenshots and separately marked PASS / FAIL / NOT RUN results. Image quality is an early prototype: the excavator and surroundings are recognizable, with soft peripheral geometry. Camera-path controls work on real sample poses; original walking-video acceptance remains **NOT RUN**.

## Local video/image pipeline

The first **user-recorded original video** now works locally: a 24.8-second
indoor capture produced 99/99 estimated cameras and a 28,496-Gaussian scene in
4 min 38 s, with actual browser rendering and path playback verified. No sample
model, supplied poses or calibrated lens values were used. The original footage and processing evidence remain private. The creator has
authorized public display of the derived desk scene and preview; the desk now
renders in the public four-world catalog, with path playback verified. [Evidence and remaining
visual limits](docs/ORIGINAL_VIDEO.md).

After installing the native tools, run the new [local pipeline command](docs/PIPELINE.md):

```sh
python3 scripts/build-world.py /absolute/path/to/walk.mov data/jobs/my-walk \
  --duration 15 --fps 4 --max-edge 960 --title "My walk" --id my-walk
```

It prepares frames, estimates cameras on CPU, requires full registration by
default, trains with Brush on Metal, and writes a viewer-ready world. Logs and
failures are preserved. Video provenance can be supplied with `--provenance`;
otherwise the artifact explicitly records an unspecified license and local file
source. Image directories require provenance. This is an implemented workflow,
not a claim that arbitrary footage reconstructs successfully. The FFmpeg checks
initially used synthetic fixtures and a licensed photo slideshow; the later
original indoor capture validates the full command. Walking-route acceptance
and a second independent recording remain outstanding. Tagged phone HDR needs
the [HDR-capable local FFmpeg](docs/HDR_TOOL.md), selected through `--ffmpeg`;
unsupported HDR input fails explicitly. [Frame extraction evidence](docs/VIDEO.md).

## Documentation
- [Vision](docs/VISION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Milestones](docs/IMPLEMENTATION.md)
- [Measured validation](docs/VALIDATION.md)
- [Reconstruction provenance and rerun evidence](docs/RECONSTRUCTION_PROOF.md)
- [Independent camera and scene reconstruction](docs/INDEPENDENT_RECONSTRUCTION.md)
- [Local reconstruction](docs/M1.md)
- [Optional CPU camera estimation](docs/COLMAP.md)
- [One-command local pipeline](docs/PIPELINE.md)
- [Original video reconstruction](docs/ORIGINAL_VIDEO.md)
- [HDR-capable local FFmpeg](docs/HDR_TOOL.md)
- [Video preparation](docs/VIDEO.md)
- [Camera-path revisit](docs/REVISIT.md)
- [Portable world format](docs/WORLD_FORMAT.md)
- [Railway deployment](docs/DEPLOYMENT.md)
- [Agent instructions](AGENTS.md)

Groundshift source license selection remains pending; third-party code and samples retain their respective licenses. Large assets, datasets, generated output and local tools are excluded from Git. Use original or appropriately licensed images and review privacy before publishing footage or scenes.
