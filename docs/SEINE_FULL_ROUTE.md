# Seine route expansion — 2026-11-07

The requested target is the previously selected **876 consecutive public ERP
photographs, ranks 808–1683**, approximately **2,185.31 m of source GPS polyline**
along the Paris Seine south bank and connected streets. This is the selected
route, not the whole river. Source GPS length is not metric reconstruction
accuracy. The original [58 m experiment](PARIS_STREAMING.md), all historical
worlds, source bytes and native exports remain intact.

## Execution design

Reuse the completed ranks 988–1011 reconstruction. Extend in bounded windows of
24 real panoramas, advancing 16 centers with eight shared sources. Cover the
remaining forward route, then extend backwards from the baseline. Endpoint
windows overlap further as needed. The deterministic plan covers all 876
sources in 55 windows, including the existing baseline: 54 new native jobs.

Each job preserves the already executed Paris configuration: six 512 px,
100-degree crops for fixed-rig PyCOLMAP 4.2.1 CPU camera estimation; twenty
768 px, 80-degree real RGB crops per center; pinned Depth Anything V2 Small
on local MPS; per-crop robust affine inverse-camera-Z calibration to observed
SfM points; dense seeding; Brush 0.3.0 Metal with 8,000 steps, 768 px, an
800,000 Gaussian ceiling, SH degree 1 and seed 42. No diffusion, synthesized
views, GPS-derived camera poses or panorama/depth-shell background is used.
Unsupported depth fits remain excluded. The former nine-panorama quality
campaign remains closed.

