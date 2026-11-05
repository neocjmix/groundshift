# Panoramic street reconstruction: staged experiment plan

Status: P0 baseline frozen and one-panorama P1 smoke test executed; see [actual results](PANORAMIC_DEPTH_P1.md). Two-panorama consistency, full P0 evaluation renders and P2–P5 remain NOT RUN. Baseline: branch `feat/local-viewer-reconstruction`, 2026-11-06. This plan is for a *continuous explorable street*, not optimizing the scooter in isolation. No performance or quality claims below are new measurements.

## Decision and hypotheses

Preserve the strongest observed scooter recipe: nine real 512x512 / 45-degree target-facing crops from nine Mapillary panoramas, original-image camera estimation, Depth Anything V2 Small relative depth calibrated against SfM and cross-view evidence, fused dense initialization, Brush 0.3.0 Metal 5,000 steps, no RIFE or diffusion. Its reported 41,533 initial points / 46,807 Gaussians / 160.298 s are **single-run observations**, not benchmarks. The no-learned-depth control (115 selected SfM points / 569 Gaussians) was substantially less recognizable, but simultaneously changed initialization density; it does not prove depth accuracy. The synthetic-image comparison has a documented one-pixel border preprocessing difference. See OBJECT_REAL_ONLY.md, OBJECT_NO_DEPTH.md, OBJECT_FOCUS_EXPERIMENT.md.

Main hypothesis: globally registered panoramas can produce a *cross-view-consistent, full-sphere dense initialization* that enables a continuous street Gaussian world. Increasing crop count alone adds angular coverage, not independent camera centers. The nine panoramas are only nine physical viewpoints; do not claim 9 x N crops are independent observations.

## Non-negotiable controls

- Preserve all existing jobs, source hashes, exports, comparison pages and viewer behavior. New runs use new directories and provenance; never overwrite.
- Use the same licensed nine Mapillary panoramas and existing fixed-rig SfM as the initial common frame; inspect pose quality and keep the panorama's virtual crop cameras co-located. Do not independently recover positions for each crop.
- Separate observed RGB, estimated pose, learned depth, synthesized RGB and Gaussian outputs in artifacts and reports. Do not include generated RGB in this experiment.
- Check code, **weights**, training-data terms and dependencies for commercial compatibility before adopting a model. Repository licenses are not automatically checkpoint licenses. DAP and GGPS are CC BY-NC candidates for research only; do not introduce them as production dependencies. Treat PanDA checkpoint terms as unresolved until checked. DA² and DepthMaster are permissive candidates subject to dependency checks.
- M2 MacBook Air 16 GB, local Metal/MPS first; avoid speculative CUDA integration. If a model cannot run, mark NOT RUN with exact blocker and continue with viable alternatives.
- Preserve stage status PASS / FAIL / NOT RUN, commands, versions, hashes, timings, resource counters, visual evidence and uncertainty. Do not equate a successful export with good geometry or view synthesis.
- Maintain separate **appearance holdout** and **geometry holdout** terminology. A target image excluded from Brush RGB training but included in SfM is not independent geometry evidence.

## P0 — Freeze baseline and evaluation

1. Pin the nine real crops, panorama source IDs/hashes, camera matrices/intrinsics, calibration/fusion settings, Brush options and PLY artifacts. Link existing runs, do not retrain by default.
2. Define a fixed evaluation camera set: original input poses, between-pose interpolations, modest lateral translations and selected viewpoints toward scooter, tree, doorway, facade and road. Record whether each camera is an observed, interpolated or extrapolated view.
3. Build a reproducible observation report showing source RGB, depth visualization, calibrated 3D cloud, Gaussian render, comparison at matched poses, geometry diagnostics and failure evidence. For held-out metrics, disclose all training/pose participation.
4. Record baseline performance and visual shortcomings, including stretched splats. No fabricated acceptance thresholds.

Gate: artifacts and comparisons can be reproduced/inspected without modifying the baseline.

## P1 — Full-sphere depth feasibility (no Brush yet)

1. Start with one existing panorama; then an adjacent pair; only then all nine. Keep ERP source resolution and camera conventions explicit.
2. Evaluate (A) Depth Anything V2 on ERP as a deliberately out-of-distribution control, (B) PanDA-Small if weights/license/runtime permit, (C) DA² if weights/runtime permit. Optionally compare overlapping perspective-crop depth stitched back to the sphere as a fallback. Do not silently replace unavailable models.
3. Save RGB, raw relative depth, depth convention (ray range vs camera-Z vs inverse depth), visualization, valid/confidence mask, reprojection diagnostics, inference time and memory. ERP left/right seam and poles require explicit inspection.
4. Backproject ERP pixel (u,v) via longitude/latitude to a unit ray, multiply by **calibrated ray range**, then transform by the *measured* panorama-to-world pose. Never treat arbitrary relative depth as metric distance or confuse pinhole camera-Z with radial range.
5. Exclude sky/invalid depths conservatively and preserve coverage statistics; compare nearby surfaces, building planes, road and trees. A visually plausible single panorama is not sufficient evidence.

