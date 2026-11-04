# Railway viewer deployment

**Last verified public release:** [Independent 120-view reconstruction](https://groundshift-viewer-production.up.railway.app/?world=/worlds/independent/world.json) · [Original supplied-pose dozer](https://groundshift-viewer-production.up.railway.app/?world=/worlds/reconstructed/world.json) · [Houseplant](https://groundshift-viewer-production.up.railway.app/)

The user explicitly requested Railway hosting after local M0/M1 acceptance and now instructs that verified viewer changes and authorized usable scenes ship in the same workflow. Only the static viewer and selected scene artifacts are hosted. Reconstruction, camera estimation, training, original inputs and job logs remain on the local Mac. The hosted viewer can open a private world folder directly in the browser, without uploading it.

## Current catalog release — PENDING

The next release collects four usable worlds: Houseplant, the original supplied-pose dozer, the independently estimated 120-view dozer, and the user's reconstructed desk. The desk's local reconstruction and browser controls passed; its public package, updated catalog and Railway release are still **PENDING** until separately verified. The last confirmed deployment is recorded below. A release upload or a local screenshot is not public-deployment acceptance.

| Selected world | What it demonstrates | Quality / evidence boundary |
| --- | --- | --- |
| Houseplant | Licensed upstream Gaussian scene; M0 viewer | Viewer sample, not a Groundshift reconstruction |
| Dozer · supplied cameras | 40 photos plus supplied measured poses/sparse initialization; local Metal training | Recognizable early reconstruction; soft surroundings |
| Dozer · estimated cameras | 120 raw photos, supplied lens calibration only; locally recovered poses/points and Metal training | Separate independently estimated pose result; supplied lens calibration is explicit |
| My desk | 99 locally estimated views from one user recording, estimated intrinsics and new Metal training | Recognizable desk/computers; peripheral smearing, thin-object streaks and blurred screen text remain |

The smaller 24-view dozer and initial 15-second desk trials are preserved locally and excluded from this catalog. They are superseded experiments, not additional accepted scenes. A second independent original recording and an actual walking-route capture remain **NOT RUN**.

### Desk publication permission

The creator has explicitly authorized **public display of the derived desk world and its selected viewer preview** in Groundshift. **All rights reserved; no open redistribution license is granted.** This permission covers the selected Gaussian scene, necessary camera/world metadata, provenance and preview. It does not publish or license the original MOV, extracted frames, private iCloud URL, location/probe metadata, absolute local paths or reconstruction logs. The public artifact cites this permission statement; no private source link or access token is exposed. [Local reconstruction evidence and limits](ORIGINAL_VIDEO.md).

## Last verified deployed revision

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

This earlier deployment was pinned to the listed commit. The existing service has now been connected to `feat/local-viewer-reconstruction` without a commit pin (`commitSha: null`), with watch paths `/deploy/**` and `/.dockerignore`. The connector accepted and returned these settings. Reconnecting initially builds the previous archive; it does not publish the new catalog. Observing the new release-pointer push trigger and complete its deployment remains **PENDING**. Source or documentation edits alone do not replace the archive consumed by `deploy/Dockerfile.github`; every viewer/scene release must update that archive URL and checksum. Retain each previous archive and deployment pointer for rollback.

The previous [viewer-2026-11-04 release](https://github.com/neocjmix/groundshift/releases/tag/viewer-2026-11-04)
and source `81adf61858673dedf9367196f4430ba8c5f24b16` remain available for rollback.
Its deployment was `00a9186e-8ae1-48b4-8371-a30072c65015`; archive
`groundshift-viewer-8c806e7.tar.gz`, SHA-256
`33b5e2c1ac2f4176cafc0593e43bd1d525dab8e0550f9a10046f2c8ee3e3dbf9`.

## Earlier revisit release verification

The new release adds camera-path navigation and the separately identified
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

Complete this sequence for verified viewer changes and selected scenes already authorized for publication. Routine approval is not needed again; preserve explicit privacy and licensing limits.

1. Finish the change and run the relevant TypeScript, lint, automated, production-build and browser checks. New reconstructed scenes require actual local rendering/quality inspection in addition to native execution evidence.
2. Select the usable worlds and their public metadata/previews. Keep scene provenance honest: downloaded sample, supplied-pose reconstruction, estimated-pose reconstruction, and original-video reconstruction are different evidence categories.
3. Build the curated static package locally using the explicit inclusion flags below. Inspect its complete inventory for private source paths, URLs, footage, frames and logs. Do not upload the repository or raw `dist/` directory.
4. Archive only `www/`, record its SHA-256, publish it under a fresh GitHub release tag, then download it and compare the hash. Keep the prior archive available.
5. Update the release URL/checksum in `deploy/Dockerfile.github`, commit the reviewable deployment pointer, and push it to the connected branch as part of the same workflow. A source-code push without this step leaves the old package live.
6. Observe Railway's deployment result and healthcheck. Read back the connected branch, watch patterns and deployed commit instead of assuming a push triggered the right deployment.
7. Compare every public file against the curated inventory. Verify missing/private paths return 404. Open the public viewer, visually inspect all four selected worlds, and exercise changed navigation/catalog behavior.
8. Record the release tag, source/deployment revisions, archive hash, Railway deployment ID and public-browser evidence here. Report any failed or unexecuted gate accurately; completion requires a verified live result.

### Branch-following configuration

The configured source is the existing service connected to `feat/local-viewer-reconstruction` without a commit pin, with autodeploy enabled and watch paths `/deploy/**` and `/.dockerignore`. Keep repository root as the build context and `deploy/Dockerfile.github` as the Dockerfile path. Native reconstruction and the production web build stay local; Railway downloads the already validated static archive and runs Caddy.

Railway deploys pushes to its connected branch, while watch patterns limit which changed paths trigger it. This keeps ordinary source/docs work from redeploying an unchanged package. The release-pointer commit under `deploy/` is the deliberate trigger; it must follow local verification and archive publication. See [GitHub autodeploys](https://docs.railway.com/deployments/github-autodeploys) and [watch paths](https://docs.railway.com/deployments/monorepo#watch-paths). The branch/watch changes were accepted and returned by the Railway connector. A new release-pointer push and its successful public deployment remain **PENDING** for this transition; configuration acceptance alone does not prove that trigger.

## Prepare a curated package locally

```sh
npm ci
npm run sample
npm run package:viewer
```

To include the already reconstructed, licensed dozer result:

```sh
npm run package:viewer -- --include-reconstruction
```

To include the separately verified independent sample as well:

```sh
npm run package:viewer -- --include-reconstruction --include-independent
```

`--include-independent` requires the measured world copied into
`public/worlds/independent/`. Both generated scene directories are ignored by
Git. This flag selects that one explicit licensed artifact, not arbitrary
folders under `public/worlds/`.

The option requires `public/worlds/reconstructed/` from the local M1 run. The default includes only Houseplant. The command builds locally and prints a fresh staging directory under `data/deploy/viewer-<timestamp>/`. It copies only HTML, hashed bundles, icon, runtime notices, explicitly selected manifests/assets/camera metadata and dataset credits. It excludes source datasets, native tools, private footage and job logs. A SHA-256 inventory stays beside the staging directory, outside any upload.

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
