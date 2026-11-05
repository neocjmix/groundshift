# P0 + one-panorama full-sphere depth experiment

Follow-up: [adjacent-pair diagnostics](PANORAMIC_PAIR_P1.md) have now executed; the one-panorama measurements below remain unchanged.

Authoritative scope: [panoramic street roadmap](PANORAMIC_STREET_RECONSTRUCTION_PLAN.md).
This run freezes the existing best scooter result and tests one full ERP; no
Gaussian training, generated RGB, nine-way fusion or scooter tuning is included.

## File-level design and acceptance matrix

| Boundary | Implementation | Evidence required |
| --- | --- | --- |
| Baseline preservation | `freeze-panoramic-baseline.py` | Source/camera/depth/PLY hashes and unchanged readback; distinct scooter/rig coordinate frames |
| Actual model inference | `infer-panoramic-depth.py` | Pinned weights/code, raw arrays, MPS execution, timing/memory/error record |
| Depth meaning and projection | `spherical_depth.py` | Analytic ray, seam, radial versus Z, calibration and rigid-pose tests |
| Common-frame diagnostic | `evaluate-panoramic-depth.py` | Explicit fit to original fixed-rig SfM radial anchors; held-out-track residuals and coverage; no metric claim |
| Inspectable output | Existing experiment/lab conventions | RGB/depth/mask, calibrated full and filtered cloud, actual browser screenshots |
| Publication | Existing immutable Railway static package | Archive checksum, live file hashes, actual public browser inspection |

Working input is the middle source panorama, `004_679966948337536.jpg`,
7680×3840. Model input is the full ERP resized to 1092×546. DA² is the primary
candidate because its official checkpoint terms are explicit, radial distance
semantics are documented, and upstream contains a macOS/MPS path. Depth Anything
V2 Small uses the existing Transformers checkpoint as a deliberately out-of-
distribution ERP control. [Audited model findings](PANORAMIC_DEPTH_MODELS.md).

Calibration uses only sparse observations of this panorama in the existing
fixed-rig model, in arbitrary SfM units. Deterministic point-ID holdout separates
calibration fitting and checking, but both subsets originate in all-image SfM;
neither is independent geometry ground truth. DA² uses scale-only range fitting.
DAV2 uses an affine inverse-range hypothesis, explicitly tested rather than
assuming its pinhole output defines full-sphere radial range.

The raw full-sphere prediction is retained. A conservative inspection mask will
exclude the upper hemisphere/sky risk and bottom panorama branding band; this
loses upper-facade/tree coverage and is not semantic sky detection. A raw calibrated
cloud remains available to expose the excluded predictions. Single-panorama
self-reprojection only checks implementation, not geometric accuracy. No
cross-panorama consistency or readiness for Gaussian training is implied.

## Actual execution — 2026-11-06 KST

Both models executed locally on Apple M2 / MPS with FP32 and no CPU operator
fallback. DA² used the audited checkpoint and unchanged model subpackage; no
CUDA port, xFormers, Accelerate launcher or upstream export stack was installed.
The wrapper imports the `model` subpackage directly because top-level `da2`
imports optional CLI/export dependencies. Source code revision and checkpoint
SHA-256 are enforced before loading. DAV2 used the existing pinned HF pipeline.

| Recorded observation | DA² | DAV2-Small ERP control |
| --- | ---: | ---: |
| Network input width × height | 1092 × 546 | 1036 × 518 |
| Saved prediction width × height | 1092 × 546 | 1092 × 546 |
| Model load seconds, cached checkpoint | 4.158 | 2.487 |
| Synchronized MPS inference seconds | 2.570 | 1.408 |
| Job elapsed seconds | 8.132 | 5.322 |
| Maximum resident set bytes | 3,159,523,328 | 623,132,672 |
| MPS driver allocation bytes at post-inference sample | 4,400,578,560 | 1,258,979,328 |
| Calibration train / withheld sparse tracks | 1,195 / 326 | 1,195 / 326 |
| Withheld-track median absolute relative radial residual | 0.2563 | 0.1377 |
| Withheld-track 90th-percentile absolute relative residual | 1.2451 | 0.5494 |
| Full valid sampled points | 66,248 | 66,080 |
| Conservative-mask sampled points | 24,074 | 24,388 |
| Retained ERP pixel fraction | 36.50% | 37.00% |
| Masked seam median adjacent range difference, SfM units | 0.05244 | 0.31594 |

