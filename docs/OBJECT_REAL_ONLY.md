# Scooter ablation: nine real images only

The user clarified that the comparison must remove **all intermediate image
generation and interpolation**, not only the diffusion model. This run uses the
same nine observed 512×512, 45° perspective crops as the
[preceding experiment](OBJECT_FOCUS_EXPERIMENT.md). No RIFE or diffusion image
enters its camera model, depth fusion or Gaussian training.

## What is held constant

The original-only image-estimated camera solution and Depth Anything V2 Small
predictions are reused from the previous job. Input image hashes are checked
against the depth report. They are recorded as reused observations, not newly
executed inference. Depth calibration/filtering, the three original-image object
rectangles, voxel spacing rule, Brush 0.3.0, 512 maximum resolution, SH degree 1,
5,000 steps, seed 42 and the 150,000-splat ceiling are unchanged. Point fusion
and Metal GS training execute again using only the nine real views.

The original experiment's 38 registered synthetic RGB images and their depth
contributions are absent. This is an ablation of the entire intermediate-image
stage, not an isolated measurement of the diffusion model's effect.

## Actual local result

| Observation | Prior augmented run | Real-only run |
| --- | ---: | ---: |
| Real / synthetic candidate images | 9 / 56 | 9 / 0 |
| Registered training images | 47 | 9 |
| Depth maps contributing points | 34 | 9 |
| Initial points | 93,595 | 41,533 |
| Metal training seconds | 610.514 | 160.298 |
| Exported Gaussians | 93,941 | 46,807 |
| Object-center selection | 93,101 | 43,268 |

These are individual recorded runs, not a repeated performance benchmark.
The new unselected PLY is 4,306,895 bytes, SHA-256
`0c5179e68dfb11e913375c34c9c6cc3ebee60aed728b46eeac6c2b2c20025e5c`.
The training log confirms **Apple M2 / Metal**. All nine original depth maps
passed the same internal calibration; none were excluded. This is not evidence
of metric-depth accuracy.

Local Chrome rendered both new artifacts and the point clouds. The inspected
home view has more defined scooter details, while strong stretched splats remain
around the object. The report places the old and new default views side by side;
these are not a matched-camera quantitative quality comparison. Independent
geometry and comparative quality measurements remain **NOT RUN**.

## Reproduce and inspect

Reuse the completed local reference job and existing native environments:

```sh
data/tools/venv/bin/python scripts/run-object-ablation.py \
  data/jobs/object-focus-20261105 data/jobs/object-focus-real-NEW
data/tools/venv/bin/python scripts/publish-object-focus.py \
  data/jobs/object-focus-real-NEW --real-only
# Capture actual browser previews for scooter-real-object and scooter-real-context.
data/tools/venv/bin/python scripts/publish-object-focus.py \
  data/jobs/object-focus-real-NEW --real-only --finish
```

The reference acquisition and environment instructions are in the preceding
experiment. The runner preserves input hashes, reuse lineage, subprocess commands,
exit codes and logs. No generated images, raw depth arrays, private paths or model
weights are added to Git or the public package. Licensed original perspective
crops, depth visualizations, compact point clouds and both GS exports are published.

Raw evidence is in `data/jobs/object-focus-real-only-20261105/`. The initially
misunderstood RIFE-only attempt is preserved as **CANCELLED** in
`data/jobs/object-focus-rife-only-20261105/ablation.json`; it stopped during camera
estimation before GS training, and none of its products enter this experiment.

[Public comparison](https://groundshift-viewer-production.up.railway.app/experiments/object-real/)
· [New GS](https://groundshift-viewer-production.up.railway.app/?world=/worlds/scooter-real-object/world.json)
· [Chronological lab](https://groundshift-viewer-production.up.railway.app/experiments/lab/).
Public release and post-publication checks are recorded in [DEPLOYMENT.md](DEPLOYMENT.md).
