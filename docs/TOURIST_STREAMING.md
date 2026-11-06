# A longer tourist route for serving — 2026-11-07

[Source scouting and GPS route](https://groundshift-viewer-production.up.railway.app/experiments/tourist-streaming/)
· [876 selected source records](https://groundshift-viewer-production.up.railway.app/experiments/tourist-streaming/route.json)
· [24-image acquisition evidence](https://groundshift-viewer-production.up.railway.app/experiments/tourist-streaming/acquisition.json).

**Select Paris: the south bank near Notre-Dame and connected streets.**
One real capture sequence supplies876 consecutive360° photographs over
approximately2.185km of GPS polyline, with median2.530m/max3.227m spacing.
Source sensor raster is12,288×6,144. A first contiguous24-image window is
actually downloaded and verified locally; new Gaussian reconstruction and
Gaussian streaming are **NOT RUN**. The public page is source evidence,
not a substitute for an actual long GS world.

The user accepts the preceding [SPZ result](COMPRESSION.md): visual degradation
is hard to distinguish in their observation. Keep that verified codec as the
delivery baseline and move to longer-distance serving. This does not claim SPZ
is the smallest possible format; additional lossy compression research is
deferred. Previous same-data quality training remains closed. No prior native
world, reconstruction, camera solution or rejected-background policy changes.

## What was actually investigated

Panoramax provides public STAC metadata, source ordering, public high-resolution
assets and item-specific license links. It avoids the own-Mapillary-token blocker
from the earlier acquisition, while keeping computation and reconstruction on
this Mac. No new service/account, hosted reconstruction, paid API or database
is introduced. [Official API documentation](https://docs.panoramax.fr/backend/api/api/)
and actual OpenAPI schemas were inspected before using endpoints/filters.

Queries use the federated `https://api.panoramax.xyz/api/search`, bbox,
`filter=field_of_view = 360`, collection IDs and URL-encoded`sortby=+ts`.
First Paris/Strasbourg queries each hit the1000-result cap; these are **not**
global counts. Collection-filtered follow-ups recover the relevant ordered
runs. A4000-result Paris query also caps; its partial coverage is not passed
off as complete. The selected876-record run has all875 provider `prev` links
confirming its adjacency, without nearest-neighbor invented ordering.

| Candidate | Actual source evidence | Decision |
| --- | --- | --- |
| Paris south bank/connected streets |876consecutive records,2.185km GPS length;2.530m median,3.227m max;12,288×6,144 | Selected: famous surroundings, dense same-day capture, bounded initial route |
| Strasbourg old town/Petite France |2024sequence1574consecutive records,6.779km GPS length;4.95m median;12,288×6,144.2025partial run2994records/10.272km,3.93m median | Strong reserve: picturesque real previews, longer route including loops/retracing |
| Mont-Saint-Michel / Annecy |0results in the explicitly queried360° bounding boxes | Excluded from this bounded search; no worldwide absence claim |

Selected Paris collection:
`9fe7f3ab-14e3-4174-8731-b06e31d9577b`, source ranks808–1683 inclusive.
Photographer attribution: **Immergis pour la Ville de Paris / Panoramax IGN**.
Capture2025-05-08T04:59:44.711Z–05:07:25.391Z. This is vehicle capture,
not walking footage. Actual SD previews show the riverbank and connected
streets, building facades, trees, pedestrians, cyclists and vehicle roof/nadir.
It is not2.185km of straight waterfront or an unobstructed cathedral survey.

The public page retains each picture's ID, sequence rank, capture/update times,
GPS, azimuth, declared accuracy, dimensions, upstream asset and metadata URLs.
The GPS accuracy field says2m; spacing is computed from those **source estimates**.
Tiny stationary steps exist (minimum0.017m), so876 records must not be called
876 independently measured, well-separated camera centers. The entire source
collection is larger; only the bounded subset is selected.

## Licensing and publication boundary

Each selected Paris item declares **etalab-2.0**, with compatible provider
metadata and source license link. The [official Open Licence2.0 text](https://github.com/etalab/licence-ouverte/blob/master/open-licence.md)
permits reproduction, transformation and redistribution with source attribution
and update-date information. Capture dates, catalog access2026-11-07 and item
update dates are recorded. This does not imply official endorsement.
The Strasbourg comparison uses the same declared license and credits
Eurométropole de Strasbourg separately. No source is silently relicensed.

Selected publicly licensed2048px SD previews and necessary route/acquisition
metadata are explicitly packaged. The24 highest-public-resolution JPEGs stay
local, unchanged from the public provider. Those provider assets are already
privacy-processed; they are not unblurred camera originals. Source-provider
hosting is read-only acquisition, not new Groundshift infrastructure.
No private footage, local paths, raw logs, model weights or HD source binaries
are published or committed.

## Actual execution and validation

| Check | Result |
| --- | --- |
|876ranks, unique IDs,875provider adjacency links, license/ERP, source times | PASS |
| Metadata preparation reproduced from saved API snapshot | PASS, byte-identical to initial selected manifest |
| Actual local HD acquisition | PASS24/24, ranks988–1011,202,545,787bytes,249.668572s |
| HD shape and integrity | All24JPEG format/header/resolution checks and SHA-256 records; all12,288×6,144 |
| Full pixel decoding | PASS3selected HD images (ranks988/1000/1011),0.8255s; full decode of all24 NOT RUN |
| Initial window GPS length |58.0227m; not a reconstructed metric baseline |
| Automated source boundary tests | PASS9Python tests |
| Viewer JS tests/typecheck/lint/build | PASS188JS tests plus TypeScript/ESLint and actual production build |
| Local source report/browser | PASS2/2in5.4s |
| Initial public source report/browser | PASS2/2in10.9s |
| Final acquisition report/browser | PASS local2/2in4.0s, public2/2in9.5s;24HD hash pins, real previews, route and HD binary exclusion checked |
| Railway publication and public integrity | PASS two incremental deployments;13 then6 changed public file size/SHA checks; fresh15-layer restore1157files |
| New local SfM, depth, GS export and lazy GS serving | NOT RUN |

Nine synthetic tests reject missing/duplicate ranks, mismatched provider links,
duplicate IDs, non-open license and non-ERP substitution. They also check UTC
ordering across offsets, longitude/latitude axes, dateline distances, stationary
capture handling and preserved failure reports. These tests are **not** an SfM
or GPU test. Actual browser checks decode real source JPEG previews, verify the
876-point GPS line, change photo selection, inspect mobile overflow and follow
the lab link. No Gaussian request or canvas is created on the source page.
The final public screenshot was also visually inspected. A first local
acquisition-page test **FAIL** expected HTTP404 for an unpublished HD path;
Vite preview returns its SPA HTML with200. The corrected check rejects image
MIME/JPEG bytes and expects that local fallback while retaining the deployed
server's404 assertion. Both final runs pass; the initial failure is retained
with its trace. This is not a claim that a raw HD image was published.

[Committed evidence summary](evidence/tourist-source.json) retains measured
source/acquisition values, final browser observations, public metadata hashes
and the two actual deployment IDs without publishing raw logs or HD binaries.

An initial probe of a guessed `api.panoramax.ign.fr` hostname fails DNS. Current
official docs identify `panoramax.ign.fr`; discovery continues through the
documented working federated API and original-instance links. There is no
authentication bypass or use of another person's API token. No failed
reconstruction is hidden: reconstruction has not started in this source run.

Raw discovery responses, acquisition report, image bytes, pixel checks and
browser evidence stay under `data/jobs/tourist-streaming-20261107/`.
The first report is published before HD acquisition/local/public validation
finishes. The next overlay adds acquisition measurements, known HD hashes and
completed source-page checks. [Deployment](DEPLOYMENT.md) records actual
statuses/public hashes separately from future streaming acceptance.

## Reproduce source acquisition

The selection is tracked in `scripts/samples/paris-seine.json`. Save a fresh
bounded official search response, then validate source ordering before fetching
images. Use a new output directory; existing evidence is never overwritten:

```sh
mkdir -p data/jobs/paris-source-reproduction
curl --fail --get 'https://api.panoramax.xyz/api/search' \
  --data-urlencode 'bbox=2.337,48.850,2.355,48.861' \
  --data-urlencode 'limit=4000' \
  --data-urlencode 'collections=9fe7f3ab-14e3-4174-8731-b06e31d9577b' \
  --data-urlencode 'filter=field_of_view = 360' \
  --data-urlencode 'sortby=+ts' \
  -o data/jobs/paris-source-reproduction/search.json
python3 scripts/prepare-tourist-route.py data/jobs/paris-source-reproduction/search.json \
  data/jobs/paris-source-reproduction/route.json
data/tools/venv/bin/python scripts/acquire-tourist-route.py \
  data/jobs/paris-source-reproduction/route.json data/jobs/paris-source-reproduction/hd \
  --first 180 --count 24
python3 -m unittest discover -s scripts/tests -p test_tourist_route.py -v
```

Pillow is available in the existing local tools environment; acquisition needs
no reconstruction engine or GPU. The downloader caps a window at64images and
each response at32MiB, never overwrites output, retains FAIL/partial evidence
and paces requests. It records observed hashes on first acquisition; a manifest
with known `hdSha256` also rejects changed bytes. The public selected manifest
includes known hashes for the24 acquired images. Remaining852HD files are not
claimed downloaded, pixel-verified or checksum-pinned. Upstream changes/removal
must fail explicitly instead of substituting another scene.

## Next bounded GS/serving experiment

1. **Establish a shared coordinate frame for the first60–100m.** Use actual
   perspective crops and fixed-rig SfM; GPS/azimuth are optional priors, not
   complete poses or collision geometry. Exclude car roof/black nadir and
   document sky/water/moving-object limits. Preserve public originals.
2. **Separate loader behavior from reconstruction differences.** First create
   one short real GS, preserve its whole-scene control, and partition its
   existing Gaussians spatially into SPZ chunks in that same frame. Give each
   Gaussian one ownership region so overlapping files do not double opacity.
   This is serving/packaging, not another quality sweep on the old nine images.
3. **Load a bounded neighborhood.** Start with the current chunk and adjacent
   chunks, prefetch in the movement direction, cancel obsolete downloads and
   dispose distant CPU/GPU resources. Bound download and decode concurrency.
   Handle reverse movement, repeated places, jumps, failed chunk loads and
   late completion after eviction. Static files on existing Railway suffice.
4. **Measure before expanding.** Verify full-scene versus chunked render
   equality with all chunks present, then actual transition coverage, first
   usable view, requested/transferred bytes, resident Gaussian count and frame
   times under movement. Do not infer GPU-memory use from compressed bytes.
   Only then extend to several hundred meters/1km using overlapping training
   blocks with common poses and explicitly checked boundary ownership.

Long-route alignment and unknown/unloaded geometry remain real uncertainties.
Photo lazy loading, source GPS continuity, compression success and a source
report's browser PASS cannot establish successful lazy Gaussian rendering.
