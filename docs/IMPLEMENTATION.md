# Implementation plan

Each milestone must report PASS / FAIL / NOT RUN. Build success does not prove GPU training or visual rendering.

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
