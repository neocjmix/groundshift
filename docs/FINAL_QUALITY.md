# Final quality attempt on the existing panoramas

Declared2026-11-06 before viewing the result. The user explicitly makes this the
**last quality campaign on these same nine source photographs**. Preserve the
best result afterward and move to new capture evidence or product work. Do not
turn a disappointing result into another model/filter/crop/budget/seed sweep.

## One actual native configuration

- Same nine licensed7680×3840 originals, source hashes and all-nine fixed-rig
  SfM. Eight training centers exclude panorama5 RGB as before.
-96 fresh1024×1024 real crops, with the exact same90° FOV, yaw/pitch and camera
  matrices. Extract directly from original ERP pixels, **not upscaled512 RGB**.
  Intrinsic pixel values scale by2; world positions and units never scale.
- Identical183,124-point DAV2 calibrated dense initialization and colors. No
  new depth prediction, new pose estimation or generated training photograph.
- Brush0.3.0 Metal,8,000 steps,800,000 Gaussian ceiling,SH1,seed42. Resolution
  and capacity change together as one practical quality probe; no factorial
  attribution or timing-speed claim. More steps alone already failed to improve
  the prior best, so this run does not repeat that search.
- Same angular nadir mask, regenerated on the1024 ray grid. Small sampling-edge
  differences are expected; do not pretend pixel masks are byte-identical.

Work directory: `data/jobs/street-final-quality-20261106/`. Each stage retains its
actual report/log. Source/previous worlds remain read-only. Mechanical failure
recovery must preserve this declared configuration and retain failed evidence;
no silent downscale or new quality budget.

## Evaluation and publication order

The incumbent is the actual512/400k DAV2 dense8k export, reused without claiming
retraining. Use the same75 evaluation cameras at512 output for direct comparison.
Also render both worlds at1024 with fresh1024 references to inspect fine detail;
do not compare an error measured at512 directly to one measured at1024.
Panorama5 appearance withholding still reuses all-nine estimated pose/sparse
geometry. No independent measured geometry, gravity, metric distance, collision
surface or unrestricted-walking claim.

Publish actual fresh input comparisons immediately with training RUNNING and
render/evaluation NOT RUN. Dispatch the native export as soon as it exists,
without waiting for full matched renders or all tests. Publish later measured
outcomes separately. A deployment sub-agent owns the static observation updates
while the main process trains, investigates and verifies.

## Geometry-preserving training: bounded investigation

The current released Brush path uses RGB/SSIM plus opacity/scale regularization;
the calibrated depth only initializes the scene. Inspect actual upstream
depth-supervision support and native interfaces before claiming an integration.
Keep this feasibility investigation distinct from the one declared standard
training. Do not silently substitute an unreleased engine, guessed metric depth,
or unverified renderer/backward implementation into the quality comparison.

## Reproduce in a fresh output directory

Prerequisites are the preserved source acquisition/rig/seed in
[STREET_CONCLUSION.md](STREET_CONCLUSION.md). The inputs command supports an
explicit resolution; its default remains512 for all historical workflows.

```sh
mkdir -p data/jobs/NEW
data/tools/venv/bin/python scripts/prepare-final-quality.py data/jobs/NEW
data/tools/venv/bin/python scripts/reconstruct.py data/jobs/NEW/datasets/hires \
  data/jobs/NEW/training-hires --steps 8000 --resolution 1024 \
  --max-splats 800000 --title 'Street final quality1024' --id street-final-hires
```

The source CLI's `--help` is retained with the actual job. Actual outcomes,
measurements, release verification and
the stopping decision are appended after execution, never assumed here.
