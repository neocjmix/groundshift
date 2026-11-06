# Paris: actual reconstruction and bounded spatial delivery — 2026-11-07

The user requests an actual autonomous result after the [source selection](TOURIST_STREAMING.md).
This run uses the acquired **24 real ERP photographs, source ranks988–1011**,
approximately58.02m of source GPS path. The selected876-record/2.185km route
remains an expansion source, **not an already reconstructed2.185km world**.
The previous nine-panorama quality campaign stays closed and unchanged.

## Implemented path

1. Preserve/checksum the24 publicly licensed12,288×6,144 originals locally.
2. Six512px100° pinhole views per source enter the existing fixed-rig CPU
   PyCOLMAP4.2.1 pipeline. Intrinsics and same-center rotations come from the
   analytic crop projection; all world positions/orientations and sparse
   points are estimated from the photos. No GPS/compass values become poses.
3.20real768px80° tangent projections per panorama cover the sphere. Roof/black
   nadir beyond ERP v=.78 is loss-masked. This does not recover missing ground
   or produce collision geometry. No RGB interpolation or diffusion is used.
4. Pinned Depth Anything V2 Small runs480actual predictions on local MPS
   (revision`5426e4f0f36572d16453bbda7a8389317b1bef99`, model/code Apache2.0).
   Raw relative inverse-depth-like values are not meters. For each crop,
   robust affine **inverse camera-Z** is fitted to observed SfM points from
   that physical camera, retaining a deterministic point-ID modulo5 split.
   This split tests internal calibration only, not held-out photographs or
   independent geometry. Unsupported fits are excluded from dense seeding.
5. Calibrated Z and actual pinhole rays form colored point candidates in the
   shared SfM frame. Voxel reduction and a180k dense seed cap plus sparse
   points initialize the existing Brush0.3.0 Metal process. The voxel size
   derives from the preserved SfM record order; it is a numerical thinning
   heuristic, not surveyed spacing. One8k-step768px800k-ceiling run is used.
6. Preserve the native PLY and metadata. A separate viewing derivative selects
   the actual24physical centers in verified source order, with an ERP-center
   viewing orientation and explicit continuity/component metadata. Scale
   remains arbitrary; straight interpolation is not a reconstructed road.
7. The existing Spark2.4.0 CPU/WASM converter writes whole-scene SPZ. Spatial
   delivery assigns each native Gaussian **once** to its nearest recorded
   camera and groups four adjacent camera regions per SPZ chunk. Raw asset
   coordinates and one global fixed-point precision remain unchanged.
   Chunk anchors alone are transformed into the viewer frame. Ownership bytes
   and checksums remain local diagnostic evidence; no duplicated opacity is
   deliberately added at region boundaries.
8. The viewer fetches a small versioned chunk index, then the nearest region
   and adjacent regions: at most3resident chunks, one fetch/decode in flight.
   Obsolete requests abort; an uncancellable late Spark decode is disposed
   before the next decode starts. Evicted meshes release their resources,
   with no decoded JS cache. Reversing, jumps and errors have explicit state
   and manual retry. Every chunk's byte length/SHA/count is checked. The
   whole-scene file stays available as an explicit comparison mode; it is
   not eagerly fetched in lazy mode.

This is a small extension of the existing local process/world/static viewer
boundaries. No service, database, account, cloud training or generic streaming
framework is introduced. Archived panorama/shell backgrounds remain disabled.

## Executed evidence so far

| Operation | Actual observation |
| --- | --- |
| CPU fixed-rig SfM | PASS24physical centers/144of144crops,8,686points,57.833446s,0.596421px mean reprojection error |
| Filtered observed SfM anchors |6,899sparse points;24physical groups |
| DAV2 MPS | PASS480predictions,71.915505s; output/input checksums retained |
| Depth calibration/seeding | PASS309fits,171unsupported depth maps excluded;6,125,498dense candidates after reduction;186,899initial points,18.245634s |
| Native GS training/export | RUNNING; final measured job status will be recorded after completion |
| Lazy rendering / public interaction | NOT RUN before export |

