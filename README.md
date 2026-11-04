# Groundshift (GS)

Revisit real places as explorable 3D worlds.

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

Requires Node.js 22.12+ and a WebGL2-capable browser. The validation machine uses Node 25.6.1 and Chrome 156 on Apple M2.

```sh
npm ci
npm run sample
npm run dev
```

Open **http://127.0.0.1:4317**. Drag to orbit, scroll or use the buttons to zoom, right-drag to pan, and use **Reset view** to return to the manifest camera. The Houseplant example is a real captured Gaussian scene, licensed CC-BY-4.0; its downloader pins and checks the exact asset. See [sample provenance](docs/SAMPLES.md).

To replace the scene, choose **Open world folder** and select a folder containing `world.json` and its asset. Nothing is uploaded. Alternatively put an artifact under `public/worlds/my-world/` and open `/?world=/worlds/my-world/world.json`. See the [world format](docs/WORLD_FORMAT.md) for explicit axes, transform, orbit camera and attribution. No floor, collision or safe walking spawn is inferred.

The viewer uses React, TypeScript, Vite, Three.js 0.180.0 and Spark 2.4.0. Loading, download progress, missing or corrupt files, invalid manifests, and graphics-context loss have visible states. Scene switches cancel fetches and release rendering resources. All runtime code and scene assets are served locally.

## Checks

```sh
npm run typecheck
npm run lint
npm test
npm run build
npm run test:browser
```

Browser tests launch installed **Google Chrome with a visible window**, serve the production build on `127.0.0.1:4318`, and save screenshots/measurements in ignored `test-results/`. Run `npm run sample` first. The optional reconstruction test is explicitly skipped until `public/worlds/reconstructed/scene.ply` exists. `HEADLESS=1 npm run test:browser` is available for automation but is not equivalent to the recorded headed hardware result. Automated pixel checks are supplemented by actual screenshot inspection.

M0 has been rendered and visually verified on the target M2. Native reconstruction integration is the next milestone.

## Documentation
- [Vision](docs/VISION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Milestones](docs/IMPLEMENTATION.md)
- [Agent instructions](AGENTS.md)

Groundshift source license selection remains pending; third-party code and samples retain their respective licenses. Large assets, datasets, generated output and local tools are excluded from Git. Use original or appropriately licensed images and review privacy before publishing footage or scenes.
