# Implementation plan

Each milestone must report PASS / FAIL / NOT RUN. Build success does not prove GPU training or visual rendering.

## Current status — 2026-11-05

| Milestone / acceptance boundary | Result | Evidence |
| --- | --- | --- |
| M0 licensed sample, controls, errors, replaceable artifact and actual M2 rendering | PASS | 165 viewer/packager tests, 22 local headed Chrome tests, inspected desktop/mobile views; original M0 hardware evidence in [VALIDATION.md](VALIDATION.md) and current release checks in [DEPLOYMENT.md](DEPLOYMENT.md) |
| M1 local image input, obtained real camera poses, native Metal training, PLY export and viewer rendering | PASS | 40-image dozer dataset, 1,500 steps, 80.35-second job, 194,789 splats; [M1.md](M1.md) |
| New CPU pose estimation and training on raw images | PASS with supplied lens calibration | 120/120 newly estimated poses, 30,468 new sparse points, 3,000 Metal steps and actual browser inspection; [evidence](INDEPENDENT_RECONSTRUCTION.md). Earlier 16/40 failure remains recorded |
| User-requested static Railway observation surface | PASS for previous 13-scene release; 15-scene release pending | Previous 89 public file hashes matched and all 13 scenes visibly rendered; new local 15-scene package and browser checks are described in [DEPLOYMENT.md](DEPLOYMENT.md) after publication. Push-triggered autodeploy remains unverified; the explicit connector trigger deployed the previous release |
| Two-endpoint panorama generation and GS comparison | PASS for local 65-frame MLX interpolation, Metal exports and Chrome rendering; 3D quality FAIL | Two licensed photos → 65 2048×1024 frames; matched real-only and generated-view GS worlds both ran 10,000 Metal steps. At two held-out real-photo views, generated-view GS had higher pixel error and visibly streaked geometry. Full video diffusion NOT RUN; [PANORAMA_VIDEO_EXPERIMENT.md](PANORAMA_VIDEO_EXPERIMENT.md) |
| Original user video → local scene | PASS for indoor desk capture | 99/99 newly estimated cameras, 4,000 Metal steps, inspected browser result; [evidence](ORIGINAL_VIDEO.md) |
| M2 original walking video | NOT RUN for walking acceptance | Real indoor video pipeline works; an actual walking-route capture remains outstanding |
| M3 camera-path controls on real sample | PASS for sample behavior | Actual supplied camera poses, interpolation/free look and gap tests; [REVISIT.md](REVISIT.md). Original walking-route continuity remains NOT RUN |
| M4 local video/image command | PASS for one original video; full milestone NOT RUN | Full private video command completed in 277.57 s; a second independently recorded input remains outstanding; [PIPELINE.md](PIPELINE.md) |

Implementation decisions: use the official Brush arm64 release, optional PyCOLMAP CPU wheels instead of requiring the Homebrew executable, and supplied measured poses for the first M1 acceptance run. Undistort the sample's actual fisheye images before Brush because its released importer does not handle their distortion. Preserve reconstruction internals in the native process and use the explicit v1 world format at the viewer boundary. These decisions keep the initial local-only design intact.

The earlier four-world 2026-11-05 catalog update added the accepted desk artifact alongside both dozer reconstructions and Houseplant. It passed 143 viewer/packager tests, 47 Python tests including actual HDR conversion, and 11 headed Chrome checks. In that earlier release, source footage and superseded trials remained local; the creator authorized public display of the derived desk scene. That historical Railway release passed all 31 public file hashes, all four scene renders and public gallery controls. The current observation release expands it to 13 scenes and 72 stage records under the policy below. Neither release's regression checks imply another native reconstruction execution.

## Observation publication policy — 2026-11-05

The user's latest instruction replaces the earlier usable-scene release filter.
Railway is an observation surface: all distinct exported trials are published,
including poor-quality or superseded results, with failed/cancelled stage evidence
and real/generated image comparisons. Execution, rendering and quality remain
separate PASS / FAIL / NOT RUN boundaries. Reconstruction remains local and private
inputs/model weights are not release files. See [current deployment evidence](DEPLOYMENT.md).

## User-directed panorama experiment

The user-directed Mapillary work uses a small consecutive licensed 360° sample,
reports actual spacing without claiming a global density maximum, and keeps
observed and generated pixels distinct. The first nine-panorama experiment
executed local fixed-rig SfM, stereo/inpainting, generated-image retraining and
browser viewing; it did not produce an accepted scene. The follow-up placed
two source panoramas at the ends of a 65-frame MLX interpolation, withheld the
middle photograph's RGB for comparison, and added the generated midpoint as
six Gaussian training views. This run established a working 2D video and two
working exported worlds, but did not improve the 3D scene. See
[the first experiment](MAPILLARY_EXPERIMENT.md) and
[the two-endpoint result](PANORAMA_VIDEO_EXPERIMENT.md). The current blocker is
useful geometric/appearance consistency between physical capture positions,
not an unexecuted GPU pipeline. Exact street fidelity is secondary to plausible
generated scenery; invented camera poses remain prohibited.

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
Unrestricted navigation, connecting places, sharing, cloud CUDA workers, privacy
redaction. Missing-view generation is now the bounded experiment described above.
