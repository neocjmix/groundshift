# Common-track calibration and perspective control

Executed locally on 2026-11-06 KST. This continues the [adjacent-pair diagnostic](PANORAMIC_PAIR_P1.md)
under the [street roadmap](PANORAMIC_STREET_RECONSTRUCTION_PLAN.md).
[Public observation](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-calibration/).

## Result and decision

Matching the calibration population alone did not materially improve held-out
feature reprojection. A subsequent bounded DAV2 perspective-depth control did
improve it: the 26 withheld points with pair parallax ≥10° had median error
2.564 / 2.161 pixels, compared with 6.935 / 6.756 for common-fit ERP depth and
6.087 / 4.776 for crop-local ERP depth. These are two directional observations
on internal SfM tracks, not independent accuracy or a GS quality benchmark.

The next useful P1 fallback is overlapping perspective depth with explicit
camera-Z to radial conversion and overlap/seam diagnostics. Repeating a single
global ERP calibration is not supported as the main remedy. Dense spherical
fusion of those perspective predictions, nine-panorama expansion and Gaussian
training remain **NOT RUN**. Previous scooter, one-panorama and pair outputs
are preserved; displayed new clouds are the common-fit ERP diagnostic only.

## Phase A — Same calibration IDs, fixed prediction and pose

Before inspecting results, [protocol A](evidence/panoramic-calibration-protocol.json)
pinned 47 input files: original predictions/RGB/masks, sparse model, panorama
anchors, crop rasters and previous display cameras. Both panoramas use the same
784 shared training point IDs; 217 shared IDs are withheld in both. The original
fits used 1,195 tracks per view. Model-specific formulas remain unchanged: DA²
scale-only radial range; DAV2 affine inverse-radial hypothesis on ERP. Input,
pose and calibration freedoms remain fixed within each model.

Each withheld point contributes one actual crop observation per panorama,
chosen by smallest normalized distance to its principal point, with image-name
tie-break. Selection uses no learned prediction or evaluation residual. This
avoids counting multiple co-located crops as independent camera positions.
Calibration samples predictions at SfM-projected ERP bearings, matching the
preceding experiment. Evaluation samples at the **observed source feature ray**,
backprojects using its actual estimated camera center, and projects into the
actual observed target crop pixel. COLMAP coordinates remain corner-origin;
first array center is 0.5,0.5. No synthetic correspondences are introduced.

Controls are (1) the original triangulated SfM point and (2) SfM radial range
along the same observed source ray. All points remain in denominators. Invalid
ranges or behind-camera predictions are counted; positive-Z projections outside
the target image remain in error statistics. The current run has zero invalid
held-out projections; some ERP fits put one point outside the target crop.

Target crops are 512×512, actual intrinsics fx=fy=cx=cy=256. Median pixel errors:

| Input / calibration | 4→5 | 5→4 |
| --- | ---: | ---: |
| SfM 3D point control | 0.362 | 0.352 |
| Observed source ray + SfM radial range | 0.525 | 0.506 |
| DA² original all-anchor fit | 2.333 | 2.150 |
| DA² common784 fit | 2.327 | 2.196 |
| DAV2 ERP original all-anchor fit | 1.521 | 1.255 |
| DAV2 ERP common784 fit | 1.481 | 1.400 |

Large-parallax points expose errors obscured by the overall median. Among the
217 withheld points, 94 have <1°, 63 have 1–3°, 34 have 3–10° and 26 have ≥10°
pair parallax. At ≥10°, DA² common-fit median errors are 37.809 / 27.661 px;
DAV2 common-fit 6.935 / 6.756 px; SfM-ray controls 0.831 / 0.869 px.

The dense pair range-disagreement medians under frozen original masks become
6.39% / 8.47% for DA² common-fit, compared with previous 3.61% / 5.10%.
DAV2 common-fit gives 3.97% / 3.69%, previously 4.07% / 3.58%. No rejection
threshold was tuned to make the new fit look better. New displayed clouds use
exactly the same original masks, stride3 and camera/center/radius, changing range
only. Counts remain 48,150 DA² / 48,776 DAV2 combined unfused points.

## Phase B — Perspective and crop-local ERP controls

