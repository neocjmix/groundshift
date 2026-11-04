# Revisit recovered camera views

The viewer now loads optional `cameras.json` and offers **Orbit** and **Camera
path** modes. Camera path supports forward/backward playback, pause, speed in
views per second, a view slider, previous/next checkpoints, free look and reset.
Positions interpolate linearly and rotations use shortest-arc quaternion
interpolation. No floor, collision surface or metric walking speed is inferred.

Only edges explicitly marked by the exporter can play continuously. Unknown
continuity and different reconstruction components stop playback; previous/next
can explicitly jump between checkpoints. Malformed or unavailable camera
metadata shows a warning while leaving orbit usable. Scene replacement cancels
camera metadata loading and disposes the old controls.

## Actual local verification — 2026-11-04

The existing 194,789-splat Metal-trained Dozer scene was inspected in the local
browser at its real supplied camera poses. The PLY and all 40 camera matrices
are unchanged. A metadata-only export attached the original sampled filename
order and the single supplied COLMAP component ID, permitting 39 interpolated
edges. This did not retrain the scene or newly estimate camera positions.

Playback advanced from camera 1 to progress 7.2506 (between cameras 8 and 9),
and pause retained that position. The excavator, cones, road and building remain
recognizable in the [inspected interpolated view](evidence/m3-interpolated-view.jpg).
Peripheral geometry is soft and stretched, consistent with the short training
run. The sample demonstrates moving between recovered views; it is not an
original walking-video acceptance test or proof of a measured continuous route.

The automated headed Chrome path test uses the actual scene and camera matrices
with **test-only continuity markers and an artificial gap**. It checks playback,
pause, speed, reverse, free look, reset, checkpoint jumps and stopping at the
gap. Those markers verify navigation behavior, not physical continuity. Unit
tests separately cover rigid matrices, world units, omitted edges, disconnected
components, interpolation and cancellation.

Raw live observations are in ignored `data/validation/m3-live-path.json`.
Metadata-only export inputs and report are in
`data/jobs/dozer-revisit-export/`; the original training result stays in
`data/jobs/dozer-1500/`. Future reconstruction commands can pass `--sequence`
and `--component-id` to generate the same contract directly. The
[one-command pipeline](PIPELINE.md) does this automatically when an ordered
source sequence is present.

**M3 navigation behavior on the licensed sample: PASS. Original walking-route
continuity: NOT RUN.** An actual walking recording is needed for that acceptance
gate; the UI does not create missing capture evidence.
