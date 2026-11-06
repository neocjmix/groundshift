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

## Executed evidence

| Operation | Actual observation |
| --- | --- |
| CPU fixed-rig SfM | PASS24physical centers/144of144crops,8,686points,57.833446s,0.596421px mean reprojection error |
| Filtered observed SfM anchors |6,899sparse points;24physical groups |
| DAV2 MPS | PASS480predictions,71.915505s; output/input checksums retained |
| Depth calibration/seeding | PASS309fits,171unsupported depth maps excluded;6,125,498dense candidates after reduction;186,899initial points,18.245634s |
| Native GS training/export | PASS M2 Metal,8,000steps,768px,800,000Gaussians;1018.285510s;73,600,652B PLY |
| Whole SPZ conversion | PASS15,921,380B,78.3679% smaller;800k/SH1/coordinates retained |
| SPZ spatial partition | PASS6unique-ownership chunks,15,863,971B; nearest3=391,088initial/408,912end points |
| Spatial interaction | PASS local4/4 then public transition/reverse/503retry; quality **FAIL**: distant coverage disappears |
| Native RAD conversion | PASS official Spark2.4.0 CPU builder,7.81s,17files/26,264,088B gsplat |
| Native compact RAD | PASS conversion/16views,17files/25,950,408B: only1.19% smaller; no retraining |
| Native LoD public browser | PASS actual headed Chrome156,cacheOFF,start/end/reverse/whole toggle; <=8pages |
| Public first snapshots |349,915/349,921selected,8pages,13,226,520B received body; ready signals7397.97/9639.68ms |
| Full2.185km GS/streaming | **NOT RUN**;24HD images reconstructed,852selected sources not acquired |

Native wall time is a one-off process observation on the user's M2/16GB Mac;
CPU source/test/build work runs concurrently. It is not an isolated benchmark.
Native `/usr/bin/time -l` reports maximumRSS757,301,248B and peak footprint2,914,159,016B.
These refer to the process, not isolated GPU allocations.
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

### What worked and what failed

The first nearest-three-chunk policy fails appearance preservation. In16fixed
768px views (seven route positions, both headings, plus up/down), mean RGB MAE
is35.1986/255,maximum76.1648. Distant buildings and sky become black. Enabling
all six chunks yields **pixel-exact** results against the whole SPZ in the
separate16-view control. Partitioning retained the data; selection removed
visible remote geometry. This failed trial remains published in the catalog.

