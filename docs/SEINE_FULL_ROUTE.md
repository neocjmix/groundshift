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
| Independent two-segment public rendering | PASS desktop WebKit 3/3 against actual Railway snapshot002; maximum two resident segments and fourteen pages, settled queues empty, no page errors |
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
Public evidence is `public-route-browser-summary.json` in the same directory.
It uses desktop WebKit with an iPhone viewport/input profile and an explicit
fullscreen-unavailable fixture, not a physical phone. Actual public Fly movement
selected 673,596 splats in the new segment; same-camera whole-SPZ comparison and
return preserved position, orientation and FOV. Both intentionally injected
single-request HTTP 503 failures retained the old segment and recovered through
retry. Recognizable road/facades/sidewalk/trees/intersection are visible, with
road/car smearing and stretched or duplicated thin structures. Settled frames
do not establish a perceptually seamless transition or surveyed street geometry.
The static tests alone do not establish native training or rendering; neither
the tests nor the browser checks establish collision geometry or surveyed street
accuracy. Further execution evidence is appended as operations finish.

### Second added window and complete source acquisition

Ranks 1020–1043 completed the same declared configuration without a restart.
SfM registered 144/144 crops, with 5,991 points and 0.598966 px mean reprojection
error. All eight shared poses passed alignment: scale 0.98944679, maximum center
residual 0.003959 reference steps, maximum orientation residual 0.025457 degrees.
Both transform-withheld poses passed; these remain internal SfM diagnostics.

DAV2 actually inferred 320 new crops on MPS in 236.181894 s and reused 160
byte-verified predictions from the neighboring job's lossless archive. The whole
depth stage took 292.181844 s. Calibration accepted 291/480 crops and produced
185,405 initial points; the other 189 maps were excluded. Brush finished 8,000
steps and 800,000 Gaussians in 3,918 s reported training time, 3,928.416475 s
wrapper time, with 537,264,128 B maximum RSS and 2,895,005,952 B peak footprint.
The export is a 73,600,652 B PLY, a 15,761,921 B SPZ and 25,963,264 B chunked RAD
including its index. These are concurrent-run measurements, not speed benchmarks.

Snapshot003 contains three independently trained segments, 56 unique physical
source poses, ranks 988–1043 and 139.263891 m of source GPS path. Its original
export receipt records browser rendering **NOT RUN**; later public checks must
identify this snapshot explicitly rather than inherit snapshot002's PASS.
Global geometry remains **NOT ACCEPTED**. Native evidence is retained under
`data/jobs/seine-full-20261107/segment-1020-1043/` and `route-world-003/`.
The subsequent actual public snapshot003 check **PASS**ed one focused desktop
WebKit 27.2 case: Fly from the second to third segment and back at recorded view
35. At most two segments and fourteen pages were resident; settled endpoints had
empty work queues, no page errors and no eager whole-SPZ requests. The handoff
preserved position, orientation and 80-degree FOV in both directions. Actual
frames show the street and buildings, with road/car blur and distorted facades.
This is an iPhone viewport/input profile on desktop, not a physical iPhone, a
full-route test or a perceptual seamlessness measurement. Evidence:
`data/validation/seine-route-20261107/public-route-003-browser-summary.json`.

The job's exact depth archive passed verification for 800 aliases of 480 unique
NPYs: 1,132,523,520 raw bytes correspond to 426,718,928 encoded bytes, of which
280,171,044 bytes were new blobs. It took 33.746636 s and retained recoverability.

All 876 selected original JPEGs are now acquired locally in fourteen batches:
6,521,351,364 B, each 12,288×6,144 pixels. An independent file audit passed
identity/rank coverage, actual sizes/SHA-256 and JPEG headers/dimensions in
6.125874 s; full pixel decoding was **NOT RUN**. Acquisition wall time was
6,871.478156 s including forty reused originals, not a pure download benchmark.
Evidence: `data/jobs/seine-full-20261107/source-acquisition-complete.json`.
Source acquisition is complete; reconstruction of the entire route is not.

### Fourth connected segment

Ranks 1036–1059 completed the unchanged 8,000-step/800,000-Gaussian configuration
on Metal. Snapshot004 joins four segments and 72 physical source poses over
179.310725 m of source GPS path. Native wrapper time was 2,453.837004 s
(Brush reported 2,448 s), maximum RSS 805,617,664 B and peak footprint
2,915,420,608 B. This differing concurrent-run duration does not establish a
training speed improvement.

All 144 SfM crops registered (5,274 points, 0.597475 px mean reprojection error).
Eight shared poses and both transform-withheld checks passed; maximum shared
center/orientation residuals were 0.014499 reference steps / 0.068385 degrees.
DAV2 inferred 320 new crops in 251.490545 s and reused 160 exact archived maps;
the whole depth stage took 301.289096 s. Calibration retained 287/480 maps and
184,453 seed points. Export sizes are 73,600,652 B PLY, 15,928,193 B SPZ and
26,091,792 B RAD including its index. Exact depth archival passed in 23.440312 s,
with 426,695,447 encoded bytes for 480 unique predictions (287,183,836 new blob
bytes). Evidence remains under `data/jobs/seine-full-20261107/segment-1036-1059/`.
The immutable snapshot's browser receipt starts at **NOT RUN**; snapshot003's
public PASS remains historical. Global geometry is still **NOT ACCEPTED**.
The later actual public snapshot004 check **PASS**ed the existing focused
WebKit case from third to fourth segment and back at recorded view 51. It kept
at most two segments/fourteen pages, preserved camera position/orientation/FOV,
and settled with no pending work, page errors or eager SPZ requests. Actual
frames show a recognizable street with road/vehicle blur and distorted tree and
facade edges. Physical iPhone, perceptual seamlessness and full-route geometry
remain unverified. Evidence:
`data/validation/seine-route-20261107/public-route-004-browser-summary.json`.