Gate: a candidate produces coherent spherical clouds and can proceed to cross-panorama testing. If none does, try overlapping perspective depth with spherical fusion before moving to GS.

## P2 — Common-frame depth calibration and fusion (critical gate)

1. Reuse fixed-rig panorama poses; confirm axes, handedness, camera center and arbitrary SfM scale. Derive all virtual crop poses analytically.
2. Fit relative depth to SfM sparse evidence with robust estimation, and test calibration residuals on held-out sparse tracks. For ERP, calibrate *radial* depth correctly and report angular/region coverage; do not assume a single global affine fit works across all directions.
3. Compare adjacent panorama clouds in overlapping regions: surface-to-surface distance (in arbitrary units), RGB reprojection, depth agreement, visibility/occlusion and seam continuity. Record weak-parallax areas and confidence.
4. Filter contradictory samples, merge into one world frame, voxel-downsample with documented spacing, and retain RGB, source view and confidence/provenance where feasible. Prevent duplicate opaque surfaces and erroneous sky points.
5. Inspect a pair before nine-way fusion. Keep both pre-filter and post-filter clouds for diagnosis.

Gate: overlapping static surfaces agree under the shared frame within **predeclared evidence-based tolerances**, not just visually pleasing snapshots. On failure, isolate pose, calibration and model disagreement before training Brush.

## P3 — Whole-street Gaussian reconstruction

1. Feed the validated global cloud as initialization to Brush, retaining *real RGB only*. Start with overlapping full-horizontal-sphere perspective crops (and vertical coverage as appropriate) with correct fixed-rig intrinsics/poses; crop count is not new viewpoint count.
2. Keep a matched baseline, document training budgets, image count/resolution, splat cap and runtime. Run bounded scale tests rather than increasing all hyperparameters together.
3. Compare continuous street rendering at observed and off-path cameras, not only scooter detail: tree, doorway, building edges, road, depth order, gaps, duplicated geometry, floaters, stretched splats and transitions.
4. Distinguish training-image fit from held-out appearance and independently validated geometry. Keep browser interaction/PLY exports separate from quality PASS.

Gate: a *single spatially continuous* scene survives between-pose motion and limited off-path viewing with documented remaining failures. If it fails, inspect the fused cloud and optimization independently.

## P4 — Independent integrated-engine comparison (research track; can run in parallel)

- InfiniSplat v2: verify actual ERP/multiview input interface, pose requirements, license/weights, runnable hardware and a fair nine-panorama comparison; do not assume hosted demo quality generalizes.
- GGPS/PanoLOG: inspect open rendered scenes/PLY and study panoramic initialization, partitioning and optimization. CC BY-NC research only unless separately licensed; its hundreds/thousands of views are not comparable to nine views.
- UniTriSplat: assess direct spherical training/rendering and portability, without committing to a CUDA port before feasibility.
- Use matched novel camera viewpoints and note dataset/camera/compute differences. Choose backend by evidence, not marketing demos.

Gate: decide retain Brush, augment it, or adopt an independently licensed backend.

## P5 — Scale after one street segment works

Test adjacent spatial blocks, overlap ownership, shared coordinates, duplicate Gaussian suppression, boundary blending, streaming/loading and camera-route continuity. Start with one extra segment; defer cloud service, accounts and large-scale ingestion until reproducible local quality exists.

## Implementation sequence for coding agents

First implementation run is **P0 plus a bounded P1 smoke test**, not P0–P5 at once:
1. Inspect current branch code, docs, pinned artifacts, tests, runtime and existing observation pages. Verify current upstream docs/licenses independently; document unknowns.
2. Produce a concrete file-level design and acceptance matrix; reuse existing spherical projection, SfM, depth and visualization utilities.
3. Implement a minimal one-panorama ERP-depth-to-colored-point-cloud experiment with a model that can actually run locally; keep raw depth, conventions and diagnostics. Add seam and ray/backprojection unit tests.
4. Add a small comparison report accessible through existing lab conventions if actual artifacts exist; do not claim publication until verified. Do not run full GS training in this first run.
5. Run relevant tests and inspect actual outputs. Record PASS/FAIL/NOT RUN and next recommended experiment. Commit and push only verified changes to this feature branch.

## References

- docs/OBJECT_FOCUS_EXPERIMENT.md
- docs/OBJECT_REAL_ONLY.md
- docs/OBJECT_NO_DEPTH.md
- docs/INFORMATION_TOPOLOGY.md
- docs/MAPILLARY_EXPERIMENT.md
- docs/DEPTH_EXPERIMENT.md
- docs/OBSERVATIONS.md
- PanDA: https://github.com/caozidong/PanDA
- DA²: https://github.com/EnVision-Research/DA-2
- DepthMaster: https://github.com/PolyU-VCLab/DepthMaster
- InfiniSplat: https://github.com/zju3dv/InfiniSplat
- GGPS: https://huggingface.co/Insta360-Research/GGPS