Phase A did not remove the mismatch. [Protocol B](evidence/panoramic-perspective-control-protocol.json)
was declared before running the additional model control. The existing pinned
`infer-relative-depth.py` executed DAV2-Small on twelve real 512×512 fixed-rig
crops, six per panorama. Same HF model revision
`5426e4f0f36572d16453bbda7a8389317b1bef99`, Apple MPS, no new model/dependency,
and `PYTORCH_ENABLE_MPS_FALLBACK=0`. [Model/license findings](PANORAMIC_DEPTH_MODELS.md)
remain applicable; no weights or training data are redistributed.

Two local fits use identical training IDs **within each crop** and the same
number of coefficients. All 784 eligible common training IDs are used somewhere
in each panorama, 47–271 per crop after shared finite/in-bounds sampling. No
withheld ID enters either fit:

- ERP-local: `1/radial = a * ERP_prediction + b`, using that crop's shared training
  subset and corresponding SfM radial ranges.
- Perspective-local: `1/camera_Z = a * perspective_prediction + b`, using the
  same subset and corresponding SfM camera-Z. For evaluation,
  `radial = camera_Z / observed_camera_unit_ray.z` before world projection.

Both use the preceding Huber IRLS solver. Out-of-domain camera-Z is invalid, not
flipped or assigned arbitrary metric scale. For calibration, perspective arrays
are sampled at projected SfM crop coordinates; for evaluation, at observed pixels.
No horizontal wrap applies to a perspective image. Reprojection uses exactly the
same selected source/target observations and all 217 withheld IDs as phase A.

| DAV2 condition | Median px 4→5 / 5→4 | p90 px 4→5 / 5→4 |
| --- | ---: | ---: |
| Global ERP common-fit | 1.481 / 1.400 | 8.225 / 7.860 |
| Crop-local ERP fit | 1.764 / 1.307 | 7.206 / 6.584 |
| Crop-local perspective camera-Z fit | **0.922 / 1.011** | **4.527 / 4.020** |

At ≥10° parallax (26 points), perspective medians **2.564 / 2.161 px** are
63.0% / 68.0% lower than the global ERP medians. Crop-local ERP gives 6.087 /
4.776 px. All 217 predictions are valid/in-image for perspective in both
directions; 141 / 134 individual points improve over global ERP. Counts, paired
changes and longitude/parallax strata remain in raw reports.

This is a practical input/calibration comparison, not a pure single-factor
projection ablation. Angular sampling is also not equalized: perspective crops are
512×512 at 90° FOV, while the ERP is 1092×546 over the full sphere (DAV2 network
1036×518 versus 518×518 for each crop, verified from the pinned processor). The crop pipeline can retain
more local detail. This is a post-run interpretation limit, not an amended
predeclared protocol or an isolated measurement of resolution benefit.
Global-to-local changes parameter count; ERP-local and
perspective-local hold point subsets and parameter count fixed, but input
projection and the appropriate depth target differ. It supports investigating
perspective depth as the next candidate, not declaring accurate geometry.

## Interpretation and visual evidence

The same estimated frame supports subpixel internal SfM-ray controls while
learned ERP ranges produce large errors at some near, high-parallax surfaces.
Changing calibration point population does not fix those errors. The perspective
control reduces the errors beyond crop-local ERP fitting in this pair. This
implicates spatial depth distortion/input suitability as an additional concern.
It does not prove camera poses or SfM distance are correct; all controls and
withheld tracks come from the same all-nine-image reconstruction.

Feature mosaics show yellow observed target points and colored displacement
vectors over actual source-licensed photos. Vector display is 2× with a 48px cap;
all reported numeric errors are uncapped. Phase A red=original, cyan=common,
pink=SfM-ray. Phase B red=crop-local ERP, cyan=perspective, pink=SfM-ray. Long
nearby railing/building/pavement-edge vectors remain in ERP. Inspect these at
full image resolution; a small median does not validate roads or upper coverage.
The earlier road rectangle has zero withheld shared tracks, facade one per view.

## Execution measurements and checks

M2 Air16GB, macOS26.6.2 arm64; existing Python/PyCOLMAP and Torch/Transformers
runtimes. Single-run values, not repeated benchmarks:

