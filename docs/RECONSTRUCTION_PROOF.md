# Reconstruction provenance audit — 2026-11-04

This audit concerns the original `/worlds/reconstructed/` scene. A subsequent
[`/worlds/independent/` scene](INDEPENDENT_RECONSTRUCTION.md) uses 120 raw photos
and supplied lens calibration, with every camera pose, sparse point and Gaussian
newly computed locally. Keep the two artifacts and their evidence distinct.

**The deployed Dozer Gaussian model was trained locally on this Mac.** Its inputs came from the public example dataset: 40 photographs, supplied camera calibration/poses, and a supplied sparse SfM point cloud. It is not a demonstration of recovering everything from 40 unposed photographs. The separate Houseplant viewer sample is a downloaded, already reconstructed Gaussian model.

## What came from upstream, and what was generated here

| Component | Origin / processing |
| --- | --- |
| Photographs | 40 selected views from the 359-view Nerfstudio dozer dataset, using the distributed 752 × 500 `images_4` files |
| Camera calibration and poses | Supplied dataset metadata; locally undistorted and converted for Brush, not newly estimated for this run |
| Initial geometry | Supplied COLMAP sparse points from the full capture; locally converted to 165,875 XYZ/RGB points in `init.ply` |
| Final Gaussian scene | Locally trained by Brush 0.3.0 on Apple M2 / Metal, 1,500 steps; 194,789 Gaussians with appearance, opacity, rotation and scale parameters |
| Railway content | The same locally exported PLY, verified by downloading the public file and comparing SHA-256 |

The inspected upstream ZIP index contains JPEGs, camera metadata and COLMAP files; no PLY, splat, SPZ, PT, PTH or CKPT model. `scripts/fetch-reconstruction-sample.py:174–180` converts upstream `points3D.bin` into `init.ply`. That input PLY contains only `x`, `y`, `z`, `red`, `green`, `blue` fields and is 2,488,305 bytes. The exported scene contains Gaussian parameters and is 17,921,240 bytes. The local adapter invokes the native arm64 Brush executable; it does not fetch a finished Dozer Gaussian model.

## Original deployed run

Preserved local evidence:

- `data/jobs/dozer-1500/job.json`: exact command, 40 views, 1,500 steps, exit code 0, wall time 80.347116 seconds, artifact size/count/hash.
- `data/jobs/dozer-1500/training.log:1`: adapter `Apple M2`, `IntegratedGpu`, `backend: Metal`.
- `training.log:12`: `Using ply "init.ply" as initial point cloud.`
- `training.log:17`: `Loaded dataset with 40 training, 0 eval views`.
- `training.log:115`: `Refine iter 1401, 194789 splats.`
- `training.log:116`: `Done training! Took FormattedDuration(78s).`
- `data/jobs/dozer-1500/resources.txt`: independent `/usr/bin/time -l` process measurements. Brush's training-loop duration and total adapter wall time measure different scopes.

Fresh readback from `https://groundshift-viewer-production.up.railway.app/worlds/reconstructed/scene.ply` matched both the original exported scene and `public/worlds/reconstructed/scene.ply`:

```text
SHA-256 ed28becf4e5a5ee1e238660e58f120f69c1e7786b1cda23f2a5943f341bffa72
```

## Fresh local rerun during this audit

Executed again into a new directory, with no publication step:

```sh
python3 scripts/reconstruct.py data/datasets/dozer-small \
  data/jobs/dozer-proof-20261104 \
  --steps 1500 --resolution 512 --max-splats 200000
```

| Check | Result |
| --- | --- |
| Machine | PASS: Mac14,2, Apple M2, 17,179,869,184 bytes unified memory |
| Live native process | PASS: PID 9387 running the arm64 `brush_app` with the recorded dataset/output arguments; observed 34 seconds after launch |
| Before output export | PASS: `scene.ply` absent during the live-process observation |
| Metal training | PASS: new native log identifies M2/Metal, 40 training views, refinement and completion |
| Native process/export | PASS: exit 0, 82.351358 seconds, 194,871 Gaussians, 17,928,784 bytes |
| Rerun artifact SHA-256 | `fa4cab138f95dfb70a1dd01e47829674d6e6094ef5867077b8db75fb10c5cf88` |
| New rerun's browser rendering | NOT RUN; the already deployed original artifact has separate browser verification |
| Raw-image-only full pose recovery | Not established by this run; the earlier independent CPU experiment registered only 16/40 views |

The two training runs produced different counts and hashes. This establishes another successful native training/export execution, not bit-for-bit deterministic reproduction. The deployed artifact remains the original run.

New evidence lives in `data/jobs/dozer-proof-20261104/{job.json,training.log,resources.txt,process-observation.json}`. `data/validation/reconstruction-proof-20261104.json` records input hashes, process evidence, log hashes and the public/local artifact comparison. Full datasets, generated models and raw logs remain outside Git.

## Acquisition-record discrepancy found and explained

44 of the 45 current prepared input files match the first `acquisition.json` hashes exactly. The remaining file, `transforms.json`, differs because the `"ply_file_path": "init.ply"` reference was added before training, but its original acquisition checksum was not refreshed.

Removing only that field and serializing with the original formatting reproduces the original 24,335-byte file's SHA-256 exactly (`90a7183069dc5672873c088884e8e1207fef0638b382d57ad629ab008cc446ec`). The current 24,366-byte manifest matches the corrected clean acquisition under `dozer-small-repro` (`61ba4700562e3c590eaf8b548d03ef60abb4d4daab873f8a7c15e41e27b19d43`). This confirms the pose/intrinsic values did not change; the initial-cloud reference did. The original acquisition report is preserved, and the audit records this bookkeeping discrepancy rather than silently rewriting historical evidence.

The `browserRendering: "NOT RUN"` field in native job reports concerns that native job's scope. It does not negate the separately performed browser inspection documented in [VALIDATION.md](VALIDATION.md) and [DEPLOYMENT.md](DEPLOYMENT.md).