Native wall time is a one-off process observation on the user's M2/16GB Mac;
CPU source/test/build work runs concurrently. It is not an isolated benchmark.
Compressed bytes, resident Gaussian counts and process RSS do not establish
GPU-memory usage. Raw logs, checkpoints, original HD images, inference outputs
and weights remain local under`data/jobs/paris-streaming-20261107/`.

## Delivery validation and limits

Same-camera PLY→SPZ→reloaded-PLY and all-chunk-union renders cover route
positions, forward/backward and vertical directions. Their purpose is to
detect codec/partition loss separately from reconstruction quality. There
are no withheld source photographs in this serving prototype. Existing
nine-panorama held-view quality scores are not reused as Paris measurements.

Spatial ownership alone does **not** make a3-chunk subset visually identical
to the full scene. A distant building, tree or large Gaussian can be visible
from outside its nearest-camera region; unloading it can create holes/pop-in.
The all-chunk union test isolates this from data loss during partitioning.
The live status exposes resident counts, encoded file sums, pending work,
evictions and cumulative transferred bytes. It does not label estimated
depth, source GPS or route interpolation as accurate geometry or free walking.

Official [Spark SplatMesh/disposal](https://sparkjs.dev/docs/splat-mesh/)
and [native RAD/LoD paging](https://sparkjs.dev/docs/lod-getting-started/)
were inspected against the pinned installed2.4.0 interfaces. Native RAD is a
valid future alternative with multiresolution coverage. It changes the
delivery representation and requires an offline LoD build; Rust/cargo is not
installed in this environment. This first control deliberately retains SPZ
and unchanged Gaussian ownership to isolate region loading. No claim is made
that SPZ region streaming is the best final city-scale format.

## Reproduce

First reproduce the pinned24-source acquisition from[TOURIST_STREAMING.md](TOURIST_STREAMING.md).
Use a **new** job directory and preserve every failed attempt. The experiment
script currently pins the acquired Paris source location, not arbitrary cities.
Copy its explicitly public provenance JSON to the new job, then:

```sh
data/tools/venv/bin/python scripts/prepare-panoramas.py \
  data/jobs/tourist-streaming-20261107/hd-initial/images JOB/sfm-inputs \
  --provenance JOB/provenance.json --size 512 --hfov 100
data/tools/colmap-venv/bin/python scripts/estimate-panorama-poses.py \
  JOB/sfm-inputs JOB/sfm --threads 4 --max-features 4096
data/tools/venv/bin/python scripts/paris-pipeline.py prepare JOB
data/tools/colmap-venv/bin/python scripts/paris-pipeline.py anchors JOB
```

Pass the paths from`JOB/tangent-inputs/inference-inputs.json` to the existing
`infer-relative-depth.py JOB/depth` CLI using the diffusion-venv interpreter
and`HF_HOME=data/tools/depth-hf-cache`; this uses the existing pinned local
weights, not an alternative model. Then:

```sh
data/tools/venv/bin/python scripts/paris-pipeline.py fusion JOB
data/tools/venv/bin/python scripts/reconstruct.py JOB/dataset JOB/training \
  --steps 8000 --resolution 768 --max-splats 800000 --title 'Paris · first58m' --id paris-58m
data/tools/venv/bin/python scripts/paris-pipeline.py finalize JOB
node scripts/compress-world.mjs JOB/view-world JOB/spz-world
node scripts/partition-world.mjs JOB/view-world JOB/spz-world JOB/stream-world
node scripts/compare-spatial.mjs JOB/stream-world JOB/comparison JOB/view-world/scene.ply
```

Native source acquisition and all output directories are excluded from Git.
Publication includes only the selected derived world, metadata, actual previews
and necessary explicitly licensed source comparisons. Source attribution is
**Immergis pour la Ville de Paris / Panoramax IGN**, captured2025-05-08,
accessed2026-11-07, **etalab-2.0/Open Licence2.0**. This is publicly
privacy-processed vehicle imagery, not the user's private footage. Previous
worlds, observation reports and immutable rollback packages are retained.
