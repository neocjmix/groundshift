# Original video reconstruction

This experiment uses a video supplied by the user, downloaded from their iCloud
share on 2026-11-04 and processed locally on the M2 MacBook Air. The acquired MOV
is 24.8 seconds, 40,287,012 bytes, HEVC Main 10 at 30 fps, with BT.2020 HLG and a
Dolby Vision compatible base layer. Its stored dimensions are 1920×1080; the
display matrix makes it portrait 1080×1920.

The input contains images, not supplied camera positions, calibrated lens
parameters, sparse geometry or a Gaussian model. CPU PyCOLMAP estimates the
intrinsics, poses and initial points; Brush trains new Gaussians using Metal.
The download archive and MOV are hashed locally. Whether iCloud transcoded the
file before download is not independently verified.

## Final executed result — 2026-11-05

**PASS: original video to a recognizable local browser scene.** No supplied
calibration, poses, point cloud or existing Gaussian scene was used.

| Gate | Result | Actual observation |
| --- | --- | --- |
| HDR preparation | PASS | CPU zscale/Mobius → sRGB; 99 frames, 540×960, 10,295,300 image bytes, 6.917 s |
| New camera estimation | PASS | 99/99 views in one component; 16,318 new points, 38.642 s; 0.55446 px mean reprojection error |
| Native training/export | PASS | Apple M2 Metal, 4,000 steps at 960px; 231.405 s; 28,496 Gaussians, 2,622,283 bytes |
| Whole video command | PASS | 277.572 s (about 4 min 38 s), including preparation, estimation and training |
| Independent evidence readback | PASS | 11 gates: hashes, color evidence, raw/exported poses, world transform, sequence and Metal/PLY output |
| Actual browser rendering | PASS | Start, middle and final camera views visually inspected; desk/computers recognizable |
| Camera controls | PASS | Forward/reverse play, pause, checkpoint seek, free look, reset and orbit zoom |
| Original MOV playback | PASS | Actual local browser playback advanced to 10.33 s, 1080×1920, no media error |
| Walking-route acceptance / second recording | NOT RUN | This is one indoor desk capture, not two walking recordings |

The maximum individual extraction-child RSS was 178,110,464 bytes. CPU SfM peak
RSS was 670,253,056 bytes. Brush maximum RSS was 339,689,472 bytes and its reported
peak memory footprint was 1,123,812,240 bytes. These are process measurements,
not an isolated GPU-memory or total unified-memory measurement. Timings are one
development run, with a short CPU test suite overlapping training.

The local viewer displayed 60 fps and 0.05 s load/decode at a 1374×1116 drawing
buffer on ANGLE Metal / Apple M2. These are one observed app reading with
uncontrolled cache state, not a performance benchmark. Peripheral smearing,
thin-object streaks and blurred screen text remain; off-route areas are
incomplete. The result demonstrates a recognizable prototype, not a clean
photorealistic model. Expanded render details cover the lower camera controls;
collapse that panel before using zoom/reset.

Use the [pinned HDR-capable FFmpeg](HDR_TOOL.md), [CPU environment](COLMAP.md) and
[Brush installation](M1.md), then run with an original local clip and a new job:

```sh
python3 scripts/build-world.py /absolute/path/input.mov data/jobs/my-video \
  --provenance /absolute/path/private-provenance.json \
  --ffmpeg data/tools/hdr-ffmpeg/ffmpeg-macos-aarch64-v9.0 \
  --ffprobe /opt/homebrew/bin/ffprobe \
  --start 0 --duration 24.8 --fps 4 --max-edge 960 --max-frames 100 \
  --camera-model SIMPLE_RADIAL --matching sequential --overlap 12 --threads 4 \
  --steps 4000 --resolution 960 --max-splats 300000 \
  --title "My original video" --id my-video
```

The actual source produced 99 frames, with nominal sample offsets through
24.5 seconds; the requested cap was 100. Sampling offsets are not measured frame
timestamps. The 99 recovered camera checkpoints have 98 adjacent interpolation
edges; those edges do not establish a straight physical walking route.

Choose `data/jobs/my-video/training/world/` with **Open world folder**. Local
files are not uploaded. The actual job is `data/jobs/desk-video-full-sdr/`.
`pipeline.json` and native reports retain their browser **NOT RUN** marker:
subsequent verification is recorded separately in
`data/validation/desk-20261104/browser-validation.json` and
`full-sdr-final-readback.json`. No native report is retrospectively rewritten.

## Privacy and evidence

Original footage, extracted frames, raw camera reports, full probe metadata and
logs remain in ignored `data/`. The creator has now authorized public display of
the selected derived desk world and its selected preview. This changes the
publication scope for that artifact; it does not make the original footage
public or grant an open redistribution license. All rights remain reserved.
The release uses only a curated scene asset, necessary camera/world metadata,
public provenance and preview, with private paths/source URLs removed.

**Public release: PENDING.** Local execution and browser acceptance above are
complete; the selected artifact is being packaged for the four-world Railway
catalog. See [publication permission and deployment evidence](DEPLOYMENT.md).
Public docs record aggregate measurements and implementation decisions; the
original MOV, extracted images and full processing evidence are not included
in Git or the static release.

The private evidence chain is retained under:

- `data/captures/desk-20261104/`: acquired MOV, archive hash, source hash, full
  probe output and explicit private provenance.
- `data/jobs/desk-video-15s/`: initial 15-second trial and its color-validation
  correction; preserved as an intermediate experiment.
- `data/jobs/desk-video-full-sdr/`: accepted complete video job, all stage logs,
  recovered cameras and final portable world.
- `data/validation/desk-20261104/`: independent hash, coordinate, PLY and native
  execution readback, browser inspection and regression logs.

The private audit compares the original hash to extraction metadata, every
extracted frame hash to the estimator input, raw COLMAP matrices to the exported
camera convention, and the world transform to every viewer camera. It checks
that the asset transform is applied once, ordered adjacent views retain their
continuity flags, and the final PLY matches the actual successful Metal job.
Those checks do not replace visual inspection or calibrated color measurement.

## Preserved initial attempt

The initial 15-second run extracted 60 frames at 540×960, registered all 60 in
one component with 9,872 newly estimated points, then trained 1,500 steps at
512px. CPU estimation took 19.775 s, Brush took 24.298 s, and the whole command
took 49.149 s. Its 11,450-splat PLY was 1,054,051 bytes. Browser inspection showed
a recognizable desk and computers with blurred peripheral geometry.

Its VideoToolbox color conversion remains **NOT RUN for efficacy validation**.
An early synthetic ramp test lost its HDR tags; identical outputs from that
test did not establish a native conversion defect. The earlier rejection and
the subsequent correction are both preserved. Successful execution of a color
filter or output tags alone do not establish correct pixel conversion. This
intermediate result is not the final color-validated deliverable.

## Acceptance scope

An indoor desk capture can demonstrate original video → recovered cameras →
Metal training → a recognizable browser scene. It does not establish a long
walking route, accurate physical dimensions, gravity, collision surfaces,
unseen geometry or performance on arbitrary footage. M4 still requires another
independently recorded input; two runs of this same clip do not count as two
recordings.