These are single-run measurements, not repeated performance benchmarks. Model
loading excludes the checkpoint download. `/usr/bin/time -l` additionally reports
DA² whole-command elapsed 8.71 s and peak process memory footprint 4,857,726,104
bytes. Process RSS, process footprint and sampled MPS allocations are different
counters and must not be added or called isolated peak GPU memory.

DA² raw output was 98th-percentile-normalized radial range. Its fitted scale is
526.1355031564 with zero offset. DAV2's OOD hypothesis fits inverse range as
`0.0697965062 * prediction + 0.0034205460`. These coefficients depend on this
panorama and arbitrary SfM scale; they are not transferable metric calibrations.
The comparison has different calibration freedoms (one versus two parameters)
and different network resolutions, so its residuals do not establish model
superiority. DAV2's affine inverse conversion also creates very large distances
near zero inverse range; the full diagnostic cloud exposes this rather than
silently clipping it into an accepted surface.

The point-ID split is deterministic before calibration. All 326 withheld tracks
remain excluded from fitting; they still come from the same all-image SfM.
Longitude-bin residuals are retained in each geometry report. Calibration anchors
cover only latitude −42.52° to +43.69°, with 47 of 72 coarse angular cells occupied.
No polar calibration or independent depth truth exists. Full-field prediction
is not full-field validation.

The conservative selection is fixed at ERP vertical fractions 0.48–0.85, plus
positive finite range no greater than the training-anchor 99th-percentile range.
It removes likely sky and the yellow nadir branding, but also upper buildings,
tree canopy and some far surfaces. This is explicitly not semantic sky detection
or learned confidence. The sampling stride is three pixels along both axes;
PLY and browser JSON contain the same selected points. Raw range arrays, masks,
calibration records, and the unmasked positive-range cloud are retained.

## Observations and limitations

Actual Chrome inspection shows a colored patch of pavement, lower facade edges,
railings, bikes and vegetation surrounding the camera. The pavement and facade
edges remain curved/stretched rather than demonstrated planar geometry. Switching
to the capture position makes source colors align by construction; that is not
new-view validation. The central hole comes from excluding nadir/branding, not
a reconstructed hole in the road. The full cloud includes distant sky-like shells
and outliers, illustrating why a finite positive prediction is not a surface.

Both models show a seam jump. The masked seam medians above are lower for DA²,
but neither is zero, and comparison with ordinary neighbors is sensitive to
smooth areas and actual edges. We apply no invented seam pass threshold and no
post-hoc seam repair. The full-sphere depth arrays include both poles; unsupported
polar geometry is not declared valid. Original stitched-panorama distortions,
weak parallax, dynamic foliage and fixed-rig pose errors remain confounded.

PanDA-Small's code, checkpoint terms and interface were investigated but inference
is **NOT RUN**: DA² fit and executed on the available hardware, so this bounded
run keeps one panoramic candidate plus the existing DAV2 control. It was not
silently substituted or reported as executed.

## Checks and decision

**PASS:** 103 baseline file hashes preserved; strict no-overwrite snapshot checks;
real MPS inference for both models; explicit calibration and estimated-pose
backprojection; 24 spherical geometry tests and 10 calibration/integration tests;
actual local Chrome model/cloud/image controls and chronological lab entry.
The analytical tests cover pixel-center rays, coordinate handedness, polar and
seam sampling, ray range versus camera-Z, mandatory calibration, invalid values,
known rigid transforms and no calibration-holdout leakage. Self-reprojection
residuals are algebraic checks only. Execution reports preserve FAIL on errors.

**NOT RUN:** independent geometric accuracy, adjacent-panorama consistency,
semantic sky masks, polar calibration, PanDA inference, new fixed evaluation
camera GS renders, and all Gaussian training. P0 provides a frozen baseline and
labeled camera set; tree/doorway/facade/road target-specific render selection is
still deferred. This is a bounded P0/P1 result, not completion of the entire P0
or P1 research program.

**Ready to expand to two panoramas for diagnosis, not ready for fusion or GS.**
Next use only adjacent panoramas 4 and 5, keep the existing fixed rig, calibrate
separately using the same split rules and inspect their overlapping static
facade/road surfaces. Compare signed radial residuals by direction, depth-aware
RGB reprojection and occlusion before merging points. DA²'s worse internal
residuals warrant checking per-direction scale and the SfM anchors; its smoother
seam alone is insufficient to select it for the street pipeline.

## Reproduce

