# Perspective depth: bounded coverage and overlap experiment

2026-11-06, existing physical panoramas **4 and 5** only. Execution **PASS**;
street geometry acceptance **NOT ACCEPTED**; fusion and Gaussian training
**NOT RUN**. [Observation page](https://groundshift-viewer-production.up.railway.app/experiments/perspective-overlap/).

## Question and implementation

The [previous perspective control](PANORAMIC_CALIBRATION.md) improved sparse
feature reprojection. This run asks whether it also improves dense street
overlap. It does not optimize or retrain the scooter.

The six original level, 512-square, 90-degree crops per panorama cannot see the
predeclared road ROI (ERP v=.78–.84). Add six **real reprojected crops** per
panorama, yaw 0/60/120/180/240/300 degrees, pitch **−30 degrees**. Positive pitch
in the existing sampler is up. These are new virtual orientations at the same
two camera centers, not twelve new physical observations. No generated RGB,
interpolation model, diffusion or new pose estimation is used.

**Depth Anything V2 Small actually executed on MPS**, with CPU fallback disabled:
`depth-anything/Depth-Anything-V2-Small-hf`, revision
`5426e4f0f36572d16453bbda7a8389317b1bef99`. Existing level predictions and fits
are reused unchanged. This is the practical perspective fallback from the
roadmap, not a newly adopted spherical model. See the previously checked
[code, checkpoint, training-data and dependency terms](PANORAMIC_DEPTH_MODELS.md)
for DAV2, DA² and the unresolved PanDA weights; no model/license substitution.

Downward camera rotations are derived analytically from the existing measured
fixed-rig panorama poses. Original level rotations and centers are also checked
against PyCOLMAP. Axes remain +X right / +Y down / +Z forward. No guessed
gravity, metric scale, alignment or ICP is introduced.

Each downward prediction is fitted to **inverse camera-Z**, using only the same
common 784 training point IDs projected into that crop; 57–183 finite positive-Z
tracks per crop. The 217 withheld IDs are excluded globally. New crop pixels are
projected existing SfM locations, not newly matched observations. Additional
projected holdout diagnostics (404 crop observations, no invalid predictions)
are retained; these repeat point IDs and do not create independent truth.

For each working 1092×546 ERP unit ray: project into the actual pinhole crop,
bilinearly sample using corner-origin coordinates minus half a pixel, apply
`1/Z = a × prediction + b`, then compute **radial range = Z / ray_camera.z**.
Reject back-facing, unsupported and nonpositive inverse-depth values. Select
the valid crop with highest ray_camera.z. This is angular sampling policy,
not confidence. Perspective sampling never wraps; spherical sampling does.

Four explicit controls are exported: original level crops; level plus downward
ring; that augmented map after same-center disagreement filtering; previous
common-calibrated ERP prediction. All use the same fixed display camera, RGB,
working dimensions, range-cap policy and source masks. Source point IDs/colors
remain inspectable; the two clouds are overlaid **without fusion**.

## Protocol and retained evidence

[Protocol](evidence/perspective-overlap-protocol.json) was declared before new
inference/dense results. Its input hashes pin original panoramas, prior
predictions/fits, sparse model and preceding pair protocol. The diagnostic
same-center log-range band **0.2908611929** is the previous sparse control's P90
absolute log radial error: 434 directional observations of 217 distinct held
IDs. It is an internal comparator, **not** a confidence interval or geometry
acceptance tolerance. It uses the preceding holdout as a design reference;
those IDs are not an independent final evaluation set for this filter.

Filter rule: at least two supported positive crop predictions and
`max(log range) − min(log range) <= band`. A single physical center sees the
same ray in its crops; disagreement cannot be attributed to inter-camera
occlusion. Shared model bias, panorama stitching and calibration error remain.

The previous road/facade rectangles and cross-view relative diagnostic band
0.3206960701 are unchanged. Cross-view signed difference is projected source
range minus target predicted range; front/behind labels do not prove occlusion.
Both directions retain unsupported samples in denominators. Statistics use
stride3; diagnostic images display those samples as 3×3 nearest-neighbor blocks.
Depth colors use each panorama's training-range P99, constant across controls.
The angular mask v=.48–.85 is **37% of ERP rows**, not full-sphere coverage or a
semantic sky mask. Positive ranges above the training P99 are excluded, with
raw maps retained. No nine-panorama expansion is performed.

## Observations

Coverage per panorama, out of **220,584 selected-band pixels**:

| Variant | Panorama 4 | Panorama 5 | Combined displayed points, stride3 |
|---|---:|---:|---:|
| Level only | 156,326 | 156,321 | 34,534 |
| Level + downward | 220,514 | 220,509 | 48,758 |
| Same-center filter | 209,748 | 211,118 | 46,618 |
| ERP control | 220,582 | 220,584 | 48,776 |

The road ROI has 16,929 pixels per panorama: zero level-only support; all are
covered by the augmented and filtered maps. Same-center road log-spread median
is .0294/.0352. This agreement alone does not establish the road's true depth:
there are **zero common SfM road anchors**, so the road remains outside the
calibration evidence. Downward crops also change angular sampling and model
context; these controls do not isolate one projection factor.

The table below uses **identical source pixels and jointly supported target
depths** for ERP versus augmented perspective. Values are median absolute
cross-view relative range residuals, not ground-truth errors:

| Region / direction | Joint samples | ERP | Perspective |
|---|---:|---:|---:|
| Road 4→5 | 1,206 / 1,881 source ROI samples | 5.80% | 2.43% |
| Road 5→4 | 1,662 / 1,881 | 5.15% | 0.96% |
| Facade 4→5 | 992 / 992 | 4.69% | 5.11% |
| Facade 5→4 | 992 / 992 | 3.58% | 5.41% |
| All 4→5 | 22,658 shared candidates | 3.99% | 2.12% |
| All 5→4 | 22,629 shared candidates | 3.70% | 2.25% |

**The tail gets worse:** paired all-region P90 rises from 10.58%/10.40% to
12.74%/12.60%. A better median does not justify full-street acceptance.

Filtering is also not an automatic improvement. It retains only **5,235/9,114**
and **6,143/9,114** facade pixels. In 5→4, comparison candidates drop from 992
to459; their RGB-difference median changes from 11.90 to29.35 (0–255).
These survivor populations differ, so this is evidence against claiming filter
success, not a matched-pixel accuracy comparison. Raw and filtered clouds,
support counts, winners, log-spread arrays and source/target residual samples
are preserved. No filter threshold was tuned to improve these outputs.

## Runtime and validation

M2 Air16GB, macOS26.6.2 arm64, same installed runtimes as prior experiment.
New 12-crop DAV2 MPS inference: **2.606 s** after Python imports; model load
**0.338 s**. Whole `/usr/bin/time -l` process **6.54 s**, maximum RSS
**528,302,080 bytes**, peak process footprint **1,626,227,744 bytes**. These are
different process counters, not isolated GPU peak measurements or benchmarks.
Final CPU calibration/maps/clouds/pair diagnostics **8.701 s**, maximum RSS
**538,656,768 bytes**. Earlier 6.520/7.276 s executions are retained separately;
the audited and final run's coverage, pair results and paired comparison
structures are numerically identical. This is a reproducibility check, not
a controlled speed comparison.

Headed Chrome screenshots were inspected: the pavement, scooter and lower
facade are recognizable as colored points, but wedge boundaries, curved/striped
road structure and stretched curtain-like points remain. The missing upper
image is largely the declared angular mask; the crop discontinuities are not
explained away by that mask. This is an inspectable diagnostic cloud, not a
validated continuous street or a new Gaussian scene.

**PASS:** actual MPS inference, CPU diagnostics/exports, all103 preserved baseline
hashes; nine new analytic tests for projection, camera-Z/radial distinction,
front/invalid conventions, seam coverage, downward rotation/co-location, sampling
policy and unsupported denominators. TypeScript, lint, production build and
166 JS tests pass. Python discovery:184 per environment,31/5 skipped; union
executes181 distinct tests. Three unrelated FFmpeg/HDR tests remain **NOT RUN**.
Six targeted **headed Chrome checks PASS** locally (20.5 s): all four new real
cloud variants, source colors, single-source visibility, camera changes,
diagnostic images, chronological lab, previous pair/one-panorama report and
calibration-page simulated-failure recovery. The initial run found a broken
relative source-preview path, now fixed; it also exposed a test's stale
assumption about which report must be newest. Failed evidence is preserved
separately. Broad historical browser suite **NOT RUN**. Public verification is
recorded in [deployment evidence](DEPLOYMENT.md).
The public release also passes six headed Chrome156 checks (59.1s) and161
selected file hashes, with public screenshots inspected. All48 new report
assets/entry are included in that hash check. Publication **PASS** is separate
from the geometry gate; the observed wedges/strips remain visible online.

**NOT ACCEPTED:** P2 static-surface geometry gate. **NOT RUN:** independent depth
truth, new GS training, voxel fusion, all-nine inference/fusion, full P0 matched
evaluation renders. The next bounded step is to constrain local depth using
actual cross-view static-surface correspondences, especially the unanchored
road and contradictory facade, rather than expanding this filter to nine views.

## Reproduce

Requires the existing licensed inputs and fixed-rig reconstruction described in
[pair reproduction](PANORAMIC_PAIR_P1.md#reproduce-and-retained-evidence) and
[perspective calibration](PANORAMIC_CALIBRATION.md#reproduce). No new packages,
weights, infrastructure or paid services are added. The existing environment
named `diffusion-venv` runs depth estimation here; no diffusion model executes.
Use fresh directories; prior jobs are never overwritten:

```sh
data/tools/venv/bin/python scripts/experiment-perspective-overlap.py prepare \
  data/jobs/overlap-input-NEW
HF_HOME=data/tools/depth-hf-cache PYTORCH_ENABLE_MPS_FALLBACK=0 /usr/bin/time -l \
  data/tools/diffusion-venv/bin/python scripts/infer-relative-depth.py \
  data/jobs/overlap-inference-NEW data/jobs/overlap-input-NEW/*.png
data/tools/colmap-venv/bin/python scripts/experiment-perspective-overlap.py run \
  data/jobs/overlap-NEW --prepared data/jobs/overlap-input-NEW \
  --inferred data/jobs/overlap-inference-NEW
data/tools/colmap-venv/bin/python -m unittest discover -s scripts/tests -v
data/tools/venv/bin/python -m unittest discover -s scripts/tests -v
npm run typecheck
npm run lint
npm test
npm run build
npx playwright test tests/browser/perspective-overlap.pw.mjs \
  tests/browser/panoramic-pair.pw.mjs tests/browser/panoramic-calibration.pw.mjs
```

`publish-perspective-overlap.py JOB` prepares the fixed observation path only
when it does not exist, appends a chronological entry and explicitly allowlists
selected static assets. It refuses to replace an earlier publication. For a
different experiment, assign a new path/ID. Original ERP images, model weights,
NumPy predictions, logs and sparse poses remain local, outside Git and hosting.
Only existing licensed reduced source previews and derived diagnostic artifacts
are published. [CC BY-SA provenance](../scripts/samples/mapillary-beijing.json).

Local jobs: `data/jobs/perspective-overlap-input-20261106/`,
`perspective-overlap-inference-20261106/`,
`perspective-overlap{,-audited,-verified}-20261106/` under `data/jobs/`.
The final report, per-crop fits/projected holdouts, raw per-crop radial stacks,
unmasked maps, masks, pair sample arrays, PLY and browser JSON are retained.
Sanitized numerical evidence is also published as
`/experiments/perspective-overlap/measurements.json`.
