# Independent camera and scene reconstruction — 2026-11-04

**PASS:** 120 raw licensed photographs → locally estimated camera poses and
sparse points → Brush on Apple M2 Metal → PLY → visually inspected browser.
Only the actual lens calibration came from upstream. No upstream camera
extrinsics, sparse geometry, Gaussian scene or training checkpoint entered this
run. This closes the earlier 16/40 registration limitation for this denser,
calibrated input; it does not establish calibration-free reconstruction of
arbitrary images.

## Input provenance

| Input or result | Origin |
| --- | --- |
| 120 JPEGs, 1504 × 1000 | Unchanged `images_2` bytes, uniformly selected from the 359-photo Dozer capture; all CRC and SHA-256 checks passed |
| Lens calibration | Actual upstream `OPENCV_FISHEYE` intrinsics; focal lengths/principal point scaled by 1/2, dimensionless distortion unchanged |
| All 120 camera extrinsics | Newly estimated by CPU PyCOLMAP 4.2.1 on this Mac |
| 30,468 sparse initialization points | Newly triangulated by that CPU job; XYZ/RGB only, not a Gaussian checkpoint |
| 75,397 final Gaussians | Newly trained by Brush 0.3.0 on this Mac's Metal GPU |
| Route ordering | Ordered sampled source filenames; no exact timestamps or measured continuous physical trajectory |
| Original walking video | NOT RUN; this source is photographs |

Source and Apache-2.0 license are pinned to the [NerfBaselines dataset
revision](https://huggingface.co/datasets/nerfbaselines/nerfbaselines-data/tree/6a638951a007c8b47eb8a0301d48b04d18e955cf/nerfstudio).
Attribution: Nerfstudio team and contributors, distributed by NerfBaselines.
[Acquisition details](SAMPLES.md), [CPU commands and failed attempts](COLMAP.md).

## Measured execution

| Stage | Result | Measurement |
| --- | --- | --- |
| Native CPU SfM | PASS | 120/120 views in one component; 351.298 s total; 1,847,443,456-byte peak process RSS |
| Sparse model | PASS | 30,468 points; mean reprojection error 0.6190 px; mean track length 4.738 |
| Camera conversion | PASS | All 120 OpenGL poses round-trip to the estimated COLMAP matrices with maximum absolute error 0.0 |
| Native Metal training | PASS | 3,000 steps, 768px maximum image dimension, 300,000-splat budget; 155.061 s; exit 0 |
| Training memory | Measured | 291,340,288-byte maximum RSS; 980,386,656-byte peak memory footprint; not GPU-only usage |
| Gaussian export | PASS | 75,397 splats; 6,937,175-byte PLY |
| Browser rendering and visual inspection | PASS | Excavator, cones, road and buildings visible at first/side views; [actual screenshot](evidence/m1-independent-120.jpg) |
| Route controls | PASS for sampled views | 120 recovered poses, 119 explicitly interpolated edges; playback/pause and keyboard checkpoint movement observed |
| Original video / metric trajectory / floor / held-out quality | NOT RUN | No such evidence inferred from the result |

The two processing stages sum to 506.359 seconds, excluding acquisition,
installation, failed experiments, agent inspection and time between commands.
They were normal development runs, not isolated cold-machine benchmarks.
Peripheral geometry remains blurred/stretched and unseen views can be poor.
The browser inspection was not a controlled FPS measurement; another small
training job began during later inspection.

Final scene SHA-256:
`67f64ebeea5fc8cdae8ea65f01e0f4d060291d120bb5656311cad6bdd0b67229`.

The original 40-photo supplied-pose scene is preserved separately with its
original hash and logs. Do not confuse it with this new independently estimated
scene. The [earlier audit](RECONSTRUCTION_PROOF.md) describes that original run.

## Reproduction

Install [Brush](M1.md) and [PyCOLMAP](COLMAP.md), acquire the raw sample, then use
the local pipeline. Output directories must be new:

```sh
python3 scripts/fetch-reconstruction-sample.py --unposed --frames 120 \
  --image-scale 2 --output data/datasets/dozer-unposed-120

python3 scripts/build-world.py data/datasets/dozer-unposed-120 data/jobs/dozer-independent-rerun \
  --camera-model OPENCV_FISHEYE \
  --camera-params 536.1409486231145,534.3453482694466,752,500,0.03126218448029553,0.005177020067511987,0.0006640977794272005,0.00010067035656515042 \
  --single-camera --fix-intrinsics --matching sequential --overlap 12 \
  --max-image-size 1504 --threads 4 --steps 3000 --resolution 768 --max-splats 300000 \
  --title "Dozer · locally estimated cameras" --id dozer-independent-120
```

These are source-specific measured lens parameters, not general defaults.
The measured 120-view run executed the estimator and trainer as separate
commands; the wrapper above performs the equivalent stages. The separate
24-view run below exercised the complete wrapper. Reconstruction may not be
bitwise deterministic, so a fresh run need not reproduce the exact PLY hash.

Select the resulting `training/world/` folder in the viewer. For the measured
run, local evidence remains at:

- `data/datasets/dozer-unposed-120/`: byte-identical source images, acquisition hashes and license.
- `data/validation/colmap/dozer-unposed-120-provided-lens.json`: calibration source/hash/scaling.
- `data/validation/colmap/dozer-unposed-120-calibrated-fisheye/`: native log, report, database, sparse model and undistorted training dataset.
- `data/jobs/dozer-independent-120/`: exact Brush command/help, Apple M2 Metal log, memory report, output hash, world and camera metadata.
- `data/validation/m1-independent-browser.json`: actual subsequent browser observations, kept separate from export-time browser NOT RUN.

## Whole-command image check

`scripts/build-world.py` also ran on the first 24 ordered raw photos, with the
same actual lens calibration, sequential overlap 8, 960px CPU input limit and
two CPU threads. **PASS:** all 24 cameras registered before the full-coverage
gate allowed 1,500 Metal training steps at 512px. Total 54.538 s; CPU stage
19.326 s wall time; training 35.142 s. Output: 9,662 splats, 889,554 bytes.
The initial sparse model contained 6,299 points at 0.62136px mean error.
Logs and exact commands are in `data/jobs/dozer-pipeline-24/` and
`data/validation/pipeline/dozer-unposed-24-input.json`.

Subsequent browser rendering **PASS**, but clean revisit quality **FAIL**:
the excavator and cones are identifiable with strong smearing and sparse
peripheral geometry in this small partial capture. See the
[inspected 24-view output](evidence/pipeline-24.jpg) and separate
`data/validation/pipeline/dozer-pipeline-24-browser.json`. The 120-view scene is
the main useful example; successful processing alone does not imply good quality.

This proves the actual image command executes all stages. It does not satisfy
M4's requirement to repeat on a second original walking recording. Video
extraction has separate [real fixture validation](VIDEO.md); no original
walking recording has been supplied yet.
