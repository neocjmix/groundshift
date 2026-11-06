# Observed correspondences and bounded road calibration

2026-11-06. Two existing physical panoramas4/5, fixed SfM poses and existing
DAV2 predictions. Actual CPU execution **PASS**; road's local agreement improves,
full P2 geometry **NOT ACCEPTED**. No new GPU inference, diffusion, pose fitting,
fusion or Gaussian training. [Observation](https://groundshift-viewer-production.up.railway.app/experiments/stereo-anchors/).

## What changed

The [previous experiment](PERSPECTIVE_OVERLAP.md) improved perspective-depth
agreement but had no sparse road calibration evidence. This run searches actual
RGB correspondences and triangulates them using the preserved fixed-rig camera
centers/rotations. It changes calibration evidence, not the depth network or poses.

Use original licensed7680×3840 panoramas to make1024-square90° crops: six level
and six pitch−30° orientations at each of two physical centers. Larger matching
crops add angular sampling, not physical viewpoints. Native OpenCV5.0.0 CPU
SIFT/BFMatcher and the existing StereoSGBM implementation run locally. Existing
512-square DAV2 Small predictions (pinned MPS execution from the previous run)
are hash-checked and reused; **new model inference NOT RUN**.

No new dependencies, services or weights. Upstream
[feature matching documentation](https://docs.opencv.org/4.13.0/dc/dc3/tutorial_py_matcher.html),
[camera projection/triangulation conventions](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html)
and [OpenCV5.0.0 Apache-2.0 license](https://github.com/opencv/opencv/blob/5.0.0/LICENSE)
were checked, alongside actual installed Python interfaces. The4.x documentation
redirects to4.13.0; installed5.0.0 APIs were also executed, not assumed from docs.
Existing [DAV2/checkpoint findings](PANORAMIC_DEPTH_MODELS.md) remain applicable.
Data: Cicero101/Mapillary via Wikimedia Commons, CC BY-SA4.0; source hashes and
[provenance](../scripts/samples/mapillary-beijing.json) unchanged.

## Protocol, failures and root cause

1. **Global SIFT:**6000 features/crop, mutual ratio<.75, positive triangulated
   camera-Z in both views, reprojection<=1px at1024, parallax>=3°, ranges within
   preceding training-SfM P99 caps.913 raw geometric candidates reduce to667
   after paired spherical-ray deduplication. **Source4 road:0**.
2. **Ground SIFT retry:** additional masked ERP v=.70–.85 search,3000 features,
   contrastThreshold=.01; geometric filters unchanged.920 raw candidates reduce
   to669, with514 training and140 held tracks. Source4 road still0; source5 road4.
   The failure precedes geometric filtering: essentially no mutual-ratio road
   correspondences, rather than evidence that camera poses caused rejection.
3. **Existing stereo,256px disparity search:** six actual fixed-pose rectified
   pairs; SGBM_3WAY block5, LR residual<=.5px, RGB MAE<=15/255, uniqueness10,
   stride16 samples, parallax>=3°, same range caps. Only7 source4-road candidates;
   below the30-candidate admission gate, **not used** in calibration.
4. **Diagnose search support before relaxing filters:** previous depth maps imply
   overlapping road disparities with P10 about277–335px, median314–340px,
   P90 about348–394px. These are **model-based hypotheses**, not true disparities
   or matcher inputs. The256px search cannot reach them. Keep all geometric,
   LR/photo filters and sampling fixed; expand only disparity search to512.
5. **Wide stereo:**291 road candidates pass; parallax P10/median/P90
   **19.07°/23.32°/29.08°**. After paired-ray dedup with SIFT, combined955 tracks:
   **754 training,186 held**. Five duplicate stereo candidates are suppressed.
   Spatially protected non-held tracks are not used for training.

The256→512 change fixes a concrete parameter limitation. It does not establish
that all291 matches are correct. Repetitive texture, panorama stitching,
occlusion and correlated LR/photo errors remain possible.

[SIFT protocol](evidence/stereo-anchors-protocol.json),
[initial stereo protocol](evidence/road-stereo-protocol.json) and
[wide search protocol](evidence/road-stereo-wide-protocol.json) were written
before each stage's outputs. Original jobs and both inadequate/adequate search
runs are retained; the new search is explicit, not a hidden substitute.

## Calibration and evaluation

Use +X right/+Y down/+Z forward camera axes, corner-origin pixel centers.
OpenCV SIFT coordinates receive **+.5**; existing raster rectification subtracts
.5 from cx/cy. All virtual camera rotations derive analytically from existing
panorama poses. A second independent DLT implementation checks sampled stereo
world coordinates against the existing rectified-depth conversion.

Merge duplicates within.35° in **both** physical panorama rays. Spatially hold
out whole source-ERP64px tiles where `(tile_x+2*tile_y)%5==0`; never split a retained
correspondence between views. New training rays within.5° of any previous217 held
SfM directions in either panorama are excluded. This is spatial protection,
not proof of physical point identity. Nearby texture remains correlated;
these are **internal calibration holdouts, not independent geometry truth**.

Fit the same Huber affine inverse camera-Z: `1/Z=a×prediction+b`. Convert each
unit ray to radial range by `range=Z/ray_camera.z`. Compare: existing calibration;
old training plus new training; new training only. Missing/invalid per-crop fits
would explicitly retain the old fit, but all24 crop fits execute in these runs.
Original fits recompute within tolerance. Baseline spherical maps and masks match
the preceding saved arrays; central-crop selection, angular band v=.48–.85,
range caps, stride3, colors, ROI boxes and display cameras are unchanged.

The report exposes **five cloud variants**: baseline, combined-road augmented,
combined-road new-only, SIFT-only augmented and SIFT-only new-only. First SIFT
attempts without road support are preserved alongside the successful search.
All outcomes remain viewable irrespective of quality; they are ordinary colored
point clouds, not newly trained Gaussians.

## Measured outcomes

Matched source pixels, jointly supported target ranges, for **old+new training
including wide stereo** versus baseline:

| Region/direction | Joint samples | Baseline median range discrepancy | Augmented |
|---|---:|---:|---:|
| Road4→5 |1,201|2.427%|**0.445%**|
| Road5→4 |1,661|0.964%|0.983%|
| Facade4→5 |992|5.113%|5.576%|
| Facade5→4 |992|5.405%|5.376%|
| All4→5 |22,471|2.104%|1.579%|
| All5→4 |22,425|2.222%|1.797%|

These are discrepancy to another estimate, **not true-depth error**. Different
ROI boxes can contain different physical surfaces. Full-population P90 remains
about12.7%/12.8%; the wall/tail problem has not disappeared.

On the same new186 held correspondences per direction,512px observed-crop
reprojection medians change **2.451→1.987px** / **3.516→2.492px**. The augmented
fit has1/2 invalid predictions, included in denominators. Road held subsets are
46 points in source4,13 in source5: **.747→.627px** / **4.838→1.412px**; relative
range residual medians **.830→.676%** / **2.704→.905%**. Triangulation controls
share the matching observations and are not independent depth evidence.

**Regressions matter:** on the earlier217-feature check, augmented calibration
has6/3 invalid predictions; combined new-only has7/**47**. Median statistics
exclude invalid values, so their counts are explicitly displayed. Adding points
does not make a globally valid calibration. The SIFT training population is much
closer: radial P10/median/P90 about3.7/5.9/15.0 versus old4.6/16.8/79.0 (view4,
arbitrary SfM units). The shifted evidence distribution and affine extrapolation
are a concrete limitation; they do not isolate all causes of each error.

The SIFT-only control modestly improves its own140 held features but worsens
dense agreement; new-only road medians reach about9.6%/6.1%. Its held set differs
from the combined186: compare calibrations **within each fixed set**, not raw
averages across different point populations. Raw held samples, all denominators,
paired comparisons and invalids remain available in local arrays/JSON and the
sanitized public measurements.

Visual inspection: actual point clouds render; road, scooters and lower facade
are recognizable. Crop wedges, strips and duplicate/offset surfaces remain.
The local improvement does not constitute continuous-street or P2 acceptance.

## Runtime and validation

M2 Air16GB, macOS26.6.2, local CPU/OpenCV5.0.0,2 OpenCV threads. Single measured
executions, not controlled benchmarks:

| Stage | Seconds | Maximum process RSS bytes |
|---|---:|---:|
| Global SIFT |10.100|590,970,880|
| Audited masked+global SIFT |13.006|575,455,232|
| Audited256 stereo |8.362|411,205,632|
|512 stereo |12.986|410,976,256|
| SIFT-only calibration/maps |9.670|543,719,424|
| Combined calibration/maps |9.614|543,670,272|

SIFT-only clouds: baseline48,758, augmented48,459, new-only48,150 points.
Wide-stereo clouds: baseline48,758, augmented48,467, new-only48,122. Counts are
stride3 masked samples, not fused geometry. No new GPU operation is claimed.

Nine new tests include exact/rotated triangulation, reprojection rejection,
half-pixel conversion, behind/degenerate cases, seam-crossing ray comparison,
spatial grouping, and **actual SGBM on a known320px-shift synthetic fixture**:
256 cannot reach it,512 recovers it with LR consistency. Synthetic fixtures
are kept separate from the real-panorama results above. TypeScript/lint/build
and166 JS tests PASS. Python discovers193 tests per environment, skips5/32;
their union executes190 distinct tests. Three unrelated HDR checks are NOT RUN.
No-overwrite checks reject existing output directories with unchanged hashes.
Seven targeted local headed Chrome checks PASS (28.2s); screenshots inspected.
Broad historical browser regression and independent depth truth **NOT RUN**.
Publication verification is recorded in [deployment evidence](DEPLOYMENT.md).

## Reproduce

Requires pinned original panoramas/fixed-rig poses and prior predictions from
[previous reproduction](PERSPECTIVE_OVERLAP.md#reproduce). No installations or
new accounts. Use fresh output directories:

```sh
gs_match_job=data/jobs/stereo-matching-NEW
gs_narrow_job=data/jobs/road-stereo256-NEW
gs_wide_job=data/jobs/road-stereo512-NEW
gs_sift_cal=data/jobs/sift-calibration-NEW
gs_combined_cal=data/jobs/combined-calibration-NEW
data/tools/venv/bin/python scripts/experiment-stereo-anchors.py "$gs_match_job" --ground
data/tools/venv/bin/python scripts/probe-road-stereo.py "$gs_match_job" "$gs_narrow_job"
data/tools/venv/bin/python scripts/probe-road-stereo.py "$gs_match_job" "$gs_wide_job" \
  --max-disparity 512
data/tools/venv/bin/python scripts/calibrate-stereo-anchors.py "$gs_match_job" "$gs_sift_cal" \
  --road "$gs_narrow_job"
data/tools/venv/bin/python scripts/calibrate-stereo-anchors.py "$gs_match_job" "$gs_combined_cal" \
  --road "$gs_wide_job"
data/tools/venv/bin/python -m unittest discover -s scripts/tests -v
data/tools/colmap-venv/bin/python -m unittest discover -s scripts/tests -v
npm run typecheck
npm run lint
npm test
npm run build
npx playwright test tests/browser/stereo-anchors.pw.mjs \
  tests/browser/perspective-overlap.pw.mjs tests/browser/panoramic-pair.pw.mjs \
  tests/browser/panoramic-calibration.pw.mjs
```

`publish-stereo-anchors.py COMBINED_NEW MATCHING_NEW --sift-control SIFT_CAL_NEW
--road STEREO512_NEW` creates a new fixed observation path only if absent,
appends the lab entry and allowlists selected derived assets. Assign a new
path/ID for another experiment. Existing reports are never replaced.

Retained under `data/jobs/`: `stereo-anchors{-ground,-audited,}-20261106/`,
`road-stereo{,-audited,-wide}-20261106/`,
`stereo-calibration{,-audited,-wide}-20261106/`, `stereo-validation-20261106/`.
Raw crops, disparity arrays, rejected candidates, correspondence IDs, poses,
fits, projected samples and logs remain local and outside Git/hosting. Licensed
reduced overlays, selected colored PLYs, comparison images and sanitized
measurements are public. Previous footage, models, scooter and all103 frozen
baseline file hashes are preserved.

Next useful diagnostic: a third actual viewpoint for road correspondence
verification, then calibration that respects measured angular/range support and
positive inverse depth. Keep near-road gains without extrapolating unsupported
far surfaces. Full nine-view fusion and Gaussian training remain **NOT RUN**.
