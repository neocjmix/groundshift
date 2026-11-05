# P0: preserved scooter baseline and panoramic evaluation frame

Executed 2026-11-06 as the read-only baseline stage of
[PANORAMIC_STREET_RECONSTRUCTION_PLAN.md](PANORAMIC_STREET_RECONSTRUCTION_PLAN.md).
No source images, camera solutions, depth arrays, point clouds or Gaussian
artifacts were changed, regenerated or retrained. This stage prepares the
whole-street experiment; it does not optimize the scooter.

## What was pinned

`scripts/freeze-panoramic-baseline.py` created
`data/jobs/panoramic-baseline-20261106/` and verified **103 existing files** against
SHA-256 hashes after reading them. The inventory includes:

- All nine licensed 7680×3840 ERP panoramas and acquisition/provenance records.
- The nine actual best-scooter training PNGs, and the nine preceding observed
  crops separately. Their documented one-pixel border difference is preserved.
- Both SfM models, their cameras/intrinsics, transforms, sparse initialization,
  and the analytic panorama crop manifest.
- Raw Depth Anything V2 arrays, calibrated depth arrays, calibration/fusion
  reports, object selection rectangles, and the dense initialization PLY.
- Both final best-scooter Gaussian PLYs, world/camera metadata, Brush options,
  execution/resource records, browser evidence, and implementation hashes.

