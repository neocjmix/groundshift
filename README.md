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

## Candidate stack
- FFmpeg for frames.
- COLMAP for camera estimation where needed; CPU matching on macOS as necessary.
- Brush (Rust/WebGPU) for 3D Gaussian Splatting training, subject to actual Metal build/export validation.
- React, TypeScript, Vite, Three.js and Spark for the viewer.
- Local CLI and filesystem for orchestration and assets.

These are candidates, not a verified end-to-end pipeline.

## Documentation
- [Vision](docs/VISION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Milestones](docs/IMPLEMENTATION.md)
- [Agent instructions](AGENTS.md)

Status: design only. License selection pending. Use original or appropriately licensed images and review privacy before publishing footage or scenes.
