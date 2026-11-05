# Adjacent panorama pair — P1 to P2 diagnostic

Executed 2026-11-06 KST under the [street roadmap](PANORAMIC_STREET_RECONSTRUCTION_PLAN.md).
[Observation report](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-pair/).

## Question and controlled scope

Can separately calibrated full-sphere depth from adjacent real panoramas agree
in the existing shared SfM frame? This run adds panorama 4 to the preceding
[one-panorama experiment](PANORAMIC_DEPTH_P1.md), reuses panorama 5's actual outputs,
and performs bidirectional projection. It does not refine poses, align clouds
with ICP, fuse points, synthesize images, run nine panoramas or train Brush.
The best scooter, original images, fixed-rig model and previous experiment stay
unchanged. The coordinate frame has arbitrary SfM units, not meters.

New input: `003_1677293342921360.jpg`; reused input:
`004_679966948337536.jpg`. Both are Cicero101's CC BY-SA 4.0 Mapillary imagery
acquired through Wikimedia Commons; source pages, acquisition hashes and license
links remain in `scripts/samples/mapillary-beijing.json` and the report. Original
7680×3840 images stay local. Working ERP is 1092×546. The exact audited DA² and
DAV2-Small checkpoints, FP32 MPS interfaces and dependency environment are
unchanged; see [model and license findings](PANORAMIC_DEPTH_MODELS.md). PanDA and
new dependencies were not introduced.

## Predeclared comparison and sparse evidence

Before dense comparison, the new extractor verified frozen inputs and exported
1,526 panorama-4 anchors. Its six virtual crops derive the same physical pose.
Panorama 5 retains 1,521 anchors. Both calibrations use the existing point-ID
hash split, so a common withheld point cannot leak into either calibration.
Pano4 has 1,195 training / 331 withheld tracks; pano5 has 1,195 / 326.

The pair shares 1,001 tracks, of which 217 are withheld in both views. Estimated
camera separation is 1.347506 SfM units. Shared observations have median 0.3643 px
and p90 1.1950 px reprojection residual in the original 512px crops. Pair
triangulation angle median is only 1.9386°; 371 tracks have less than 1°.
Small internal image residuals do not establish accurate camera positions.

[The protocol](evidence/panoramic-pair-protocol.json) was saved before inspecting
dense comparison outputs. Candidate road and lower-facade/railing rectangles
were chosen from observed RGB. Identical normalized ERP rectangles do **not**
guarantee identical physical surfaces across motion. The road rectangles have
zero shared SfM tracks; facade rectangles contain only 11 / 8, with one withheld
track in each. These are selection diagnostics, not semantic segmentation.

A first-order diagnostic range scale is computed from measured sparse bearing
residual, half an ERP pixel diagonal and pair triangulation angle:
`sqrt(2) * (p90 bearing residual + half-pixel diagonal) / abs(sin(angle))`.
Its median is 32.07%, p90 150.49%; weak parallax makes it very broad. This is
**not a confidence interval or an acceptance tolerance**: it cannot bound pose,
correspondence, stitching or learned-depth bias. The broad global band is used
only to color candidate front/behind/agreement masks. The facade-only sparse
medians are 3.86% / 4.64%, also not accuracy bounds. No post-hoc threshold tuning
or P2 geometry PASS follows from a largely green mask.

## Actual measurements

| Single local execution | DA² | DAV2-Small ERP control |
| --- | ---: | ---: |
| New pano4 synchronized MPS inference | 2.1533 s | 0.4096 s |
| New pano4 job elapsed | 7.7328 s | 4.1212 s |
| New pano4 process maximum RSS | 3,165,667,328 bytes | 673,939,456 bytes |
| Post-inference MPS driver allocation | 4,400,578,560 bytes | 1,258,995,712 bytes |
| Pano4 withheld-track median absolute relative residual | 28.20% | 15.67% |
| Displayed pano4 + pano5 points (stride 3) | 24,076 + 24,074 | 24,388 + 24,388 |

