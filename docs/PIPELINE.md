# Local world command

`scripts/build-world.py` chains local frame extraction (for video), CPU camera
estimation, a registration coverage gate, and Brush Metal training. It creates a
new directory and keeps stage commands, logs, exit codes and measurements in
`pipeline.json`. It does not start a server or upload input.

Install the [M1 tools](M1.md) and [PyCOLMAP environment](COLMAP.md) first. Video
also needs local `ffmpeg` and `ffprobe`; see [video preparation](VIDEO.md).

```sh
python3 scripts/build-world.py /absolute/path/to/walk.mov data/jobs/my-first-walk \
  --duration 15 --fps 4 --max-edge 960 \
  --provenance /absolute/path/to/provenance.json \
  --title "My first walk" --id my-first-walk
```

For images, pass an image directory or a dataset containing `images/`. A sibling
`provenance.json` or `--provenance` is required. Use `--single-camera` only when
the images share intrinsics. Video enables this assumption automatically; zoom
changes, mixed cameras or stabilization can violate it. The default camera
model is `SIMPLE_RADIAL`; `--camera-model OPENCV` allows a more flexible lens
model. By default no supplied calibration is imported. If actual lens
calibration exists, `--camera-params` supplies it in the selected COLMAP model's
order and `--fix-intrinsics` keeps it fixed. Record its source and resize scaling;
do not guess values and call them measured. Supplied poses and point clouds are
never imported by this command. Sequential matching is optional (`--matching sequential --overlap 12`)
and only appropriate for a correctly ordered overlapping capture.

By default **all input images must register in the selected component** before
training starts. A partial run retains its CPU output and fails the command.
`--min-coverage 0.95` explicitly relaxes this gate, but does not turn partial
registration into full registration or establish visual quality. Image coverage
alone cannot detect every incorrect reconstruction. Inspect the camera report
and the rendered result.

Successful output is `data/jobs/my-first-walk/training/world/`. Choose **Open
world folder** in the viewer and select that directory. Optional `--publish
public/worlds/my-first-walk` copies the world into a **new local** directory for
HTTP viewing; this is not remote publishing. Never publish private captures
without reviewing them.

`pipeline.json` deliberately leaves `browserRendering` and `visualQuality` as
**NOT RUN**. A subsequent browser inspection is a separate acceptance gate.
Failures do not start later stages. Ctrl-C/SIGTERM propagates to the active
adapter, which terminates its native child and preserves its report. Prior job
and publication directories are never overwritten.

## Camera sequence

Video preparation writes a source `sequence.json`. Image inputs may provide the
same file, `selected-frames.json` from the sample acquisition command, or an
explicit `--sequence` file. It must contain an ordered `frames` array whose
`file` values exactly match the estimator's `images/<filename>` paths.

The exporter orders genuine recovered cameras by that list and marks only
consecutive surviving entries in the selected SfM component for interpolation.
Missing registered views break playback. Without an explicit source sequence,
the viewer offers individual camera checkpoints only. This describes
interpolated views, not measured ground, collision surfaces, metric speed, or a
continuous physical walking trajectory. [World contract](WORLD_FORMAT.md).

## Acceptance limits

The original-video milestone requires an actual short walking recording. A
video made from existing sample photos is useful for extraction checks but
does not satisfy that requirement. A complete second-recording run is also
required before claiming M4 acceptance. See [current validation](VALIDATION.md)
for executed checks and remaining blockers.