The existing environments and licensed source acquisition are documented in
[MAPILLARY_EXPERIMENT.md](MAPILLARY_EXPERIMENT.md). Reuse the already downloaded
originals and baseline jobs; never run into an existing output directory.

```sh
# Add only the two missing model dependencies to the existing PyTorch environment.
data/tools/diffusion-venv/bin/python -m pip install --no-deps \
  torchvision==0.29.2 einops==0.8.1
git clone https://github.com/EnVision-Research/DA-2.git data/tools/da2
git -C data/tools/da2 checkout d659838585f2bc9967c7e9367af573795271dbbb
HF_HOME=data/tools/panorama-hf-cache data/tools/diffusion-venv/bin/python - <<'PYTHON'
from huggingface_hub import hf_hub_download
hf_hub_download('haodongli/DA-2', 'model.safetensors',
    revision='0d55ccb5e46b8ed4715fae3a4c04fc897f1689f3',
    local_dir='data/tools/da2-checkpoint')
PYTHON

data/tools/colmap-venv/bin/python scripts/freeze-panoramic-baseline.py \
  data/jobs/panoramic-baseline-NEW
/usr/bin/time -l data/tools/diffusion-venv/bin/python scripts/infer-panoramic-depth.py \
  data/samples/mapillary-beijing/images/004_679966948337536.jpg \
  data/jobs/panoramic-da2-NEW --model da2
HF_HOME=data/tools/depth-hf-cache /usr/bin/time -l \
  data/tools/diffusion-venv/bin/python scripts/infer-panoramic-depth.py \
  data/samples/mapillary-beijing/images/004_679966948337536.jpg \
  data/jobs/panoramic-dav2-NEW --model dav2
# Repeat for each completed inference job.
data/tools/venv/bin/python scripts/evaluate-panoramic-depth.py \
  data/jobs/panoramic-da2-NEW \
  data/jobs/panoramic-baseline-NEW/selected-panorama.json \
  data/jobs/panoramic-da2-NEW/geometry
```

After evaluating both models, `scripts/publish-panoramic-depth.py DA2_JOB DAV2_JOB`
prepares the explicit public comparison assets and adds its lab entry. Model
weights, original-resolution panoramas, raw arrays and logs remain local. The
original source and all previous GS artifacts are unchanged. The published PLYs
are ordinary colored point clouds, not trained Gaussian scenes.

Executed environment: Python 3.12.12, Torch 2.15.0, torchvision 0.29.2,
Transformers 5.22.1, huggingface-hub 2.4.0, safetensors 0.8.0, einops 0.8.1,
NumPy 2.5.4, Pillow 13.0.0, macOS 26.6.2 arm64. The existing separate OpenCV and
PyCOLMAP environments run geometry/snapshot tests. The initial core import failed with `ModuleNotFoundError: torchvision`; installing
these dependencies resolved it before inference. Only torchvision and einops
were added; existing Torch was not replaced. Upstream training pins differ and
are not represented as the tested environment.

[Compact recorded measurements](evidence/panoramic-depth-p1.json) are tracked with
the code; raw evidence and large outputs remain local/release assets.

Local evidence directories: `data/jobs/panoramic-baseline-20261106/`,
`data/jobs/panoramic-depth-{da2,dav2}-20261106/`,
`data/jobs/panoramic-depth-input-20261106/`, and model research snapshots.
The actual deployment and public-origin checks are recorded in [DEPLOYMENT.md](DEPLOYMENT.md).



Post-run software checks: TypeScript, lint, production build and all 166 JS tests
PASS. Python suites each ran 140 tests: five dependency skips in OpenCV and 31
in PyCOLMAP. The union executes 137 distinct tests; three unrelated HDR/FFmpeg
checks remain skipped in both environments and are NOT RUN for this release.
The 34 new geometry/calibration tests are included in these totals, not additional.
The full historical headed-browser suite is NOT RUN; focused actual local report
inspection passes for both models, both cloud masks, capture/overview views,
point-size control, lab ordering and the preserved scooter report. Public checks
are recorded after deployment separately.


Public deployment **PASS**: both models' actual point clouds and report controls
were inspected in headed Chrome 156 at the Railway origin, with no page errors;
all 68 selected new/shared public file hashes and `/healthz` pass. The chronological
lab lists this report first and preserves all 22 existing GS scenes. This changes
no geometric uncertainty or NOT RUN boundary. See the [release record](DEPLOYMENT.md#one-panorama-full-sphere-depth--2026-11-06-kst).