These are individual runs, not repeated benchmarks. The earlier pano5 inferences
(2.570 / 1.408 s) are reused, not rerun. Do not interpret different cached-run
timings as a measured speedup. RSS and sampled MPS counters are different and
must not be summed or called peak GPU memory.

DA² pano4 range scale is 596.05244, offset zero; DAV2 fits inverse radial range
`0.07920954 * prediction + 0.00250233`. All coefficients refer to this SfM frame.
Pano5 retains its earlier fit. Calibration freedoms differ between models.

Each selected source pixel is backprojected, transformed into the other camera,
and projected onto its ERP. A candidate requires valid positive target range
and all nonzero-weight bilinear neighbors inside the target mask. Horizontal
sampling wraps; poles clamp. Main statistics retain all supported candidates,
including disagreements. Source z-buffer collisions and diagnostic front/behind
classes are reported separately, not silently filtered out.

| Model / direction | Target support within selected source | Median abs. relative range difference | p90 | RGB mean abs. difference, 0–255 |
| --- | ---: | ---: | ---: | ---: |
| DA² 4→5 | 92.34% | 3.61% | 12.15% | 24.39 |
| DA² 5→4 | 92.33% | 5.10% | 12.37% | 22.36 |
| DAV2 4→5 | 92.99% | 4.07% | 10.77% | 18.59 |
| DAV2 5→4 | 93.03% | 3.58% | 10.61% | 17.92 |

The denominator is target predicted radial range. Positive signed difference
places the source point behind the target prediction; this can be actual
occlusion **or an error**, not confirmed visibility. Photos participated in pose
and depth estimation, so RGB differences are not independent appearance truth.
No exposure matching or perceptual score is applied.

| Region / model | Median abs. relative difference 4→5 / 5→4 | Target support 4→5 / 5→4 |
| --- | ---: | ---: |
| Road / DA² | 2.87% / 6.10% | 68.1% / 91.2% |
| Road / DAV2 | 6.41% / 4.69% | 64.9% / 88.8% |
| Facade and railing / DA² | 10.24% / 13.97% | 100% / 100% |
| Facade and railing / DAV2 | 4.63% / 3.85% | 100% / 100% |

The facade DA² signed medians are −10.02% / +11.28%, compatible with view-dependent
depth or calibration bias. This does not isolate its cause. DAV2's smaller dense
pair discrepancy can hide shared bias: its few facade training anchors differ
from SfM range by signed median +46.03% / +41.85%. DA² gives −17.78% / −10.69% on
those anchors. Each facade has only one withheld track, so neither local fit nor
model ranking is established. Road accuracy lacks common sparse support entirely.

## Visual observation and decision

Actual headed Chrome inspection shows both source clouds and their controls.
Source-color overlays expose offset layers and stretched outer boundaries rather
than a single coincident surface. The inverse-warp images sample the other real
photo onto the **source ERP grid**, not a rendered destination view. Black areas
are masked or unsupported. Both show distorted object/railing edges; DA²'s
nearby objects stretch more visibly in these particular images. DAV2 remains
imperfect. The source mask removes upper sky risk and nadir branding, losing
useful upper facades and trees too. It is not model confidence or a semantic mask.

**Execution PASS; P2 geometry acceptance NOT RUN / not accepted for fusion.**
Internal agreement is encouraging enough to diagnose, but cannot establish a
single coherent street or rule out shared wrong depth. The next bounded test
should reuse these predictions and fixed poses, fit each model with the same
784 common training IDs, and evaluate the 217 common withheld tracks by
reprojection to their actual matched target crop pixels. Use SfM range on the
same observed source ray as a control, stratified by parallax and longitude.
This isolates calibration-population bias before spending on new inference.
Persistent directional structure would motivate overlapping perspective-depth
or larger-parallax observations. Avoid ICP and facade-only fitting that could
hide the mismatch; only one local withheld track is available.

## Reproduce and retained evidence

