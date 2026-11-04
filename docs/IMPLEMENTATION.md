# Implementation plan

Each milestone must report PASS / FAIL / NOT RUN. Build success does not prove GPU training or visual rendering.

## Current status — 2026-11-05

| Milestone / acceptance boundary | Result | Evidence |
| --- | --- | --- |
| M0 licensed sample, controls, errors, replaceable artifact and actual M2 rendering | PASS | 118 automated viewer tests; 4 production Chrome tests and inspected screenshots in [VALIDATION.md](VALIDATION.md) |
| M1 local image input, obtained real camera poses, native Metal training, PLY export and viewer rendering | PASS | 40-image dozer dataset, 1,500 steps, 80.35-second job, 194,789 splats; [M1.md](M1.md) |
| New CPU pose estimation and training on raw images | PASS with supplied lens calibration | 120/120 newly estimated poses, 30,468 new sparse points, 3,000 Metal steps and actual browser inspection; [evidence](INDEPENDENT_RECONSTRUCTION.md). Earlier 16/40 failure remains recorded |
| User-requested static Railway viewer | PASS | Public HTTPS, 14 file hashes, both scene renders and controls; [DEPLOYMENT.md](DEPLOYMENT.md) |
| Original user video → local scene | PASS for indoor desk capture | 99/99 newly estimated cameras, 4,000 Metal steps, inspected browser result; [evidence](ORIGINAL_VIDEO.md) |
| M2 original walking video | NOT RUN for walking acceptance | Real indoor video pipeline works; an actual walking-route capture remains outstanding |
| M3 camera-path controls on real sample | PASS for sample behavior | Actual supplied camera poses, interpolation/free look and gap tests; [REVISIT.md](REVISIT.md). Original walking-route continuity remains NOT RUN |
| M4 local video/image command | PASS for one original video; full milestone NOT RUN | Full private video command completed in 277.57 s; a second independently recorded input remains outstanding; [PIPELINE.md](PIPELINE.md) |

Implementation decisions: use the official Brush arm64 release, optional PyCOLMAP CPU wheels instead of requiring the Homebrew executable, and supplied measured poses for the first M1 acceptance run. Undistort the sample's actual fisheye images before Brush because its released importer does not handle their distortion. Preserve reconstruction internals in the native process and use the explicit v1 world format at the viewer boundary. These decisions keep the initial local-only design intact.

## M0 — Viewer
Create React + TypeScript + Vite viewer using Three.js and Spark. Load a licensed sample splat, support orbit/reset and errors. Verify actual rendering on M2 MacBook Air (16 GB), record FPS, browser, asset size.

## M1 — Local reconstruction
Verify current Brush build and Metal support, output formats, COLMAP macOS CPU alignment. Train on a small licensed multi-view dataset. Render result in viewer. Record commands, logs, duration, peak memory and failures. Evaluate another native Metal trainer only if Brush fails in practice.

## M2 — Original walking video
Start with a steady 10–15 second recording and approximately 30–60 frames at 960px long edge, adjusting from real observations. Verify recognizable scene and reconstructed camera poses.

## M3 — Revisit interaction
Follow recovered camera path forward/backward with free look, reset and speed control. Verify spatial continuity. Do not invent floor/collision from splats. Free walking is deferred.

## M4 — One-command pipeline
Video path -> frame preparation -> reconstruction -> artifact validation -> viewer-ready files. Repeat with a second recording without manual 3D modeling.

## Evidence
Record machine, OS, tool versions, capture duration/resolution, frame count, alignment, training time, total time, peak memory, artifact size, browser FPS, visual issues and PASS/FAIL/NOT RUN.

## Deferred
Unrestricted navigation, missing-view generation, connecting places, sharing, cloud CUDA workers, privacy redaction.
