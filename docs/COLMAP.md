# Optional local camera estimation

Groundshift can estimate poses from a local image directory with CPU PyCOLMAP. This is an optional preprocessing step for unposed images; the validated first Brush experiment uses the dataset's supplied poses. The CPU smoke test ran successfully, but its largest model registered only 16 of 40 views. It does **not** establish reliable full-dataset pose recovery.

## Installation decision

The [COLMAP installation guide](https://colmap.github.io/install.html) recommends Homebrew on macOS. The [Homebrew formula](https://formulae.brew.sh/formula/colmap) lists an Apple Silicon Tahoe bottle for COLMAP 4.2.1. On this machine, even `brew info colmap` stopped with an unaccepted Xcode license error. No license acceptance or system developer-directory changes were performed.

The official [PyCOLMAP installation guide](https://colmap.github.io/pycolmap/index.html) offers prebuilt macOS wheels. Installing its native arm64 wheel worked without compiling or installing Homebrew dependencies:

```sh
python3.12 -m venv data/tools/colmap-venv
data/tools/colmap-venv/bin/python -m pip install --only-binary=:all: pycolmap==4.2.1
```

The validation machine used Python 3.12.12, PyCOLMAP 4.2.1 and NumPy 2.5.4. Wheel tag: `cp312-cp312-macosx_14_0_arm64`. The installed module reported `has_cuda=False`. Feature extraction, matching and bundle adjustment are explicitly configured for CPU; Metal acceleration is used by Brush, not this step. The [COLMAP library license](https://github.com/colmap/colmap/blob/4.2.1/COPYING.txt) is BSD-3-Clause; its dependencies have separate terms.

## Run on images

```sh
data/tools/colmap-venv/bin/python scripts/estimate-poses.py \
  --images /absolute/path/to/images \
  --output data/jobs/my-poses \
  --provenance /absolute/path/to/provenance.json
```

The output directory must be new. The script performs CPU SIFT extraction, exhaustive matching, incremental mapping, then image undistortion. It preserves every sparse component under `sparse/`, selects the largest registered component for `dataset/`, and reports registered and omitted image names. Inspect coverage before training. Exhaustive matching is intended for small datasets, not long videos or thousands of frames.

The default camera model is COLMAP's `SIMPLE_RADIAL`; it uses available image metadata and COLMAP's intrinsic estimation. For known calibration, pass `--camera-model` and `--camera-params` in COLMAP's documented parameter order. Add `--fix-intrinsics` to retain that calibration during pose estimation; otherwise COLMAP may refine it. Use `--single-camera` only when all images actually share a camera and intrinsics. Defaults are four CPU threads and a 1280-pixel long-edge limit.

The optional provenance file is retained for the Brush adapter; provide the same fields described in [M1](M1.md). A sibling `LICENSE` is also copied when present. The script reads no supplied camera extrinsics. Its output contains:

- `execution.log`: native COLMAP output and Python failures.
- `report.json`: versions, settings, elapsed stage times, process peak resident memory, components and coverage.
- `database.db` and `sparse/`: extraction/matching data and estimated sparse models.
- `dataset/images/` and `dataset/sparse/`: undistorted images and their matching camera models.
- `dataset/transforms.json` and `dataset/init.ply`: estimated cameras and genuine sparse points for Brush.

The transform conversion inverts COLMAP's world-to-camera pose, then negates camera Y/Z to produce OpenGL camera-to-world axes. The source model's world frame is preserved; no measured gravity, metric scale, or walking surface is claimed. See [COLMAP's pose format](https://colmap.github.io/format.html).

The exported dataset passed the reconstruction adapter's input validation. A later Brush run trained these 16 estimated poses on the actual Apple M2 Metal adapter for 1,500 steps at 512-pixel resolution. Training/export **PASS**: 22.509 seconds, 1,048 splats, 97,066-byte PLY. This is a very sparse partial result, and complete 40-view registration remains **FAIL**. Subsequent browser rendering **PASS**, but inspected visual quality **FAIL**: strong blur, stretching and incomplete geometry. Use the supplied-pose dataset for the primary M1 visual result. See [separate browser evidence](VALIDATION.md); the original job record correctly retains its export-time browser NOT RUN status. Native evidence is `data/jobs/dozer-estimated-1500/job.json` and `training.log`.

## Actual CPU smoke test, 2026-11-04

Input: the 40-image licensed dozer subset from [M1](M1.md), already undistorted at 752 × 500. This test discarded supplied extrinsics and reused only its actual pinhole intrinsics. Re-estimating these prepared images is distinct from validating arbitrary raw-camera images and distortion estimation.

```sh
data/tools/colmap-venv/bin/python scripts/estimate-poses.py \
  --images data/datasets/dozer-small/images \
  --output data/validation/colmap/dozer-40 \
  --camera-model PINHOLE \
  --camera-params 194.87574563751383,194.22308338762105,376.0,250.0 \
  --single-camera --max-image-size 752 --threads 4 \
  --provenance data/datasets/dozer-small/provenance.json
```

| Check | Result | Measured evidence |
| --- | --- | --- |
| Native arm64 PyCOLMAP installation/import | PASS | 4.2.1, CUDA absent |
| CPU feature extraction | PASS | 5.365 seconds |
| CPU exhaustive matching | PASS | 13.750 seconds |
| Incremental mapping execution | PASS | 0.389 seconds; two components |
| Complete 40-view registration | FAIL | Largest component 16/40 views; another component has 2 views |
| Largest model | PASS | 641 triangulated points; mean reprojection error 0.4983 pixels |
| Image undistortion/export | PASS | 0.059 seconds; 16 images exported |
| Camera-coordinate conversion | PASS | 16 exported camera matrices round-trip to estimated COLMAP poses with maximum absolute error 0.0 |
| Reconstruction adapter input validation | PASS | Accepted exported image/camera/provenance structure |
| Estimated-pose Brush training/export | PASS | Later 16-view run: actual M2 Metal, 1,500 steps, 1,048 splats, 97,066-byte PLY; sparse partial result |
| Estimated-pose scene browser rendering | PASS rendering / FAIL useful quality | Inspected in headed Chrome; sparse, heavily smeared output; supplied-pose M1 remains the primary visual experiment |
| COLMAP standalone CLI `--help` and SfM | NOT RUN | Homebrew blocked before installation |

Total elapsed time: **19.571 seconds**. Python process peak resident memory: **501,284,864 bytes** (about 478 MiB), measured with `getrusage`; this is the whole-process peak, not an isolated per-stage benchmark. These numbers describe one small run on the current Mac.

Logs and exact command are local, ignored files under `data/validation/colmap/`. `dozer-40/report.json` and `dozer-40/execution.log` preserve the first run. `coordinate-check.json` records coordinate and adapter checks. The script subsequently gained explicit coverage status and terminal warnings; the first run's raw report already records all omitted images and its warning.

The incomplete model is a concrete limitation. Keep the supplied poses for this M1 dataset. Before depending on the unposed-image path, investigate denser overlapping input views, calibration and matching coverage, then verify newly trained output visually. Low reprojection error on 16 registered views does not establish correctness or coverage for the remaining 24.

A targeted retry checked calibration drift after the first run's tiny two-view component optimized its focal lengths far from the provided values. Repeating the same command with a fresh `--output data/validation/colmap/dozer-40-fixed-intrinsics` and `--fix-intrinsics` retained the real calibration but still registered only 16/40 views. It took 22.434 seconds with a 535,756,800-byte process peak and produced 641 points at 0.50084-pixel mean reprojection error. This ruled out that one change as a coverage fix; the cause of incomplete registration is not resolved. Its complete logs/report are retained separately, and `fullRegistration` explicitly reports `FAIL`.

## Cancellation

`SIGINT` (Ctrl-C) and `SIGTERM` finalize the job and interrupted stage as `CANCELLED`, preserve output/logs, and exit with status 130 or 143 respectively. Handlers are installed before writing the first `RUNNING` report. Further termination signals are ignored while the final report is saved. A Python signal handler can be deferred while a native PyCOLMAP call is running, so this does not promise immediate cancellation of a long native operation. An uncatchable `SIGKILL` or machine shutdown cannot guarantee report finalization.

`python3 -m unittest scripts/tests/test_estimate_poses.py -v` exercises actual subprocess signals against a mocked sleeping COLMAP stage. Both signal tests pass and verify final status, exit codes, logs and input preservation. These are lifecycle tests, not GPU or SfM evidence; the actual SfM measurements are listed separately above.

An independent check also sent `SIGTERM` to actual PyCOLMAP feature extraction on the 40 dozer images with one CPU thread and a 512-pixel limit. It exited 143 with both job and stage `CANCELLED`, 1.406 seconds after the signal. The temporary test directory was removed after inspection; the observed summary is retained in `data/validation/colmap/cancellation-check.json`.

## CLI/API verification

Runtime inspection of the installed Python module confirmed these actual entry points: `extract_features(..., extraction_options=..., device=...)`, `match_exhaustive(..., matching_options=..., device=...)`, `incremental_mapping(..., options=...)`, and `undistort_images(...)`. Their signatures and option defaults are retained in `data/validation/colmap/pycolmap-api.txt`. The Groundshift script's `--help` was also executed.

The current upstream [standalone CLI documentation](https://colmap.github.io/cli.html) documents `feature_extractor`, `exhaustive_matcher`, `mapper`, and `image_undistorter`, with CPU switches `--FeatureExtraction.use_gpu 0` and `--FeatureMatching.use_gpu 0`. Those names were checked against current documentation, but were **not** tested against a standalone executable on this Mac. Do not copy older `SiftExtraction.use_gpu`/`SiftMatching.use_gpu` flags into this version without checking its own help.

## FFmpeg scope

Installed FFmpeg **8.0.1** ran `-version`, `-L`, and filter help for `fps` and `scale`. The installed build enables GPL and version 3; its reported license is GPL version 3 or later. The [upstream 8.0.1 filter source documentation](https://github.com/FFmpeg/FFmpeg/blob/n8.0.1/doc/filters.texi) and [license](https://github.com/FFmpeg/FFmpeg/blob/n8.0.1/LICENSE.md) were checked. Output is retained under `data/validation/colmap/ffmpeg-*`.

Actual video frame extraction is **NOT RUN**. Video ingestion remains M2 scope; no frame quality or video reconstruction claim follows from these help checks.
