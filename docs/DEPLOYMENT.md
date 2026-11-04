# Railway viewer deployment

**Live:** [Observation room](https://groundshift-viewer-production.up.railway.app/) · [My desk](https://groundshift-viewer-production.up.railway.app/?world=/worlds/desk/world.json) · [Estimated-camera dozer](https://groundshift-viewer-production.up.railway.app/?world=/worlds/independent/world.json) · [Supplied-camera dozer](https://groundshift-viewer-production.up.railway.app/?world=/worlds/reconstructed/world.json) · [Houseplant](https://groundshift-viewer-production.up.railway.app/?world=/worlds/sample/world.json)

The user explicitly designates Railway as an **observation surface**, not a production quality gate. Viewer changes, every distinct exported trial, and sanitized experiment evidence ship in the same workflow regardless of quality. Reconstruction, camera estimation and training remain local. Private original inputs, raw job logs and model weights stay on the Mac; explicitly licensed public comparison crops are included with attribution. The hosted viewer can open a private world folder directly in the browser, without uploading it.

## Observation release — 2026-11-05

The observation catalog contains **13 distinct scenes**: the previous four and
nine additional exports, including all four Mapillary Gaussian variants, early
dozer trials, the proof rerun, partial-pose failure and initial desk trial. The
unchanged dozer camera-path re-export is represented by its existing scene and
explicit duplicate lineage. The comparison report publishes 10 licensed source /
warp / mask / gray-control / diffusion images, 72 summarized stage records and
per-image attribution. Visual quality does not exclude a result.

| Item | Value |
| --- | --- |
| Viewer source | `0870435a1367327dfe45e78331a505adb9d9608d` |
| Release | [viewer-observations-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-observations-2026-11-05) |
| Archive | `groundshift-observations-20261105.tar.gz`, 147,359,576 bytes |
| SHA-256 | `8cbb3335f30127be05f81904e792ae2190d5483bf3c9a564b6d25358c38ebb20` |
| Static payload | 89 files, 159,297,244 bytes |
| Deployment | Pending public verification; see follow-up evidence below |

**Local PASS:** TypeScript, lint, 165 viewer/packager tests, production build,
22 headed Chrome tests in 1.9 minutes, and 102 distinct native-adapter tests
across their required environments. The OpenCV environment ran 102 with 19
missing-dependency skips; supplemental Pillow, PyCOLMAP and HDR-FFmpeg runs
executed every skipped test successfully (5 inpaint, 11 augmentation, 6 rig,
20 video tests, with overlap). This is 102 unique cases, not the sum of runs.
All 13 scene renders, desktop/mobile gallery, search/filter, report images,
sliders, history and return navigation were checked. The nine new canvas
previews were captured and visually inspected. No GPU training or inference
was repeated for publication; the measured existing binaries are unchanged.

The complete archive was read back locally: all 89 members exactly match their
public file inventory. Every new Gaussian PLY matches the existing local job
SHA-256, and coordinates/navigation are unchanged. The report is rebuilt from
explicit selected fields and an image allowlist; raw job logs, private footage,
private frames, model weights and local paths are not included.

See [observation workflow](OBSERVATIONS.md) and [the comparison report](https://groundshift-viewer-production.up.railway.app/experiments/mapillary/index.html).
The four-world release below remains a rollback package and historical evidence.

## Previous four-world catalog release — PASS, 2026-11-05

The catalog release collects four usable worlds: Houseplant, the original supplied-pose dozer, the independently estimated 120-view dozer, and the user's reconstructed desk. Local checks, the curated package, downloaded release checksum, Railway deployment, all 31 public file hashes, and actual public rendering of all four scenes are **PASS**. The gallery and scene navigation were exercised on the public origin.

| Historical package | Verified value |
| --- | --- |
| Viewer source | `f78bd6b476cbd5369597ac42f77fee8264957c4e` |
| Deployment-pointer commit | `c2516d6bb8867e3b7151acb8223feb73ae4d2706` |
| Railway deployment | `638cd8cb-9a99-45bf-95dd-0d2700e33fa9` — SUCCESS |
| Deployment timing | Created 2026-11-04 15:52:43 UTC; succeeded 15:53:14 UTC (2026-11-05 KST) |
| Actual trigger | Explicit latest-branch connector trigger; GitHub push autodeploy was not observed |
| Release | [viewer-gallery-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-gallery-2026-11-05) |
| Archive | `groundshift-viewer-f78bd6b.tar.gz`, 31,014,851 bytes |
| Archive SHA-256 | `75d14a661283a9c5ca24e48de9b491d5d06cb7c3171a2dfd36dd4d5cffd012ff` |
| Static payload | 31 files, 35,174,566 bytes |

| Public check | Result | Observed evidence |
| --- | --- | --- |
| Build, service and integrity | PASS | Archive checksum verified in build logs; healthcheck passes; `/healthz` returns 200/`ok`; all 31 public file bytes and hashes match |
| Missing/private paths | PASS | Four tested paths return actual 404s |
| Four-scene gallery and rendering | PASS | All previews and all four actual scenes visually inspected; each selected scene reaches ready with one canvas |
| Desk playback and scene switching | PASS | Path advances to progress 16.316 with changed camera position/orientation; pause works; sidebar switches all four scenes |
| Return, category and search | PASS | Back to scenes leaves zero canvases; reconstruction category returns two cards; desk search returns one; clearing returns four |
| Captured console | PASS | No warnings or errors in the captured public-browser console |
| GitHub push-triggered autodeploy | NOT VERIFIED | No new deployment observed after the push; explicit connector trigger completed this release |

The public viewer showed a rolling 60 fps label for each scene on this M2 Mac. Those are observations with uncontrolled cache/session conditions, not a controlled benchmark. Public evidence is retained in `data/validation/deployment/railway-gallery-{http,browser}.json`, with inspected screenshots `railway-gallery.jpg` and `railway-gallery-{desk,independent,reconstructed,sample}.jpg`. These are public-origin captures; original private video frames were not copied into the repository. Final Railway status had no pending work or staged changes.


Local verification passed TypeScript, lint, **143 viewer/packager tests**, **47 Python tests** including real HDR pixel checks, the production build, and **11 headed Chrome tests in 48.9 seconds**. Desktop/mobile layouts and all selected previews were visually inspected. Home loads 321,212 uncompressed JavaScript bytes and makes no WebGL context or PLY request; viewer, camera-path and world-loading chunks load only after a scene is selected. These are local execution observations, not a claim about a fresh public client or hosted performance. This release reuses the previously verified native exports; it does not imply a new reconstruction run.

| Selected world | What it demonstrates | Quality / evidence boundary |
| --- | --- | --- |
| Houseplant | Licensed upstream Gaussian scene; M0 viewer | Viewer sample, not a Groundshift reconstruction |
| Dozer · supplied cameras | 40 photos plus supplied measured poses/sparse initialization; local Metal training | Recognizable early reconstruction; soft surroundings |
| Dozer · estimated cameras | 120 raw photos, supplied lens calibration only; locally recovered poses/points and Metal training | Separate independently estimated pose result; supplied lens calibration is explicit |
| My desk | 99 locally estimated views from one user recording, estimated intrinsics and new Metal training | Recognizable desk/computers; peripheral smearing, thin-object streaks and blurred screen text remain |

The earlier four-world release excluded the smaller 24-view dozer and initial 15-second desk trials. The observation release now includes them as experiments, retaining their measured limitations. A second independent original recording and an actual walking-route capture remain **NOT RUN**.

### Desk publication permission

The creator has explicitly authorized **public display of the derived desk worlds and their rendered viewer previews**, including earlier trials under the later instruction to publish every experiment in Groundshift. **All rights reserved; no open redistribution license is granted.** This permission covers the selected Gaussian scene, necessary camera/world metadata, provenance and preview. It does not publish or license the original MOV, extracted frames, private iCloud URL, location/probe metadata, absolute local paths or reconstruction logs. The public artifact cites this permission statement; no private source link or access token is exposed. [Local reconstruction evidence and limits](ORIGINAL_VIDEO.md).

## Earlier revisit deployed revision

| Item | Value |
| --- | --- |
| Project | Groundshift — `db649cd6-49db-4750-b86d-c3c4d14b213d` |
| Environment | production — `43346592-217f-414e-b2ad-334e09b37599` |
| Service | groundshift-viewer — `2c6ac4d5-37bb-4ea8-aee0-1e75a1abdf69` |
| Deployment | `40916425-e59e-4d5c-b6f8-38fd90bc2750` — SUCCESS, 2026-11-04 13:37 UTC |
| Pinned deployment source | `16f943b6a5c6ed4242a63589208ed9de81aa8d66` on `feat/local-viewer-reconstruction` |
| Locally built viewer source | `b06d583535599ca911b8efb601069c7775a1ca73` |
| Public package | [viewer-revisit-2026-11-04 prerelease](https://github.com/neocjmix/groundshift/releases/tag/viewer-revisit-2026-11-04) |
| Archive | `groundshift-viewer-b06d583.tar.gz`, 28,259,801 bytes, 18 static files |
| Archive SHA-256 | `2e26d090d378540530677083de5167ba484c7551fee2f9b94ee7380fa85d2025` |

`deploy/Dockerfile.github` downloads the locally built archive, checks its SHA-256, and copies only `www/` into the pinned official Caddy image. Runtime notices, world provenance, camera metadata and dataset licenses are included. Large assets are release attachments, not Git commits. Root `.dockerignore` excludes everything except the deployment files.

This earlier deployment was pinned to the listed commit. The connector accepted a new source request for `feat/local-viewer-reconstruction` without a commit pin (`commitSha: null`), and watch patterns `/deploy/**` and `/.dockerignore` are confirmed by settings readback. However, service configuration only returned the source repository, and no new deployment appeared for more than 90 seconds after the release-pointer push. **Push-triggered autodeploy is NOT VERIFIED.** The agent therefore explicitly triggered the latest branch revision through the connector; deployment `638cd8cb-9a99-45bf-95dd-0d2700e33fa9` succeeded and its full static inventory matches publicly. No cause for the missing push trigger has been established. Source or documentation edits alone do not replace the archive consumed by `deploy/Dockerfile.github`; every viewer/scene release must update that archive URL and checksum. Retain each previous archive and deployment pointer for rollback.

The previous [viewer-2026-11-04 release](https://github.com/neocjmix/groundshift/releases/tag/viewer-2026-11-04)
and source `81adf61858673dedf9367196f4430ba8c5f24b16` remain available for rollback.
Its deployment was `00a9186e-8ae1-48b4-8371-a30072c65015`; archive
`groundshift-viewer-8c806e7.tar.gz`, SHA-256
`33b5e2c1ac2f4176cafc0593e43bd1d525dab8e0550f9a10046f2c8ee3e3dbf9`.

## Earlier revisit release verification

The earlier revisit release added camera-path navigation and the separately identified
[120-photo independent reconstruction](INDEPENDENT_RECONSTRUCTION.md). The
original Dozer PLY is unchanged; only its camera sequence metadata was added.
All 40 original camera matrices are unchanged. The smaller 24-view pipeline
experiment was not selected for publication because of its poor visual quality.

**PASS:** Railway build checksum, container health, all 18 public file hashes,
real 404s for missing/private paths, actual rendering of all three scenes, and
the new scene's play/pause, keyboard view selection and free look. Free look
changed camera rotation while preserving position. Actual public rendering is
shown in the [inspected screenshot](evidence/railway-independent-120.jpg).

The new scene displayed 75,397 Gaussians, 6.94 MB, 2.53 s load/decode and a
60 fps rolling label in the in-app Chromium browser on M2 Metal. This is one
observation with no native training active, not a controlled cold-cache or
GPU-only benchmark. The public file's SHA-256 matches the local native export:
`67f64ebeea5fc8cdae8ea65f01e0f4d060291d120bb5656311cad6bdd0b67229`.
Raw evidence: `data/validation/deployment/railway-revisit-{http,browser,logs}.json`.

Preparation passed TypeScript, lint, 118 viewer unit tests, 41 Python tests,
production build and four headed Chrome tests. Native image pipeline and
Metal training have separate execution reports; original walking-video
acceptance is still NOT RUN.

## Standing release workflow

Complete this sequence for viewer changes and all experiment outcomes already authorized for observation. Routine approval is not needed again; preserve explicit privacy and licensing limits.

1. Finish the change and run relevant TypeScript, lint, automated, production-build and browser checks. Verify actual rendering for exported scenes. Inspect and report quality separately; FAIL quality is published rather than filtered out.
2. Inventory all exported worlds and experimental outcomes. Publish each distinct scene with public metadata and an actual render preview. Record failed/cancelled/unexecuted stages and duplicate-export lineage in the report. Keep downloaded samples, measured/supplied-pose reconstructions, original video and generated-input trials distinct.
3. Build the curated static package locally using the explicit inclusion flags below. Inspect its complete inventory for private source paths, URLs, footage, frames and raw logs. Only explicitly allowlisted licensed public crops/comparisons belong in the report. Do not upload the repository or raw `dist/` directory.
4. Archive only `www/`, record its SHA-256, publish it under a fresh GitHub release tag, then download it and compare the hash. Keep the prior archive available.
5. Update the release URL/checksum in `deploy/Dockerfile.github`, commit the reviewable deployment pointer, and push it to the connected branch as part of the same workflow. A source-code push without this step leaves the old package live.
6. Observe Railway's deployment history, revision and healthcheck. A source-connection response is insufficient evidence of push-triggered deployment. If the expected new deployment does not appear, explicitly trigger the latest intended branch revision through the connector, continue validation, and record which trigger actually worked. The standing instruction already authorizes this routine fallback.
7. Compare every public file against the curated inventory. Verify missing/private paths return 404. Open the public viewer, visually inspect all included worlds, and exercise changed navigation/catalog behavior.
8. Record the release tag, source/deployment revisions, archive hash, Railway deployment ID and public-browser evidence here. Report any failed or unexecuted gate accurately; completion requires a verified live result.

### Branch request and explicit deployment fallback

The requested source is `feat/local-viewer-reconstruction` without a commit pin, with watch paths `/deploy/**` and `/.dockerignore`. Keep repository root as the build context and `deploy/Dockerfile.github` as the Dockerfile path. Native reconstruction and the production web build stay local; Railway downloads the already validated static archive and runs Caddy.

Railway documents branch autodeploy and watch patterns, but this service did not visibly deploy the release-pointer push during observation. The connector accepted the branch request and returned `commitSha: null`; later settings readback confirmed the watch patterns but only exposed `source.repo`. That does not prove a functioning GitHub push trigger. Its cause is not diagnosed. See [GitHub autodeploys](https://docs.railway.com/deployments/github-autodeploys) and [watch paths](https://docs.railway.com/deployments/monorepo#watch-paths).

The working release procedure must observe a new deployment and use an explicit latest-revision connector trigger when needed. Record that fallback rather than calling webhook autodeploy successful. The standing user instruction is to finish verified deployment in the same workflow; it does not depend on this unverified automatic trigger. Ordinary source/docs work must still produce a fresh archive and update the deployment pointer before any release is complete.

## Restore scene assets in a fresh checkout

The catalog and preparation recipe are tracked; generated scenes and comparison
images are ignored. `npm run sample` supplies only Houseplant's Gaussian asset.
For the complete observation surface, restore this immutable release in a
**fresh checkout**. The commands verify the archive before copying the 13 named
world folders and the public comparison report. Existing files in these paths
would be replaced; keep any personal variants elsewhere.

```sh
(
  set -e
  gs_release_dir=$(mktemp -d)
  gs_archive=groundshift-observations-20261105.tar.gz
  curl --fail --location --output "$gs_release_dir/$gs_archive" \
    "https://github.com/neocjmix/groundshift/releases/download/viewer-observations-2026-11-05/$gs_archive"
  printf '%s  %s\n' \
    '8cbb3335f30127be05f81904e792ae2190d5483bf3c9a564b6d25358c38ebb20' \
    "$gs_release_dir/$gs_archive" | shasum -a 256 -c -
  tar -xzf "$gs_release_dir/$gs_archive" -C "$gs_release_dir"
  for gs_world in sample reconstructed independent desk beijing-10k beijing-generated beijing-20k beijing-2k dozer-smoke dozer-proof dozer-partial dozer-24 desk-15s; do
    mkdir -p "public/worlds/$gs_world"
    cp -R "$gs_release_dir/www/worlds/$gs_world/." "public/worlds/$gs_world/"
  done
  mkdir -p public/experiments/mapillary
  cp -R "$gs_release_dir/www/experiments/mapillary/." public/experiments/mapillary/
  cp "$gs_release_dir/www/worlds/catalog.json" public/worlds/catalog.json
)
npm ci
npm run dev
```

The extraction/copy procedure was executed in an isolated fresh directory: all
13 worlds and the report restored with 80 files / 155,723,181 bytes matching
the release inventory. Evidence: `data/validation/deployment/observation-fresh-restore.json`.

This restores display assets only. It neither downloads the private original
video nor repeats reconstruction. Desk creator-authorized display terms remain
separate from the open sample licenses. The earlier four-world archive remains
available in its historical release entry above.

## Prepare a curated package locally

After restoring the assets above, or generating and checking the same selected public artifacts locally, build the full observation release:

```sh
npm run package:viewer -- --include-reconstruction --include-independent --include-desk --include-experiments
```

The first three flags select the existing worlds; `--include-experiments` includes every world and report file explicitly listed in `scripts/observation-worlds.json`. See `python3 scripts/prepare-observations.py --render-previews` for regeneration from local jobs. The default `npm run package:viewer` includes only Houseplant and still requires its `preview.jpg`. The catalog is filtered to included scenes, so a smaller curated package does not advertise missing worlds or an absent report.

The command builds locally and prints a fresh staging directory under `data/deploy/viewer-<timestamp>/`. It copies only HTML, hashed bundles, icon, runtime notices, the selected catalog, scene assets, previews, manifests, camera metadata and credits. It checks ordinary files/directories and public provenance, rejects symlink escapes and common private references, and preflights inputs before creating output. This is a practical publication boundary, not a substitute for inspecting scene content. Source datasets, native tools, private footage and job logs are excluded. A SHA-256 inventory stays beside the staging directory, outside any upload.

The staging directory contains `Dockerfile`, `Caddyfile`, `.dockerignore` and `www/`. To prepare the release attachment, substitute the exact printed path and a fresh archive name:

```sh
COPYFILE_DISABLE=1 tar -czf data/deploy/groundshift-viewer-<revision>.tar.gz \
  -C data/deploy/viewer-<timestamp> www
shasum -a 256 data/deploy/groundshift-viewer-<revision>.tar.gz
```

Compare the archive contents against the staging inventory before publishing. The current release includes `SHA256SUMS` and `viewer-files.json` as independently readable checksums. Re-download the published archive and verify the checksum before connecting Railway.

## Railway configuration

The Railway connector created the project/service, configured it, and attached `neocjmix/groundshift` at the pinned commit. The local Railway CLI token and saved login were expired; this did not block the connector. GitHub CLI authentication was valid, so a GitHub release supplied the curated files without requiring another login.

Apply these settings through the Railway connector or service settings:

- Dockerfile path: `deploy/Dockerfile.github`; repository root as build context.
- Healthcheck: `/healthz`, timeout 60 seconds.
- Restart: `ON_FAILURE`, maximum 3 retries.
- Public domain target: port 8080. Caddy listens on Railway's `PORT` (default 8080), on all interfaces.
- No custom start/build command, volume, database, bucket, secret or GPU service is required.

Railway rejected configuring a `railway.json` path for this new service. Its current [Infrastructure as Code documentation](https://docs.railway.com/infrastructure-as-code) says Config as Code is deprecated, unavailable to new services, and stops being read for legacy services on 2026-12-01. The unused JSON configuration was removed; this one service uses direct settings without adding an IaC dependency.

Railway terminates HTTPS. Missing manifests/assets return genuine HTTP 404s. Hashed bundles use immutable caching; HTML, manifests and scene paths revalidate. Use **Open world folder** for private local artifacts. Loading arbitrary localhost HTTP URLs from an HTTPS website is subject to browser mixed-content, CORS and local-network restrictions.

### Alternative: authenticated CLI upload

This path is available for a future session with valid CLI authentication. Set the service's Dockerfile path to `Dockerfile` before uploading the curated directory, keeping the healthcheck/restart/domain settings above:

```sh
railway up data/deploy/viewer-<timestamp> --path-as-root --no-gitignore \
  --project db649cd6-49db-4750-b86d-c3c4d14b213d \
  --environment production --service 2c6ac4d5-37bb-4ea8-aee0-1e75a1abdf69
```

`--no-gitignore` is only appropriate with the curated staging directory and `--path-as-root`. Never apply it to the repository root. The current deployment used the connector/GitHub route, not this CLI upload.

## Initial public verification — 2026-11-04

| Check | Result | Evidence |
| --- | --- | --- |
| Railway container build/start/health | PASS | Build log verifies archive checksum, starts Caddy and passes `/healthz`; deployment SUCCESS |
| HTTPS and static file integrity | PASS | All 14 decoded public files match the local SHA-256 inventory; root and health return 200 |
| Licenses, manifests, cache headers | PASS | JSON parses; credits/notices reachable; immutable hashed bundles and no-cache world/HTML responses |
| Missing/private paths | PASS | Missing JSON/PLY, `/.env`, `/data/jobs/dozer-1500/job.json` return 404 |
| Houseplant actual rendering | PASS | Leaves and pot visible in [public-origin screenshot](evidence/railway-houseplant.jpg) |
| Local dozer actual rendering | PASS | Excavator, road and cones visible in [public-origin screenshot](evidence/railway-dozer.jpg); direct deep link also verified |
| Orbit, zoom, reset, scene replacement | PASS | Actual camera-position changes and return to initial coordinates; one canvas after replacement |
| Browser errors | PASS | No errors in captured browser console |
| Railway CLI upload | NOT RUN | Invalid local authentication; deployment used the connected Railway plugin |
| Other devices and load/stress testing | NOT RUN | No cross-device or capacity claim |

Public-browser checks used the Codex in-app Chromium browser on this M2 Mac, 1280 × 720 CSS viewport. Runtime reported `ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)`. Observed rolling frame-rate labels were 60 fps for both scenes. Load + decode displayed 2.54 seconds for Houseplant and 5.14 seconds for dozer; these are single observations, not controlled cold-cache benchmarks. Browser/edge caches were not forcibly cleared, and dozer loaded after Houseplant. These measurements are separate from the original localhost Chrome results.

Raw HTTP hashes, browser details/camera positions and Railway build/runtime logs are retained locally in `data/validation/deployment/railway-{http,browser,logs}.json`. Earlier local Caddy validation remains in `local.json`. TypeScript, lint, 86 unit tests and the production build passed during package preparation; the subsequent packaging-only adjustment passed syntax and inventory checks, with unchanged `www/` hashes.

Current references: [Railway CLI root/ignore behavior](https://docs.railway.com/cli/up), [Railway Caddy deployment](https://railway.com/guides/caddy), [IaC and Config as Code deprecation](https://docs.railway.com/infrastructure-as-code), [Caddy file server](https://caddyserver.com/docs/caddyfile/directives/file_server). The Docker image is pinned to the verified available `2.11.7-alpine` manifest digest; Caddy's current release was 2.11.8 when checked, but that Docker tag was not yet available.