### Further completed increments

Each row is an actual unchanged 8,000-step/800,000-Gaussian Metal run. Source
counts are unique physical panoramas across the connected snapshot; GPS length
is not reconstructed metric accuracy. Detailed source, pose, depth, native and
archive receipts remain in the matching `segment-FIRST-LAST/` job directory.

| Snapshot | Added ranks | Connected sources / GPS path | Native wrapper seconds | SPZ / RAD bytes | New public boundary |
| --- | --- | --- | --- | --- | --- |
| 005 | 1052–1075 | 88 / 214.834239 m | 1,062.463517 | 15,959,587 / 26,167,680 | PASS one public WebKit case |
| 006 | 1068–1091 | 104 / 255.782957 m | 1,040.793582 | 16,019,693 / 26,124,281 | PASS one public WebKit case |

For 005, SfM registered all 144 crops (6,105 points, 0.590331 px reprojection
error); all eight shared poses and both transform-withheld checks passed.
DAV2 inferred 320 maps on MPS in 44.448657 s, reused 160 exact maps and took
83.739180 s overall. Calibration retained 343/480 maps and 185,472 seed points.
Native maximum RSS was 724,254,720 B and peak footprint 2,901,608,944 B.
Exact depth archival passed in 23.948872 s (440,303,176 encoded bytes,
292,218,400 new blob bytes). The large wall-time variation across jobs is an
observation, not evidence of a model/configuration change or isolated speed gain.
The focused public005 Fly check crossed fourth to fifth segment and returned at
recorded view 67. It preserved camera position/orientation/FOV, stayed within two
resident segments/fourteen pages, and settled with empty queues, no page errors
or eager whole-SPZ requests. Actual frames show a recognizable road/intersection
with persistent road smearing, vehicle ghosts and distorted facade/tree edges.
Evidence: `data/validation/seine-route-20261107/public-route-005-browser-summary.json`.
This remains desktop WebKit with an iPhone profile; physical iPhone and global
geometry acceptance are not established.

For 006, all 144 SfM crops registered (7,353 points, 0.638448 px reprojection
error). All eight shared poses passed alignment, with scale 1.13660548,
maximum center residual 0.006298 reference steps and orientation residual
0.046252 degrees; both transform-withheld checks passed. These are internal
alignment diagnostics, not independent street geometry. DAV2 inferred 320 maps
on MPS in 44.542876 s and reused 160 exact maps; the depth wrapper took
81.644144 s. Calibration retained 326/480 maps and 186,476 seed points.
Native maximum RSS was 850,722,816 B and peak footprint 2,911,373,760 B.
Exact depth archival passed in 23.343513 s (421,966,768 encoded bytes,
276,869,696 new blob bytes). The coordinator continued to ranks 1084–1107
without restarting training or changing the declared configuration.
The public006 check passed one focused fifth-to-sixth-and-back Fly case at
recorded view 83. Selected counts were 580,096 → 694,110 → 626,430; residency
stayed within two segments/fourteen pages, settled queues were empty and there
were no page errors or eager whole-SPZ requests. Camera position/orientation/FOV
were preserved across ownership changes. The inspected public frame shows an
intersection, crossing, signs and buildings, with strong road/vehicle smearing
and distorted facade/pole edges. Evidence:
`data/validation/seine-route-20261107/public-route-006-browser-summary.json`.
Physical iPhone testing remains **NOT RUN**; global geometry **NOT ACCEPTED**.

### Unattended continuation

The native coordinator continues locally using the completed source cache. A separate
locked publisher watches atomic exports every five seconds, immediately prepares
and uploads the checksum-pinned incremental package, and queues the exact branch
pointer. The existing Railway environment's GitHub auto-deploy UI currently says
**Auto deploy unavailable**; a Git push alone is not deployment proof. The
authorized thread follow-up checks every five minutes and uses the existing
healthy Railway connector for pending dispatches. Public status/hash checks and
browser acceptance remain separate. Queue ownership, receipts and the manual
metadata-overlay procedure are documented in [DEPLOYMENT.md](DEPLOYMENT.md).

Publication now keeps the last selected GS preview instead of reverting each
increment to the baseline image. It remains labeled as a prior reference, not
proof of the new snapshot. Earlier browser checks move into snapshot-keyed
history, while the new current snapshot starts at **NOT RUN**. Eight publication
boundary tests and five watcher tests passed after this metadata correction;
those fixtures do not establish rendering.
The current coverage measurement row also advances directly from each completed
snapshot, so it cannot retain an older source count or distance beside the new
overview. Nine publication tests passed after adding this regression check;
snapshot-specific past browser measurements remain unchanged.