The strongest observed baseline is unchanged:
[nine-real-image comparison](https://groundshift-viewer-production.up.railway.app/experiments/object-real/)
· [object world](https://groundshift-viewer-production.up.railway.app/?world=/worlds/scooter-real-object/world.json).
The previous run records 41,533 initial points, 46,807 full-scene Gaussians,
43,268 selected Gaussians and 160.298 seconds of Brush 0.3.0 M2 Metal training.
These are reused single-run observations, **not new benchmarks**. Its scooter
is recognizable but blurred and affected by stretched splats; independent
geometric accuracy remains **NOT RUN**. See [OBJECT_REAL_ONLY.md](OBJECT_REAL_ONLY.md).

## Two coordinate frames must remain separate

The best scooter camera solution was re-estimated from the nine object-facing
crops. Its sparse model contains 671 points and has its own arbitrary SfM frame.
The full-street fixed-rig solution estimates nine physical camera centers from
54 overlapping crops and contains 3,232 points. No alignment between those two
frames was estimated by this snapshot. Scooter camera matrices must not be
applied directly to the fixed-rig street cloud.

The street frame is pinned from
`data/jobs/mapillary-beijing-rig-poses-v2/dataset/sparse`. Current readback confirms
54 registered virtual views, nine physical panorama centers and mean internal
reprojection error **0.5181939403 pixels**. Six virtual views per panorama share
one center by construction. This is nine physical viewpoints, not 54 independent
ones. The recorded co-location check passes with maximum center deviation
4.53×10⁻¹⁵ SfM units. This constrains the model mathematically; it does not prove
that the estimated street is geometrically accurate. Gravity and metric scale
are unknown.

## Selected panorama and reusable calibration evidence

The bounded P1 input is middle panorama `pano_000005`:

- Local source: `data/samples/mapillary-beijing/images/004_679966948337536.jpg`.
- Mapillary image ID: `679966948337536`.
- Original dimensions: 7680×3840; the original remains intact.
- Author: Cicero101; CC BY-SA 4.0 via the existing Wikimedia Commons acquisition.
  Exact acquisition URLs, license text and source hash remain pinned locally.

`selected-panorama.json` exports the panorama-to-world matrix, source and model
hashes and **1,521 unique sparse anchors** visible in its six virtual views. Each
anchor records world XYZ, original point ID and color, radial distance,
normalized ERP coordinates, selected-view observed pixel references,
reprojection error, distinct physical panorama count and maximum triangulation
angle. All 1,521 are finite, have positive radial range and tracks involving at
least two physical centers. No learned depth or synthesized RGB supplied these
anchors.

The transform is derived from the existing exported OpenGL camera matrix:

```text
worldFromCameraCV = worldFromOpenGLCamera × diag(1, -1, -1, 1)
worldFromPanorama.rotation = worldFromCameraCV.rotation
                              × relativeCameraToPanoramaRotationᵀ
worldFromPanorama.translation = worldFromCameraCV.translation
```

Panorama coordinates are right-handed **+X right, +Y down, +Z forward**.
For unit ray `(x,y,z)`, normalized ERP coordinates are:

```text
u = (atan2(x,z) / (2π) + 0.5) mod 1
v = 0.5 - asin(-y) / π
pixel-center coordinates = ((column + 0.5)/width, (row + 0.5)/height)
radial range = norm(Xworld - cameraCenter)
```

The six independently read virtual-camera matrices reproduce one panorama
matrix; the maximum matrix-element discrepancy across all nine panorama groups
is 4.44×10⁻¹⁵. Radial ranges are **arbitrary SfM units, not meters and not pinhole
camera-Z depth**. The panorama anchors and poses were jointly estimated using
all nine panoramas; a calibration holdout of these points is still internal
model validation, not independent ground truth.

Current support is geographically incomplete:

| Sparse support diagnostic | Readback |
| --- | ---: |
| Selected panorama unique anchors | 1,521 |
| Latitude range | −42.52° to +43.69° |
| Occupied 30° longitude × 30° latitude cells | 47 / 72 |
| Median / 95th-percentile radial range | 16.72 / 88.76 SfM units |
| Median / 95th-percentile per-point reprojection error | 0.403 / 1.368 pixels |
| Median distinct physical centers per track | 5 |
| Median / 95th-percentile maximum triangulation angle | 7.72° / 41.99° |

There are no anchors in either polar 30° band. The 47 occupied cells do not
imply dense surface coverage. Some points are distant or weakly triangulated;
no semantic sky mask was inferred in this baseline snapshot. A depth model's
poles, sky and extrapolation outside these anchors need explicit treatment.

## Fixed evaluation camera metadata

`evaluation-cameras.json` fixes:

- Nine **observed-image, SfM-estimated** panorama poses in the street frame.
- Eight **interpolated diagnostic** centers midway between neighboring estimated
  centers, retaining the left panorama's orientation. They are not measured
  captures and have no reference RGB image.
- Two **extrapolated diagnostic** cameras displaced from the middle panorama
  along its local X axis by ±0.1 of median adjacent-center spacing. That spacing
  is 1.36820 arbitrary units, so each offset is 0.13682 units. This is a display
  choice, not evidence of a safe or walkable physical location.
- The nine actual scooter training cameras and intrinsics, explicitly tagged
  with the separate scooter SfM frame.

All new street evaluation renders are **NOT RUN** in P0. Existing observed
scooter crops are linked; target-specific tree, doorway, facade and road
view selection is **NOT RUN** because no reviewed target coordinate or matched
crop has yet been selected. No target points were invented to fill those gaps.
New P1 inspection should select actual visible street regions and preserve
that selection before multi-panorama or novel-view quality comparisons.

## Reproduce and verify

Run from the repository root in the existing PyCOLMAP 4.2.1 environment:

```sh
data/tools/colmap-venv/bin/python scripts/freeze-panoramic-baseline.py \
  data/jobs/panoramic-baseline-NEW

data/tools/colmap-venv/bin/python scripts/freeze-panoramic-baseline.py \
  data/jobs/panoramic-baseline-NEW --verify
```

A freeze refuses an existing output directory. `--verify` only reads snapshot
and source files, fails on any size/hash mismatch and does not rewrite evidence.
The executed freeze and post-read verification passed in **0.329 seconds** on
this Mac; this is inventory processing time, not reconstruction or inference.
Three execution checks passed: unchanged-source verification, refusal to overwrite
an existing snapshot, and rejection of a deliberately corrupted hash in a
separate disposable manifest. No source bytes were altered for these tests;
commands, exit codes and errors are retained in `validation.json`.
The output retains `baseline.json`, `selected-panorama.json` and
`evaluation-cameras.json` locally. Raw reports contain existing execution paths
and are not intended for direct publication. Large assets remain in their
original locations and outside Git.

P0 status: **PASS for immutable inventory, pose export and diagnostic-camera
metadata**. Baseline rerender, new inference, target-specific street views,
independent geometry validation and Gaussian retraining are **NOT RUN by this
stage**. The separate P1 report records actual new model execution and visual
inspection.