- Phase A CPU job: **1.926 s**, maximum RSS **225,443,840 bytes**.
- Phase B actual twelve-image MPS job: **2.723 s** from after Python imports,
  model load **0.358 s**, synchronized per-image inference **0.087–0.900 s**.
  Whole `/usr/bin/time -l` command **6.63 s**, max RSS **523,943,936 bytes**,
  peak process footprint **1,628,750,928 bytes**. These counters are different;
  neither is claimed isolated GPU peak. First image includes warm-up effects.
- Phase B calibration/reprojection: under one second in the recorded run.

**PASS:** actual CPU experiments and MPS perspective inference; unchanged global
holdout; input/raw-prediction hashes and exact source cameras; 13 new tests for
observed-ray projection, point selection, exclusion, out-of-image denominators,
corner-origin sampling, inverse-camera-Z versus radial range and calibration.
TypeScript, lint, build and 166 JS tests pass. Full Python discovery has 175 tests
per environment (5 / 31 skipped); union executes 172 distinct tests. Three
unrelated HDR/FFmpeg tests are **NOT RUN**. All 103 frozen baseline hashes remain
unchanged. Five targeted headed Chrome checks cover the new page and preserved
pair/one-panorama report; broad historical browser suite is **NOT RUN**.

**NOT RUN:** independent geometry truth, perspective dense overlap/seam evaluation,
full-sphere perspective-cloud fusion, all-nine inference/fusion and new GS.
**Publication PASS:** Railway deployed the checksum-pinned archive; 113 selected public file hashes and five targeted headed Chrome checks passed. Public cloud screenshots were inspected. [Release evidence](DEPLOYMENT.md) records IDs, timings and rollback package.

## Reproduce

Requires the previous local pinned inputs and models from
[P1](PANORAMIC_DEPTH_P1.md#reproduce) and [pair diagnostics](PANORAMIC_PAIR_P1.md#reproduce-and-retained-evidence).
Scripts intentionally check those frozen paths/hashes. Use new output directories:

```sh
# Declare a new protocol before examining a different run's results.
data/tools/colmap-venv/bin/python scripts/diagnose-pair-calibration.py \
  --output data/jobs/panoramic-calibration-NEW
HF_HOME=data/tools/depth-hf-cache PYTORCH_ENABLE_MPS_FALLBACK=0 /usr/bin/time -l \
  data/tools/diffusion-venv/bin/python scripts/infer-relative-depth.py \
  data/jobs/panoramic-perspective-NEW \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset/images/pano_000004_view_*.png \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset/images/pano_000005_view_*.png
data/tools/colmap-venv/bin/python scripts/compare-perspective-depth.py \
  data/jobs/panoramic-perspective-NEW data/jobs/panoramic-calibration-NEW \
  data/jobs/panoramic-perspective-control-NEW
```

`diagnose-pair-calibration.py --declare NEW_PROTOCOL` creates a fresh input
manifest; `--protocol NEW_PROTOCOL` selects it. The tracked protocols describe
this exact fixed pair. For a new pair or changed hypothesis, write new protocols
before examining outputs and retain errors. Existing directories are rejected.

`publish-panoramic-calibration.py PRIMARY_JOB --perspective CONTROL_JOB` prepares
the report in a fresh public output directory and explicitly allowlists assets.
Only selected licensed feature mosaics, sanitized summaries and ordinary colored
clouds enter the static archive. Original panoramas, raw prediction arrays,
weights and logs remain local. Re-run the targeted browser tests with
`npx playwright test tests/browser/panoramic-calibration.pw.mjs tests/browser/panoramic-pair.pw.mjs`
after building; `GS_BASE_URL` selects the deployed origin.

Local retained evidence: `data/jobs/panoramic-calibration-20261106/`,
`data/jobs/panoramic-calibration-input-20261106/`,
`data/jobs/panoramic-perspective-depth-20261106/`,
`data/jobs/panoramic-perspective-control{-audited,}-20261106/`.
Initial comparisons and an audited rerun are preserved, with identical numeric
results. Neither prior ERP/GS artifacts nor original footage is overwritten.