[Official native RAD/LoD documentation](https://sparkjs.dev/docs/lod-getting-started/)
and pinned Spark2.4.0 source/CLI were then inspected. Native multiresolution
paging preserves coarse distant coverage while loading finer visible GS. A
small optional `paging` index feeds native `PagedSplats`; Spark owns selection,
eviction and its524,288-slot/eight-page pool. Target selection is350k and two
fetchers. The adapter verifies exact bytes/SHA of every declared root/chunk and
records actual requests/body bytes/pending/errors. Whole SPZ is fetched only
when explicitly selected. No photo/depth-shell backdrop is rendered.

The official MIT source is pinned to tagv2.4.0,commit
`ffe210dc0a45d0515a06c9235878108112827d61`. Rust was installed locally under
ignored `data/tools`, without modifying shell profiles. Initial compilation
**FAIL** (`library System not found`) is retained; explicit CommandLineTools
SDK/linker settings repair it. The executable's actual CLI was used with
`--quality --gsplat --max-sh=1 --rad-chunked`; website/default guesses were not
used. CPU conversion took7.81s,maxRSS244,072,448B.17files include derived coarse
parent nodes, so26.26MB is greater than the complete15.92MB SPZ; lazy transfer
and bounded residency, rather than smaller total storage, are the purpose.

A second **encoding-only** derivative with`--csplat` totals25.95MB,1.19% less.
It is published for comparison, but this small gain does not justify another
format sweep. This is the same newly trained Paris GS, not another training run.

| Same-camera768px comparison,16views | Mean MAE /255 | Worst MAE | Worst fraction with max RGB difference>20 | Strict all-view screen |
| --- | ---: | ---: | ---: | --- |
| Whole SPZ vs native PLY |1.03583 |1.09085 | Not this test's criterion | PASS declared codec MAE<=3,p99<=24 |
| Reloaded native PLY |0 |0 |0 | PASS |
| Union of all six SPZ chunks vs whole SPZ |0 |0 |0 | PASS |
| Nearest3regions vs whole SPZ |35.1986 |76.1648 |69.96% | FAIL |
| Native gsplat LoD vs whole SPZ |3.63169 |7.98989 |14.781% | FAIL |
| Native csplat LoD vs whole SPZ |3.54889 |6.03552 |9.918% | FAIL |

For LoD the strict screen requires **each view** MAE<=5 and changed fraction<=10%.
The first public gsplat view passes (MAE3.16579,3.854% changed), but the broader
screen fails. Do not relabel the first-view pass as general quality acceptance.
Native LoD removes the large black omissions observed in nearest-region mode;
remaining detail changes are visible. Selection varies by view, so350k is a
budget target, not a mandatory count. The8-page count is not a total browser or
GPU memory measurement. First-ready timing is an app signal, not a measured
first-visible pixel; actual FPS/frame-time/long-network benchmarks are NOT RUN.
The final instrumented cache-disabled public run returned13.23MB initially,
21.40MB after jumping to the end,and29.57MB after returning. Evicted pages are
re-fetched; no retained decoded JS cache is used. On this small scene the round
trip transfers more than the15.92MB completeSPZ. Thus bounded precision residency
is demonstrated; bandwidth reduction or faster loading is **not established**.
The earlier7.40s and final9.64s first-ready observations are single network-bound
runs,not comparative performance guarantees.

Two suites rendered128actual fixed-camera images (64codec/union/reload,
64whole/three-region/two-native-encodings) on this Mac. Selected start/middle,
forward/backward and vertical screenshots were directly inspected. The public
report includes actual render comparison sheets and poor nadir/road regions.
Vehicles, trees, hood/nadir contamination, softness and ghosting remain.
Neither calibrated depth nor plausible GS constitutes independent geometry,
collision acceptance or unrestricted safe walking.

### Automated and public checks

- PASS TypeScript,lint,production build and207JS tests after paging metadata/package checks.
- PASS main Python environment:252run,247pass,5skip; PyCOLMAP environment:
  252run,220pass,32skip. These are two environment results, not504distinct tests.
- PASS local spatial/source suite4/4,then native LoD1/1. The initial Home-key
  assertion read a previous GPU frame; its failure/trace and corrected explicit
  progress wait are retained. No inference or training was re-run to repair it.
- PASS completed public suite5/5 (~1.2min):nativeLoD1,spatial2,source/lab2.
  Public sizes/SHA for33changed LoD-release files match the explicit package.
- PASS final public snapshot4/4:default LoD+report/lab3cases in40.8s;
  compact LoD1case in26.9s. Both actually render,move,reverse and switch control.
  All37changed public sizes/SHA match; fresh22-layer restore verifies1,235files.
  The default run has actual pending==0 before sampling and re-fetches evicted
  pages on reverse. Individual first-view screens pass,broader16views fail.
  [DEPLOYMENT.md](DEPLOYMENT.md) records immutable pointers/rollback archives.
- NOT RUN full legacy browser suite on the final public deployment,independent
  Paris geometry,km-scale training/serving,long-network/FPS benchmark.

Sanitized machine-readable evidence is in[evidence/paris-streaming.json](evidence/paris-streaming.json).
Raw model outputs,logs,PNG frames and failures stay locally reproducible.

## Conclusion and next boundary

A real58m Paris world now runs with bounded native LoD paging and an explicit
whole-scene control. Simple proximity chunk selection is insufficient; native
hierarchical coverage is the more useful serving path. It trades small detail
changes and larger offline storage for bounded precision residency. This is
**short-route feasibility**, not a completed2km world or lossless serving.

The next meaningful expansion is two overlapping reconstruction segments in one
image-derived coordinate frame, with actual overlap/boundary/return checks.
Then measure hundreds of meters under cold cache, constrained bandwidth and
frame-time recording. Do not paste separately scaled worlds using source GPS
alone. No further old-nine-panorama quality sweep is reopened.

## Reproduce

First reproduce the pinned24-source acquisition from[TOURIST_STREAMING.md](TOURIST_STREAMING.md).
Use a **new** job directory and preserve every failed attempt. The experiment
script currently pins the acquired Paris source location, not arbitrary cities.
Copy the tracked public provenance JSON to the new job, then:

```sh
mkdir JOB
cp scripts/samples/paris-seine-provenance.json JOB/provenance.json
data/tools/venv/bin/python scripts/prepare-panoramas.py \
  data/jobs/tourist-streaming-20261107/hd-initial/images JOB/sfm-inputs \
  --provenance JOB/provenance.json --size 512 --hfov 100
data/tools/colmap-venv/bin/python scripts/estimate-panorama-poses.py \
  JOB/sfm-inputs JOB/sfm --threads 4 --max-features 4096
data/tools/venv/bin/python scripts/paris-pipeline.py prepare JOB
data/tools/colmap-venv/bin/python scripts/paris-pipeline.py anchors JOB
```

Run the existing pinned model with the prepared list (no alternative model):

```sh
HF_HOME="$PWD/data/tools/depth-hf-cache" data/tools/diffusion-venv/bin/python - JOB <<'PY'
import json, subprocess, sys
from pathlib import Path
job = Path(sys.argv[1])
images = json.loads((job/'tangent-inputs/inference-inputs.json').read_text())
subprocess.run([sys.executable, 'scripts/infer-relative-depth.py', str(job/'depth'), *images], check=True)
PY
```

Then:

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

### Native LoD derivative and reproduction

Install Rust locally (the tested toolchain is under`data/tools/cargo` and
`data/tools/rustup`),clone the pinned official source into`data/tools/spark-2.4.0`,
then build using the installed CommandLineTools SDK:

```sh
RUSTUP_HOME="$PWD/data/tools/rustup" CARGO_HOME="$PWD/data/tools/cargo" \
 SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk \
 CC=/Library/Developer/CommandLineTools/usr/bin/clang \
 CXX=/Library/Developer/CommandLineTools/usr/bin/clang++ \
 CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/Library/Developer/CommandLineTools/usr/bin/clang \
 RUSTFLAGS='-C link-arg=-isysroot -C link-arg=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk' \
 data/tools/cargo/bin/cargo build --release --locked --no-default-features -j2 \
 --manifest-path data/tools/spark-2.4.0/rust/build-lod/Cargo.toml
```

Run `build-lod --help` from the actual built executable before conversion. Its
quality build defaults differ from older website examples. The tested command
uses the native PLY with explicit flags:

```sh
mkdir JOB/rad-build
cp JOB/view-world/scene.ply JOB/rad-build/scene.ply
# Run inside JOB/rad-build; executable path depends on your checkout location:
/path/to/spark-2.4.0/rust/target/release/build-lod \
 --quality --gsplat --max-sh=1 --rad-chunked scene.ply
```

The resulting root`scene-lod.rad` and16`scene-lod-N.radc` files become the
HTTP-served derivative:

```sh
data/tools/venv/bin/python scripts/prepare-paged-world.py \
 JOB JOB/rad-build JOB/lod-world --id paris-58m-lod --encoding gsplat
node scripts/compare-paged.mjs JOB JOB/paged-comparison
```

For the published compact control run the same build-lod command with
`--csplat` replacing`--gsplat` in a separate directory; prepare with
`--id paris-58m-lod-compact --encoding csplat`. Do not overwrite native outputs.
The comparison requires both derivatives. Local RAD folder selection is
explicitly unsupported; serve via HTTP (Vite preview) or open whole SPZ.
Publication commands and frozen archives are recorded in[DEPLOYMENT.md](DEPLOYMENT.md).
