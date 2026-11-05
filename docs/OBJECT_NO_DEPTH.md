# Scooter ablation: no learned monocular depth

The same nine real training images from the [preceding real-only trial](OBJECT_REAL_ONLY.md)
are used again. Intermediate image interpolation and diffusion remain absent.
This trial additionally removes learned-depth inference, depth calibration and
depth-to-point-cloud fusion. It initializes Brush using only triangulated SfM
points from the original-image camera reconstruction.

## Controlled inputs

The actual nine training PNG files and `transforms.json` are copied byte for byte
from the preceding run and checked by SHA-256. The previous COLMAP preprocessing
border difference therefore does not apply between these two trials. The original
image-estimated camera poses are reused, not estimated again. Scale is arbitrary.

The same three observed-image object rectangles select 115 of 671 triangulated
points. This retains the object selection used for the preceding dense cloud;
it is not a baseline initialized with the entire unselected SfM scene. RGB inputs
still contain background, as before. Brush 0.3.0, resolution 512, 5,000 steps,
maximum 150,000 splats, SH degree 1 and seed 42 are unchanged. No learned-depth
arrays are read by the runner. The same rectangles select trained Gaussian
centers for the separate object export; large Gaussian extents can remain.

The previous display camera is reused only for side-by-side presentation after
checking coordinate transforms match. It does not enter initialization or
training. The preceding point cloud is included only as a comparison visualization.

## Actual local result

| Recorded observation | With learned depth | Without learned depth |
| --- | ---: | ---: |
| Real / generated training images | 9 / 0 | 9 / 0 |
| Contributing depth maps | 9 | 0 |
| Initial points | 41,533 | 115 |
| Metal training seconds | 160.298 | 116.339 |
| Full export Gaussians | 46,807 | 569 |
| Object selection Gaussians | 43,268 | 237 |

The native log confirms Apple M2 / Metal. The full PLY is 52,997 bytes, SHA-256
`c057c83eecd504a0e2a9e0d837af9b17e8d94cb57b6309e81df14378063236e9`.
The process reports maximum resident set 172,638,208 bytes and peak memory
footprint 283,132,696 bytes; these are process counters, not a measurement of
total system or GPU unified-memory use. Times describe single runs, not repeated
performance benchmarks.

Actual Chrome rendering shows severe blurring and stretched splats: the scooter's
shape is substantially less defined in this home view. Export/render execution
passes, but a recognizable complete object has not been achieved. This result
supports keeping dense initialization for this particular recipe; it does not
establish that all no-learned-depth GS pipelines are worse. No retuning, extra
steps or alternative initialization was performed in this controlled trial.

## Reproduction and evidence

Use the existing original-only posed job and native environments from the
preceding experiment. Run into a new directory:

```sh
data/tools/colmap-venv/bin/python scripts/run-object-no-depth.py \
  data/jobs/object-focus-real-only-20261105 data/jobs/object-no-depth-NEW
data/tools/venv/bin/python scripts/publish-object-no-depth.py \
  data/jobs/object-no-depth-NEW
# Capture actual viewer previews for scooter-nodepth-context and scooter-nodepth-object.
data/tools/venv/bin/python scripts/publish-object-no-depth.py \
  data/jobs/object-no-depth-NEW --finish
```

The existing licensed Cicero101 / Mapillary via Wikimedia Commons photographs
remain CC BY-SA 4.0. No new dataset or model download is needed. The acquisition
recipe is linked from [the original object experiment](OBJECT_FOCUS_EXPERIMENT.md).
Raw evidence is retained in `data/jobs/object-no-depth-20261105/`: `ablation.json`,
`dataset/`, `training/job.json`, native logs and actual browser screenshots.
The public package contains licensed crops, compact point clouds, both exports
and the comparison, without local paths, model weights or raw execution logs.

**PASS:** native Metal execution, exact training image/camera equality,
TypeScript, production build, lint, 165 JS tests and actual local rendering of
both new scenes. Python suites each ran 106 tests: OpenCV environment had five
dependency skips, PyCOLMAP had 31. The first local report check timed out waiting
for comparison images; an unchanged rerun decoded both and passed all report
controls and chronological ordering. This does not establish a root cause for
the initial timeout. **NOT RUN:** independent geometry accuracy, quantitative image
quality comparison and the full historical browser regression suite. Learned
monocular depth and intermediate generation were intentionally not executed.
Public deployment and post-publication checks are recorded in [DEPLOYMENT.md](DEPLOYMENT.md).

## Public result

[Side-by-side comparison](https://groundshift-viewer-production.up.railway.app/experiments/object-nodepth/)
· [New object GS](https://groundshift-viewer-production.up.railway.app/?world=/worlds/scooter-nodepth-object/world.json)
· [Chronological lab](https://groundshift-viewer-production.up.railway.app/experiments/lab/).

Railway deployment succeeded. Public headed Chrome rendered both new exports,
operated report controls and verified newest/oldest sorting without page errors.
All 64 selected new/shared files matched the release hashes; health check passed.
The screenshots confirm the poor visual result is present in the actual deployed
artifact. The complete-object quality target is **FAIL**, not rescued by successful
export or deployment. See the [release record](DEPLOYMENT.md#scooter-without-learned-depth--2026-11-05).