The existing source, pose and model environments are required, as in the
[one-panorama instructions](PANORAMIC_DEPTH_P1.md#reproduce). Run every output in
a new directory. Original outputs are never overwritten.

```sh
data/tools/colmap-venv/bin/python scripts/extract-panoramic-pair-anchors.py \
  data/jobs/pair-NEW/anchors-4
/usr/bin/time -l data/tools/diffusion-venv/bin/python scripts/infer-panoramic-depth.py \
  data/samples/mapillary-beijing/images/003_1677293342921360.jpg \
  data/jobs/pair-NEW/da2-4 --model da2
HF_HOME=data/tools/depth-hf-cache /usr/bin/time -l \
  data/tools/diffusion-venv/bin/python scripts/infer-panoramic-depth.py \
  data/samples/mapillary-beijing/images/003_1677293342921360.jpg \
  data/jobs/pair-NEW/dav2-4 --model dav2
# Repeat these two commands for MODEL=da2 and MODEL=dav2.
MODEL=da2
data/tools/venv/bin/python scripts/evaluate-panoramic-depth.py \
  data/jobs/pair-NEW/$MODEL-4 data/jobs/pair-NEW/anchors-4/selected-panorama.json \
  data/jobs/pair-NEW/$MODEL-4/geometry
data/tools/venv/bin/python scripts/compare-panoramic-pair.py \
  data/jobs/pair-NEW/$MODEL-4 data/jobs/panoramic-depth-$MODEL-20261106 \
  data/jobs/pair-NEW/anchors-4/selected-panorama.json \
  data/jobs/panoramic-baseline-20261106/selected-panorama.json \
  docs/evidence/panoramic-pair-protocol.json data/jobs/pair-NEW/audited/$MODEL
```

The tracked protocol intentionally fixes this dataset, sources and sparse-only
comparison scale. For a different pair, declare a new protocol from sparse
observations and source RGB **before** inspecting dense results. Do not copy
its coefficients or convert them to meters.

`publish-panoramic-pair.py JOB --comparisons JOB/audited` builds the fixed report
on a fresh output path, checks the audited protocol and adds it to the existing
chronological lab. Its narrative is specific to this run; do not reuse it
unchanged for another dataset. Reconstruction arrays/weights/logs stay local;
selected derived PNGs, sanitized JSON and ordinary colored PLYs are explicitly
allowlisted. Exported PLY is concatenated unfused points, not a Gaussian artifact.

Local job: `data/jobs/panoramic-pair-20261106/`. `anchors-4/` keeps sparse evidence,
predeclared tolerance and coverage. `da2-4/` and `dav2-4/` keep MPS inference and
calibration; `audited/{da2,dav2}/` keep final pair reports, consumed-file hashes,
per-sample NPZ diagnostics, region/longitude summaries and cloud exports. Initial
comparisons are preserved separately and their directional results equal the
final audited run. Raw prediction hashes are checked before use. No-overwrite
failures remain in logs. Browser screenshots and control evidence are in
`data/jobs/panoramic-pair-ui-20261106/`.

## Validation

- **PASS:** new MPS inference for both models; same global point-ID holdout;
  source/pose/array provenance; 103 frozen baseline hashes unchanged.
- **PASS:** 22 new Python tests (6 anchor/split/conditioning, 16 pair geometry),
  all 166 JavaScript tests, TypeScript, ESLint and production build.
- **PASS:** Python discovery 162 tests in both environments: OpenCV environment
  skips 5, PyCOLMAP environment skips 31; their union executes 159 distinct tests.
- **NOT RUN:** 3 FFmpeg/HDR tests skipped by both current environments. The full
  historical browser suite was not rerun; this release has targeted real-browser
  rendering, controls, stale-response and simulated HTTP failure/recovery checks (3 targeted headed Chrome tests PASS). Run `npx playwright test tests/browser/panoramic-pair.pw.mjs` after `npm run build`; set `GS_BASE_URL` to test the public origin.
- **NOT RUN:** independent geometry truth, validated P2 acceptance tolerance,
  nearest-surface distance analysis, semantic sky mask, nine-way fusion and GS.

[Compact results](evidence/panoramic-pair-p1.json) and [release verification](DEPLOYMENT.md)
record the final publication status separately from geometry acceptance.
