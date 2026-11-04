# Optional local camera estimation

Groundshift can estimate poses from a local image directory with CPU PyCOLMAP. The latest native experiment registered **120/120 raw images in one model**, recovering every camera pose and 30,468 sparse points locally. It used the capture's provided lens calibration, but no supplied camera poses, sparse points or Gaussian model. Full pose recovery **PASS** applies to this calibrated dataset; fully uncalibrated reconstruction remains unverified. The earlier 40-view experiment registered only 16/40, and those earlier results are retained below.

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

The default camera model is COLMAP's `SIMPLE_RADIAL`; it uses available image metadata and COLMAP's intrinsic estimation. Select a model appropriate to the lens using the [upstream camera-model guidance](https://colmap.github.io/cameras.html). The installed version rejects fisheye image pairs when no focal-length prior is available: choosing `SIMPLE_RADIAL_FISHEYE` alone is insufficient for uncalibrated images without focal metadata. For known calibration, pass `--camera-model` and `--camera-params` in COLMAP's documented parameter order. Add `--fix-intrinsics` to retain that calibration during pose estimation; otherwise COLMAP may refine it. Use `--single-camera` only when all images actually share a camera and intrinsics. Defaults are four CPU threads and a 1280-pixel long-edge limit.

For ordered video frames or a photo sequence, use `--matching sequential --overlap 12`. This matches neighboring filenames and quadratic neighbors using the installed `SequentialPairingOptions` API. Vocabulary-tree loop detection stays disabled, so this option downloads no model and calls no service. Exhaustive matching remains the default for small unordered collections. `--guided-matching` uses verified image-pair geometry to search for additional correspondences. `--max-features` controls the requested SIFT feature count (default 8,192); multiple feature orientations can yield a larger descriptor count. `--affine-features` enables affine shape estimation and domain-size pooling, a slower option recommended upstream for difficult matching. These controls were verified against both the installed PyCOLMAP 4.2.1 API and [current upstream guidance](https://colmap.github.io/faq.html#increase-number-of-matches-sparse-3d-points).

The optional provenance file is retained for the Brush adapter; provide the same fields described in [M1](M1.md). A sibling `LICENSE` is also copied when present. The script reads no supplied camera extrinsics. Its output contains:

- `execution.log`: native COLMAP output and Python failures.
- `report.json`: versions, settings, elapsed stage times, process peak resident memory, components and coverage.
- `database.db` and `sparse/`: extraction/matching data and estimated sparse models.
- `dataset/images/` and `dataset/sparse/`: undistorted images and their matching camera models.
- `dataset/transforms.json` and `dataset/init.ply`: estimated cameras and genuine sparse points for Brush.

Reports also preserve input image SHA-256 hashes, feature counts, raw-match and verified-pair counts, match-graph components, estimated camera parameters and mean track length. These diagnostics distinguish feature correspondences, verified pair geometry and successful image registration; none alone guarantees visually useful training. If `sequence.json` exists beside the input `images/` folder, it is copied unchanged to the prepared dataset. It retains omitted input frames so a route consumer can stop at registration gaps rather than fabricate continuity.

The transform conversion inverts COLMAP's world-to-camera pose, then negates camera Y/Z to produce OpenGL camera-to-world axes. The source model's world frame is preserved; no measured gravity, metric scale, or walking surface is claimed. See [COLMAP's pose format](https://colmap.github.io/format.html).

The **historical 16-view export** passed the reconstruction adapter's input validation. A later Brush run trained those 16 estimated poses on the actual Apple M2 Metal adapter for 1,500 steps at 512-pixel resolution. Training/export **PASS**: 22.509 seconds, 1,048 splats, 97,066-byte PLY. This was a very sparse partial result, and complete 40-view registration remained **FAIL**. Subsequent browser rendering **PASS**, but inspected visual quality **FAIL**: strong blur, stretching and incomplete geometry. The first successful M1 visual result therefore used supplied poses. See [separate browser evidence](VALIDATION.md); the original job record correctly retains its export-time browser NOT RUN status. Native evidence is `data/jobs/dozer-estimated-1500/job.json` and `training.log`. These historical results describe neither the newer 120-view model nor its eventual training quality.

## Historical 40-view CPU smoke test, 2026-11-04

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

That incomplete 40-view model is a concrete limitation of the first experiment. Low reprojection error on 16 registered views does not establish correctness or coverage for the remaining 24. The subsequent 120-view experiment below tests denser raw input with the actual lens model; this does not retroactively make the first run successful.

A targeted retry checked calibration drift after the first run's tiny two-view component optimized its focal lengths far from the provided values. Repeating the same command with a fresh `--output data/validation/colmap/dozer-40-fixed-intrinsics` and `--fix-intrinsics` retained the real calibration but still registered only 16/40 views. It took 22.434 seconds with a 535,756,800-byte process peak and produced 641 points at 0.50084-pixel mean reprojection error. This ruled out that one change as a coverage fix; the cause of incomplete registration is not resolved. Its complete logs/report are retained separately, and `fullRegistration` explicitly reports `FAIL`.

## Denser raw-image experiments, 2026-11-04

A separate acquisition, `data/datasets/dozer-unposed-120`, contains 120 unchanged 1504 × 1000 source JPEGs spanning the full 359-image capture. It has the original lens distortion and any original EXIF bytes. Its acquisition reads no source calibration, camera poses or sparse geometry; source indices and hashes are recorded in `selected-frames.json` and `acquisition.json`. These are source photos with ordered filenames, not original video or measured capture timestamps. See [sample acquisition](SAMPLES.md).

The earlier 40-view input produced 3,061–7,171 SIFT descriptors per image and 111 verified pairs. The denser, higher-resolution input produced 9,691–15,808 descriptors per image. More features alone did not resolve camera modeling:

1. **Uncalibrated fisheye: FAIL.** `SIMPLE_RADIAL_FISHEYE`, shared camera, sequential overlap 12 and guided matching took 101.794 seconds (1,841,790,976-byte process peak). There were 713 pairs with raw feature correspondences but zero verified geometries and no reconstructed model. The native warning explains that fisheye focal length cannot be recovered from a fundamental matrix without a prior. The matching API returned, but that is not successful pose recovery. Full evidence: `data/validation/colmap/dozer-unposed-120-fisheye-sequential/`.
2. **Uncalibrated OPENCV self-calibration: CANCELLED.** This used the same input and matching settings, with no supplied camera parameters. Matching slowed to about 19 seconds per image batch. To bound the experiment, SIGINT ended it cleanly with exit 130 after 337.280 seconds total (276.183 seconds in matching; 5,393,891,328-byte process peak). At cancellation, 208 raw-match pairs and 177 verified pairs existed; camera mapping and training were **NOT RUN**. This establishes neither success nor failure of eventual self-calibration. The original report and separate read-only `post-cancellation-diagnostics.json` are retained in `data/validation/colmap/dozer-unposed-120-opencv-sequential/`.

The installed [COLMAP two-view implementation](https://github.com/colmap/colmap/blob/4.2.1/src/colmap/estimators/two_view_geometry.cc) explicitly handles the uncalibrated-fisheye limitation. A known lens calibration is a legitimate separate input; it must be disclosed separately from locally estimated camera poses and sparse points. `data/validation/colmap/dozer-unposed-120-provided-lens.json` records the original calibration source/hash and the exact factor-of-two image scaling: focal lengths and principal point are divided by two, while dimensionless distortion coefficients remain unchanged.

### Calibrated raw-image pose recovery: PASS

The third experiment used the same 120 raw JPEGs and the provided `OPENCV_FISHEYE` lens intrinsics only. Intrinsics were fixed during SfM. SIFT features, pair geometry, camera extrinsics and all sparse points were computed locally. Guided matching was disabled to bound CPU cost; no verification or registration thresholds were relaxed.

```sh
data/tools/colmap-venv/bin/python scripts/estimate-poses.py \
  --images data/datasets/dozer-unposed-120/images \
  --output data/validation/colmap/dozer-unposed-120-calibrated-fisheye \
  --camera-model OPENCV_FISHEYE \
  --camera-params 536.1409486231145,534.3453482694466,752.0,500.0,0.03126218448029553,0.005177020067511987,0.0006640977794272005,0.00010067035656515042 \
  --single-camera --fix-intrinsics --matching sequential --overlap 12 \
  --max-image-size 1504 --threads 4 \
  --provenance data/datasets/dozer-unposed-120/provenance.json
```

Use a fresh output directory for a repeat run. The supplied numerical intrinsics are specific to this dataset at 1504 × 1000; they are not defaults for an arbitrary video or camera.

| Check | Result | Measured evidence |
| --- | --- | --- |
| Input integrity | PASS | All 120 original JPEG SHA-256 hashes agree with acquisition |
| CPU SIFT extraction | PASS | 168.475 seconds |
| Sequential matching | PASS | 147.526 seconds; 709 raw-match pairs, 577 verified pairs; one connected graph |
| Local incremental mapping | PASS | 30.417 seconds; one model with all 120/120 cameras and 30,468 points |
| Registration coverage | PASS | 100%; no omitted views |
| Sparse fit | Measured | Mean reprojection error 0.619025 pixels; mean track length 4.73838 images |
| Undistortion/export | PASS | 4.667 seconds; all 120 views exported |
| Coordinate conversion | PASS | All camera matrices round-trip to estimated COLMAP poses with maximum absolute error 0.0 |
| Sparse initialization | PASS | All 30,468 coordinates finite; XYZ/RGB `init.ply` is 457,199 bytes, with no learned Gaussian attributes |
| Reconstruction adapter input validation | PASS | Accepted exported images, intrinsics, poses and provenance |
| Training/browser acceptance in this SfM report | NOT RUN | Handed to the separate Brush/viewer stages; see their independent evidence |

Total CPU job time was **351.298 seconds** and whole-process peak resident memory was **1,847,443,456 bytes** (about 1.72 GiB). These are actual measurements on the M2; runtime includes the machine's state during this run and is not a controlled cross-engine benchmark. The full logs, report, sparse model and `coordinate-check.json` are retained in `data/validation/colmap/dozer-unposed-120-calibrated-fisheye/`. The viewer-ready reconstruction input is its `dataset/` directory, and its selected model ID is `0`.

After SfM, only the exported provenance note was clarified to state explicitly that lens calibration was provided while all poses and points were locally estimated. Its before/after hashes and reason are preserved in `provenance-export-note.json`; images, geometry, camera matrices and the original run report were unchanged. The script now writes that distinction automatically for future exports and records its command, script hash and explicit calibration/pose/geometry source flags.

This result closes the local pose-estimation gap for this particular calibrated capture. Because input density, resolution, lens handling and matching settings changed together, it does not isolate a single cause of the earlier 16/40 result. It also does not validate unknown cameras, every future walking video, or visual quality after Gaussian training.

## Cancellation

`SIGINT` (Ctrl-C) and `SIGTERM` finalize the job and interrupted stage as `CANCELLED`, preserve output/logs, and exit with status 130 or 143 respectively. Handlers are installed before writing the first `RUNNING` report. Further termination signals are ignored while the final report is saved. A Python signal handler can be deferred while a native PyCOLMAP call is running, so this does not promise immediate cancellation of a long native operation. An uncatchable `SIGKILL` or machine shutdown cannot guarantee report finalization.

`python3 -m unittest scripts/tests/test_estimate_poses.py -v` exercises actual subprocess signals against a mocked sleeping COLMAP stage, empty-model failures, disconnected match diagnostics, provenance distinctions and non-overwriting input validation. All seven tests pass. These are script tests, not GPU or SfM evidence; the actual SfM measurements are listed separately above.

An independent check also sent `SIGTERM` to actual PyCOLMAP feature extraction on the 40 dozer images with one CPU thread and a 512-pixel limit. It exited 143 with both job and stage `CANCELLED`, 1.406 seconds after the signal. The temporary test directory was removed after inspection; the observed summary is retained in `data/validation/colmap/cancellation-check.json`.

## CLI/API verification

Runtime inspection of the installed Python module confirmed these actual entry points: `extract_features(..., extraction_options=..., device=...)`, `match_exhaustive(..., matching_options=..., device=...)`, `match_sequential(..., matching_options=..., pairing_options=..., device=...)`, `incremental_mapping(..., options=...)`, and `undistort_images(...)`. Their signatures and option defaults are retained in `data/validation/colmap/pycolmap-api.txt` and `pycolmap-matching-api.json`. The Groundshift script's `--help` was also executed.

The current upstream [standalone CLI documentation](https://colmap.github.io/cli.html) documents `feature_extractor`, `exhaustive_matcher`, `mapper`, and `image_undistorter`, with CPU switches `--FeatureExtraction.use_gpu 0` and `--FeatureMatching.use_gpu 0`. Those names were checked against current documentation, but were **not** tested against a standalone executable on this Mac. Do not copy older `SiftExtraction.use_gpu`/`SiftMatching.use_gpu` flags into this version without checking its own help.

## FFmpeg scope

Installed FFmpeg **8.0.1** ran `-version`, `-L`, and filter help for `fps` and `scale`. The installed build enables GPL and version 3; its reported license is GPL version 3 or later. The [upstream 8.0.1 filter source documentation](https://github.com/FFmpeg/FFmpeg/blob/n8.0.1/doc/filters.texi) and [license](https://github.com/FFmpeg/FFmpeg/blob/n8.0.1/LICENSE.md) were checked. Output is retained under `data/validation/colmap/ffmpeg-*`.

Those initial help checks did not exercise video extraction. The later [video-preparation validation](VIDEO.md) records actual FFmpeg extraction from explicitly synthetic/local fixtures as **PASS**, separately from original walking footage, which remains **NOT RUN**. Neither the fixture extraction nor the dozer photo sequence establishes reconstruction of an original walking video.
