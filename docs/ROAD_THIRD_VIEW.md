# Road correspondences in a third observed panorama

2026-11-06. Local native CPU execution **PASS**. An additional real RGB viewpoint
supports a small road region; full-street P2 geometry remains **NOT ACCEPTED**.
No new depth-model inference, calibration fitting, pose estimation, fusion or GS
training. [Observation page](https://groundshift-viewer-production.up.railway.app/experiments/road-third-view/).

## Question and controls

The [preceding run](STEREO_ANCHORS.md) recovered291 road tracks from real
panoramas4/5, then improved local depth calibration. Would those points and that
improvement survive another actual photograph? Preserve the291 tracks, original
sources, existing radial maps, fixed camera poses, scooter GS and every earlier
experiment. Do not optimize the scooter or generate intermediate views.

Match original photos5/6 independently using existing local OpenCV5.0.0 CPU
StereoSGBM. The matcher consumes only their RGB and fixed camera calibration;
previous4/5 XYZ and learned depth are **not matcher inputs**. Compare the resulting
triangulation at each old track's exact panorama5 bearing. RGB6 was absent from
the road calibration, but all camera poses were jointly estimated from the nine
photos. This is additional appearance/correspondence evidence, **not independent
camera or surveyed-depth ground truth**.

No dependency or checkpoint was added. Reuse the
[previously verified OpenCV interface/license](STEREO_ANCHORS.md) and existing
[DAV2 model/weight findings](PANORAMIC_DEPTH_MODELS.md). DAV2 Small's preceding MPS
predictions and calibrated radial maps are unchanged; **new GPU inference NOT RUN**.
Three original7680×3840 panoramas are Cicero101/Mapillary via Wikimedia Commons,
CC BY-SA4.0; [source URLs and hashes](../scripts/samples/mapillary-beijing.json).
Only derived licensed previews, diagnostic point clouds and selected metadata
are published. Originals, raw arrays and process logs remain local.

## Protocol and coordinates

[Protocol](evidence/road-third-view-protocol.json) is written before disparity
inference. Six1024-square90° crops per physical camera, yaw0…300° in60° steps,
pitch−30°. Keep the earlier2× finite rectified canvas,512-disparity search,
SGBM_3WAY block5/uniqueness10, LR tolerance.5px, RGB MAE<=15/255. At each old
panorama5 bearing, select one crop **before matching**, ranked by original-camera
ray Z among own-valid finite canvases. Do not select the lowest-error result.

Subpixel disparity uses bilinear interpolation only when every nonzero-weight
neighbor passes LR/photo checks and neighborhood disparity spread<=2px. No
nearest-valid fallback or interpolation across a depth boundary. Fixed-pose DLT
must have positive camera-Z in both cameras, parallax>=3°, reprojection<=1px.
No new learned-depth/range cap. Retain unsupported points in the291 denominator.
Other crop trials remain in raw track diagnostics, without replacing the primary
selection. These are correlated texture tests, not proven object identity.

Use only the baseline's **observed** camera records, never its virtual target
poses. All54 virtual-crop transforms are checked against the corresponding
panorama poses; existing4/5 anchors must agree to1e−10. World frame is
`fixed-rig-sfm-20261104`, arbitrary SfM units, unknown gravity. Panorama/CV axes
are+X right,+Y down,+Z forward; ERP seam−Z. OpenGL camera poses convert with
`diag(1,-1,-1,1)`. Corner-origin crop coordinates and OpenCV array-index pixels
differ by.5. Rectification changes ray projection, not physical camera centers.

Compare angular ray difference at camera6, absolute relative radial difference
at camera5 (denominator=new5/6 range), and cross-ray separation in SfM units.
Do not interpret any value as meters. A predeclared internal repeatability screen
requires>=30 supported tracks and>=80% of supported tracks within1° and5%.
It is a diagnostic threshold, **not street accuracy/fusion acceptance**.

## Actual observations

[Native result](evidence/road-third-view.json): **44/291 supported (15.12%)**,
247 LR/photo-unsupported at their preferred crop. All44 supported tracks pass the
internal repeatability screen. Their angular difference at6 has median
**0.06866°**, P90**0.35884°**, maximum**0.66850°**; absolute radial difference at5
has median**0.57060%**, P90**1.79366%**, maximum**2.58042%**. This is positive
evidence for a small road region, not success for the247 unconfirmed points.

Using any crop would support86 tracks. That number is diagnostic only; it does
not replace the preferred-crop44 or justify choosing a favorable residual.
[Posthoc coverage diagnostic](evidence/road-third-view-coverage.json): old4/5 XYZ
hypotheses predict all247 unsupported points inside the512px disparity search
(P10/median/P90 **294.11/345.23/405.35px**). Seventeen project outside the matching
camera6 crop; one into the known nadir band. Only3 have nonpositive raw matcher
disparity. These hypotheses are not measured correspondences, but they suggest
that simply widening the search again is not the next useful fix. Texture,
LR/photo consistency, visibility and stitching require localized inspection;
the exact cause is **unresolved**.

The overview shows a narrow, sparse patch of road. The previous291 include
isolated remote candidates; they remain in the all-points control. Default3D
display frames the common44+44 points for inspection. Switching to all points
fits the full range, which makes the main cluster small. Display framing never
changes the measured coordinates. Actual RGB6 overlay includes every old point:
green=supported within diagnostic threshold, red=supported outside, yellow=no
primary support. Twenty-four examples are selected at evenly spaced track indices,
**not by success**. Patches are actual original RGB, not synthesized renderings.

## Does the previous calibration improvement carry over?

A separate [evaluation protocol](evidence/road-third-view-calibration-protocol.json)
samples the unchanged panorama5 radial maps at the same44 exact bearings. No fit
or camera update. **All three methods have5 invalid depths**, retained explicitly;
the following medians use the same39 valid tracks. Of those,6 were withheld from
the preceding calibration and33 were training points.

| Frozen calibration | Camera6 angle median,39 | Absolute radial difference median,39 | P90 radial difference,39 | Previous-held6: radial median |
|---|---:|---:|---:|---:|
| Previous baseline |0.05849°|0.42994%|1.41611%|0.50673%|
| Previous + new road/SIFT anchors |0.04606°|0.38384%|0.75055%|0.24292%|
| New anchors only |0.04003°|0.35255%|0.73559%|0.17287%|

[Measurements](evidence/road-third-view-calibration.json) retain full counts,
held/training strata and paired statistics. Augmented calibration improves22/39
individual comparisons and4/6 previous-held comparisons. This is a modest local
gain, not universal improvement. New-only's favorable road subset does not undo
its preceding **47 invalid historical far-region predictions**. No uncertainty
interval or population-level significance is claimed for six held points.

## Runtime, failures and reproduction

M2 MacBook Air16GB, macOS26.6.2 arm64; OpenCV5.0.0 CPU, two threads.
Stereo/crops/diagnostic exports: **16.266s**, maximum process RSS**795,639,808B**
(758.781MiB). Frozen-map evaluation: **0.06979s**, RSS**58,163,200B**. RSS includes
the Python process and loaded images/arrays, not measured GPU memory. No new
Gaussian/rendering FPS benchmark. Exported standard PLYs contain291 old and44
new colored points, in the unchanged world frame.

The first map-evaluation invocation **FAIL**ed on a relative-path provenance
conversion before reading depth maps. Its report/log is preserved in
`data/jobs/road-third-view-calibration-20261106/` and
`data/jobs/third-view-validation-20261106/calibration-evaluation.log`.
Resolve CLI input directories before recording provenance; successful retry uses
a new`road-third-view-calibration-v2-20261106`directory. No geometric/matching
parameters were changed to obtain the successful run.

Requires the prior local jobs documented in[STEREO_ANCHORS.md](STEREO_ANCHORS.md).
Use **fresh output paths**; scripts refuse an existing directory:

```sh
data/tools/venv/bin/python scripts/check-road-third-view.py \
  data/jobs/road-third-view-REPEAT
data/tools/venv/bin/python scripts/evaluate-road-third-view.py \
  data/jobs/road-third-view-REPEAT \
  data/jobs/stereo-calibration-wide-20261106 \
  data/jobs/road-third-view-calibration-REPEAT
```

The checked run uses`road-third-view-20261106`and
`road-third-view-calibration-v2-20261106`. Publication, once per observation path:

```sh
data/tools/venv/bin/python scripts/publish-road-third-view.py \
  data/jobs/road-third-view-20261106 \
  data/jobs/road-third-view-calibration-v2-20261106
npm run build
npx playwright test tests/browser/road-third-view.pw.mjs \
  tests/browser/stereo-anchors.pw.mjs tests/browser/perspective-overlap.pw.mjs \
  tests/browser/panoramic-pair.pw.mjs tests/browser/panoramic-calibration.pw.mjs
```

## Validation and remaining gate

- **PASS:** nine new synthetic tests cover ray/rectification rotations, corner vs
  array-index convention, behind/outside rays, coherent subpixel support, invalid
  neighbors, depth discontinuity, known angular residual, seam and scale invariance.
- **PASS:** TypeScript, lint, JS166 tests, production build. Python202 discovered
  per environment:197 pass/5 skip(OpenCV),170 pass/32 skip(PyCOLMAP); union199
  distinct passes. Three HDR/FFmpeg checks **NOT RUN**. Existing large-chunk build
  warning remains.
- **PASS:** all103 pinned scooter/input artifacts retain original hashes.
- **PASS:** nine local headed Chrome156 checks(30.8s), actual sparse-cloud rendering, color/scope/orbit/reset,
  three real previews, measured subsets, PLY download, chronological discovery
  and explicit simulated503 failure handling are checked. Final run and public
  deployment evidence are recorded in[DEPLOYMENT.md](DEPLOYMENT.md).
- **PASS:** all21 pre-execution protocol input/code hashes read back unchanged;
  all three CLIs reject an existing output without changing its report.514 prior
  packaged world/experiment data files retain their hashes. Built HTML references
  and the appended chronological timeline are separate from those data checks.
- **NOT RUN:** new GPU inference/training, independent measured geometry, facade
  or far-region third-view validation, all-nine fusion/GS. **P2 NOT ACCEPTED**.

P1 already expanded to adjacent panoramas in earlier runs; this adds only a
bounded third-RGB check. Next useful work is a direction/range support map and
localized diagnostics of unsupported road, facade and far regions. Preserve
visibility/coverage denominators. Do not expand to a full street Gaussian merely
because this small supported subset agrees.

## Implementation files

Implementation commit`4d125f280f79dd9f1a62fdb452d9b46b8bae5757`:

- Native execution:`scripts/check-road-third-view.py`,
  `scripts/evaluate-road-third-view.py`, `scripts/third_view_geometry.py`.
- Publication:`scripts/publish-road-third-view.py`,
  `scripts/observation-worlds.json`.
- Browser:`experiments/road-third-view/index.html`, `src/road-third-view.ts`,
  `src/road-third-view.css`, `vite.config.ts`.
- Tests:`scripts/tests/test_third_view_geometry.py`,
  `tests/browser/road-third-view.pw.mjs`.
- Documentation:`README.md`, `docs/PANORAMIC_STREET_RECONSTRUCTION_PLAN.md`,
  this report; evidence:`docs/evidence/road-third-view.json`,
  `road-third-view-protocol.json`, `road-third-view-calibration.json`,
  `road-third-view-calibration-protocol.json`, `road-third-view-coverage.json`.

Deployment-pointer and final verification commits update only deployment/docs;
their evidence is recorded in[DEPLOYMENT.md](DEPLOYMENT.md). No original footage,
large generated assets or model weights are committed to Git.

Final publication **PASS**: immutable337,976,806-byte archive read back, server
checksum verified,250 selected public hashes correct including all12 new report
files, public headed Chrome9 checks pass(CLI rounded1.4m). See
[release evidence](evidence/road-third-view-release.json) and
[actual public sparse-cloud screenshot](evidence/road-third-view-browser.png).
The lab preserves22 Gaussian scenes and13 reports in chronological order.