The upstream versions, model revision, licenses and actual interfaces are
recorded in [the baseline report](PARIS_STREAMING.md). The source remains
Immergis pour la Ville de Paris / Panoramax IGN, captured 2025-05-08, under
[Open Licence 2.0](https://github.com/etalab/licence-ouverte/blob/master/open-licence.md).
Public source metadata and original checksums are retained; original HD images,
model weights and raw execution logs are local only.

### Coordinate connection

`seine_alignment.py` matches identical source identities and SHA-256 values,
then aligns the independently estimated physical camera poses. Shared camera
orientations determine relative rotation; centers determine positive scale and
translation. This avoids the poorly constrained roll of a center-only fit on
a nearly straight street. It does not replace estimated poses with GPS.

At least six shared physical cameras are required. The engineering gate uses
75% consensus, center residual at most 0.25 of the reference median camera step,
and orientation residual at most 3 degrees. A deterministic quarter of shared
poses is excluded from transform fitting, checked, and then the inlier poses
are refitted. Those images still participated in SfM: this is an internal
alignment diagnostic, not held-out imagery or independent geometry truth.

The raw SfM similarity transforms are composed into the baseline frame. For
rendering, the segment-viewer-to-route-viewer transform is explicitly
`baselineAssetToWorld * rawAlignment * inverse(segmentAssetToWorld)`.
Camera orientations are rotated without scaling their basis. Global anchors
and camera-path positions are transformed once. A failed alignment stops the
connection and retains its evidence rather than inventing a continuous road.
Accumulated drift along the complete chain is still unmeasured.

### Streaming and publication

Every completed native export gets a whole SPZ and an official Spark 2.4.0
quality/SH1/csplat chunked RAD derivative. Each immutable route snapshot includes
only completed, aligned, consecutive source coverage. The viewer keeps one
active segment and at most one incoming segment in a shared fourteen-page
(917,504-slot) pool, targeting 800,000 selected splats. It loads segment roots
on demand, preserves the previous segment if loading fails, and uses a short
complementary opacity transition. Camera ownership has hysteresis. Whole-SPZ
comparison refers to the current segment at the same camera and field of view.

This keeps storage and active residency separate: it does not keep all 55 roots
resident or claim that every distant feature along the entire route is present
in the active local reconstruction. Selection readiness is not proof of fully
decoded, displayed detail. Actual independently trained boundary rendering is
checked separately from unit tests and synthetic lifecycle fixtures.

As soon as a scene or observation becomes deployable, publish it through the
existing checksum-pinned Railway package, concurrently with remaining work.
Preserve all prior observations, label incomplete stages, and verify live file
hashes and public rendering after dispatch. See [deployment rules](DEPLOYMENT.md).

### Resume and storage

The coordinator records every native command, exit code and elapsed time. A
completed stage is reused; a failed or interrupted native stage is not silently
overwritten. Route exports are assembled in a distinct temporary directory and
renamed atomically, so an export interruption can be retried without retraining.
A process lock prevents duplicate coordinators. Six GiB free is the minimum
before acquiring the next window; insufficient space is an explicit blocker.

Originals are reused only after actual checksum/JPEG validation. Depth reuse
also verifies the exact model/revision, default 518×518 neural input, original
crop bytes, finite float32 prediction, shape/range and output checksums. Cached
predictions remain relative inverse-depth-like values. Cache hits are recorded
separately from new MPS inference and do not inherit a fabricated current timing.
Immutable duplicate files can share hardlinks; changes to frozen publication
paths must use atomic replacement, never write through a shared inode.

New completed route jobs share byte-identical PNGs across overlap windows and
stage copies. Native PLY viewing derivatives share the original export bytes.
After publishing an atomic scene snapshot, `seine_depth_archive.py` losslessly
archives only that new completed job's depth NPY files. A reversible byte shuffle
followed by zlib compression preserves every original NPY byte, with its SHA-256
and alias manifest. It verifies persisted archive bytes before removing raw
aliases; interrupted operations remain readable/restorable. Previous experiments
and active jobs are excluded. Cache hits transparently recover the exact original
prediction bytes; this changes storage only, not model precision or geometry.

The checked-in codec was actually executed read-only on all 480 baseline NPYs:
1,132,523,520 B became 532,989,536 B (47.062%), with every exact-byte round trip
verified, in 34.02 s and 39.85 MB maximum process RSS. No baseline NPY was changed.
The approximately 19.45 GB full-route depth figure is extrapolation, not measured
full-route storage. The first new completed job has now actually archived all
480 exact NPY files: 1,132,523,520 B became 492,364,393 B in 50.896771 s. The
persisted archives passed original-byte SHA verification before raw aliases were
removed. Concurrent reconstruction, source downloads and publishing mean the
filesystem free-space delta is not an isolated savings measurement.

Below 20 GiB free, the coordinator can evict an older completed **new** segment's
reproducible PNG working cache. It retains the baseline, newest segment and the
next window's shared-image reference. Before removing any candidate it regenerates
the exact PNG bytes from preserved ERP originals, verifies every SHA and retains
the projection code, library versions and restoration manifest. Original JPEGs,
depth bytes/visualizations, SfM databases and poses, logs and native exports are
excluded. Interrupted eviction is resumable; unrelated missing cache files still
fail rather than being silently ignored.

The real read-only baseline proof regenerated 1,104 recipes covering 2,832 PNG
aliases: all encoded SHA-256 values and sizes matched. It took 249.392120 s with
1,387,151,360 B maximum process RSS. Actual new-job PNG eviction is **NOT RUN**;
this is a regeneration proof, not a measured storage-saving result. Evidence:
`data/validation/paris-full-route-20261107/storage/png-baseline-proof/manifest.json`.

```sh
# Restore all exact original NPY paths in one archived new segment, if needed.
data/tools/venv/bin/python scripts/seine_depth_archive.py \
  data/jobs/seine-full-20261107/segment-1004-1027 --restore

# Restore exact generated PNGs after an actual verified cache eviction.
data/tools/venv/bin/python scripts/seine_png_cache.py restore \
  data/jobs/seine-full-20261107/segment-RANK-RANK/png-cache-proof-TIMESTAMP/manifest.json
```

An additional frozen-publication-only deduplication verified matching encoded
bytes, owner, mode, flags, xattrs and ACLs, then atomically shared 7,969 copies.
Free filesystem space increased by 13,500,645,376 B during that operation;
concurrent filesystem activity means this net change is not an isolated savings
benchmark. A subsequent audit found no remaining eligible replacements. Sources,
native job artifacts, archives, logs and active staging were excluded.

## Reproduce

Use the existing locally installed tools from the baseline setup. The selected
route manifest is `data/jobs/tourist-streaming-20261107/route.json`; the completed
baseline is `data/jobs/paris-streaming-20261107/`. The coordinator deliberately
requires these original provenance records and actual baseline outputs.

```sh
# Build one additional window and a new immutable route snapshot.
data/tools/venv/bin/python scripts/seine-route.py \
  data/jobs/seine-full-20261107 --limit 1

# Continue the remaining fixed windows, preserving completed work.
data/tools/venv/bin/python scripts/seine-route.py \
  data/jobs/seine-full-20261107

# Test planning, coordinates, source/depth cache integrity and failure retention.
data/tools/venv/bin/python -m unittest discover -s scripts/tests -p 'test_seine*.py' -v
data/tools/venv/bin/python -m unittest discover -s scripts/tests -p 'test_infer_seine_depth.py' -v
```

`route-run.json` contains overall status, completed segment lineage and snapshot
paths. Each segment has `runner.json` (the first pilot has `pipeline.json`),
`alignment.json`, depth/fusion reports and the native `training/job.json`.
Snapshots contain sanitized `coverage.json`, the route index, explicit segment
transforms, source-camera path, licensed metadata and selected renderable assets.
Never publish the raw coordinator/job directories.

## Actual observations so far

| Check | Result |
| --- | --- |
| Added ranks 1004–1027 acquisition | PASS 24 original JPEGs, 188,213,148 B, 202.955850 s; eight overlap the baseline |
| New fixed-rig SfM | PASS 144/144 crops, 8,069 sparse points, 0.616063 px mean reprojection error; wrapper 126.461858 s |
| First shared-pose alignment | PASS 8/8 inliers; scale 1.00909535; maximum center error 0.00507274 reference steps and orientation error 0.0691011 degrees |
| Transform-only held-pose check | PASS both withheld poses; not independent SfM truth |
| First added DAV2 execution | PASS 480 actual MPS predictions, wrapper 362.371952 s |
| First added calibrated seed | PASS 308/480 supported fits, 186,839 initial points; 172 maps excluded; wrapper 24.074309 s |
| First added native GS export | PASS 8,000 steps on Apple M2 Metal, 800,000 Gaussians; 73,600,652 B PLY |
| First added delivery derivatives | PASS 15,945,260 B SPZ; 26,045,905 B chunked RAD including its index |
| First connected export | PASS two independently trained segments, 40 actual source poses, ranks 988–1027; 98.749536 m source GPS coverage |
| Independent two-segment local rendering/interaction | PASS Chrome 3/3 and desktop WebKit 3/3; actual Fly boundary, reversal, current-segment SPZ, metadata/RAD failure retention and retry |
| Independent two-segment public rendering | NOT RUN at this documentation update; first snapshot dispatched for separate public checks |
| Physical iPhone boundary/long-session test | NOT RUN |
| Entire 876-source reconstruction | RUNNING, not complete |
| Global metric accuracy / long-route drift | NOT ACCEPTED / NOT RUN |

The first new native run completed without restart or configuration changes:
5,502 s reported by Brush, 5,511.631969 s wrapper wall time, 567,656,448 B maximum
RSS and 2,885,208,344 B peak process footprint. A long gap in refinement logs
coincided with heavy host memory compression/decompression and approximately
13 GB swap usage; process-specific GPU counters still advanced. Refinement then
resumed through 8,000 steps. Those observations do not establish a single cause.
Private diagnostic evidence is retained in
`data/validation/seine-full-20261107/brush-slowdown-diagnostic.json` and
`brush-progress-after-slowdown.json`.

Runtime values are actual one-off wall times with concurrent development and
brief browser work on the same M2, not isolated benchmarks. The old 1,018-second
baseline is not a reliable ETA: this added window took materially longer on the
current machine. The whole route may require more than a day;
no full-route runtime is measured yet. Source preparation, depth, exports and
failure recovery add time. Storage is also bounded: unique full
float32 depth predictions alone would approach 41 GB for all 876×20 crops.
Frozen publication staging was deduplicated by verified identical bytes while
preserving paths and rollback packages; this is not deletion of source evidence.

Automated planning/coordinate/failure/cache checks include 22 alignment/route
tests, nine cached-depth tests, nine depth-archive tests, eight exact PNG-cache
tests and nine source-route tests. The full Python run before first publication
executed 317 tests: 312 PASS and five skipped, in 12.024 s. Browser suites against
the first real two-segment frozen export passed in 110.817168 s (Chrome) and
86.534011 s (WebKit); those are suite wall times, not rendering benchmarks.
Evidence: `data/validation/seine-route-20261107/browser-real-batch.json` and its
retained engine logs/screenshots.
They do not establish native training, rendering, collision geometry or
surveyed street accuracy. Live viewer and execution evidence will be appended
as those operations actually finish.

### Unattended continuation

The native coordinator and source acquisition continue locally. A separate
locked publisher watches atomic exports every five seconds, immediately prepares
and uploads the checksum-pinned incremental package, and queues the exact branch
pointer. The existing Railway environment's GitHub auto-deploy UI currently says
**Auto deploy unavailable**; a Git push alone is not deployment proof. The
authorized thread follow-up checks every five minutes and uses the existing
healthy Railway connector for pending dispatches. Public status/hash checks and
browser acceptance remain separate. Queue ownership, receipts and the manual
metadata-overlay procedure are documented in [DEPLOYMENT.md](DEPLOYMENT.md).
