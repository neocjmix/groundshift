# Groundshift (GS)

Revisit real places as explorable 3D worlds.

**Live demo:** [Independently reconstructed dozer](https://groundshift-viewer-production.up.railway.app/?world=/worlds/independent/world.json) · [Original supplied-pose dozer](https://groundshift-viewer-production.up.railway.app/?world=/worlds/reconstructed/world.json) · [Houseplant](https://groundshift-viewer-production.up.railway.app/). Choose **Camera path → Play path** to revisit reconstructed views. [Deployment and public-browser verification](docs/DEPLOYMENT.md).

## Vision
Anyone can record a memorable walk, reconstruct an explorable place, and revisit it later. Eventually separately recorded places can connect into a growing shared world. Pedestrian paths, alleys, corners and stairs matter more than driving routes. Recognizability and spatial continuity matter more than survey accuracy or geometric precision.

## First goal
On a 2022 M2 MacBook Air (16 GB), transform a short original walking video into a locally reconstructed 3D scene and revisit it in a browser. Start with path-constrained movement and free look; unrestricted movement comes later.

## Constraints
- Free and open-source tools; no paid API or cloud GPU.
- Optimize for Apple Silicon and Metal today, not hypothetical CUDA parity.
- Avoid coupling application code to a particular reconstruction engine. Preserve an input/job boundary and a portable world artifact for a future CUDA worker.
- Do not prematurely build cloud services, user accounts, GIS, social features or automatic scene stitching.
- No fabricated benchmarks, camera poses, collision geometry or hardware test results.

## Run the M0 viewer

Requires Node.js 24+ and a WebGL2-capable browser. The validation machine uses Node 25.6.1 and Chrome 156 on Apple M2.

```sh
npm ci
npm run sample
npm run dev
```

Open **http://127.0.0.1:4317**. Drag to orbit, scroll or use the buttons to zoom, right-drag to pan, and use **Reset view** to return to the manifest camera. The Houseplant example is a real captured Gaussian scene, licensed CC-BY-4.0; its downloader pins and checks the exact asset. See [sample provenance](docs/SAMPLES.md).

To replace the scene, choose **Open world folder** and select a folder containing `world.json` and its asset. Nothing is uploaded. Alternatively put an artifact under `public/worlds/my-world/` and open `/?world=/worlds/my-world/world.json`. See the [world format](docs/WORLD_FORMAT.md) for explicit axes, transform, orbit camera and attribution. No floor, collision or safe walking spawn is inferred.

Worlds with camera metadata also offer **Camera path**: play/pause, forward/backward, speed, checkpoint jumps and free look. Playback stops at unverified gaps; it interpolates recorded views without inventing a walking surface. See [revisit behavior and actual browser evidence](docs/REVISIT.md).

The viewer uses React, TypeScript, Vite, Three.js 0.180.0 and Spark 2.4.0. Loading, download progress, missing or corrupt files, invalid manifests, and graphics-context loss have visible states. Scene switches cancel fetches and release rendering resources. Local development serves code and scenes from this Mac. The optional [Railway deployment](docs/DEPLOYMENT.md) hosts a curated static viewer; reconstruction remains local.

## Checks

```sh
npm run typecheck
npm run lint
npm test
npm run test:native
npm run build
npm run test:browser
```

Browser tests launch installed **Google Chrome with a visible window**, serve the production build on `127.0.0.1:4318`, and save screenshots/measurements in ignored `test-results/`. Run `npm run sample` first. The optional reconstruction test is explicitly skipped until `public/worlds/reconstructed/scene.ply` exists. `HEADLESS=1 npm run test:browser` is available for automation but is not equivalent to the recorded headed hardware result. Automated pixel checks are supplemented by actual screenshot inspection.

## Native reconstruction (M1)

The first local reconstruction is working: **40 licensed images + supplied measured camera poses and sparse point initialization → Brush on M2 Metal → PLY → this viewer**. A 1,500-step run took 80.35 seconds and exported 194,789 Gaussians (17.92 MB). The actual result was visually inspected in Chrome. See [installation, dataset acquisition and exact commands](docs/M1.md).

The backend is a local Python process adapter; the portable output is a directory of scene, manifest, camera metadata and provenance. No server, database or GPU abstraction is involved. The follow-up [CPU PyCOLMAP path](docs/COLMAP.md) now registers **120/120 raw photographs**, using only supplied lens calibration. All camera positions and sparse points are newly estimated locally. A separate 3,000-step Metal run produced 75,397 Gaussians in 155.06 seconds, and its browser result was visually verified. [Independent reconstruction evidence](docs/INDEPENDENT_RECONSTRUCTION.md). The original 16/40 failure and supplied-pose result remain preserved separately.

**M0: PASS. M1: PASS for both the supplied-pose and newly estimated-pose samples.** The latter requires actual lens calibration; calibration-free fisheye reconstruction remains unvalidated. See [validation and remaining limitations](docs/VALIDATION.md) for hardware evidence, screenshots and separately marked PASS / FAIL / NOT RUN results. Image quality is an early prototype: the excavator and surroundings are recognizable, with soft peripheral geometry. Camera-path controls work on real sample poses; original walking-video acceptance remains **NOT RUN**.

## Local video/image pipeline

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
used synthetic fixtures and a licensed photo slideshow; no original walking
recording has been processed yet. [Frame extraction evidence](docs/VIDEO.md).

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
- [Video preparation](docs/VIDEO.md)
- [Camera-path revisit](docs/REVISIT.md)
- [Portable world format](docs/WORLD_FORMAT.md)
- [Railway deployment](docs/DEPLOYMENT.md)
- [Agent instructions](AGENTS.md)

Groundshift source license selection remains pending; third-party code and samples retain their respective licenses. Large assets, datasets, generated output and local tools are excluded from Git. Use original or appropriately licensed images and review privacy before publishing footage or scenes.
