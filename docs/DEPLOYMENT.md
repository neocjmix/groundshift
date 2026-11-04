# Railway viewer deployment

The user explicitly requested Railway hosting after local M0/M1 acceptance. Only the static viewer and selected licensed examples are hosted. Reconstruction, camera estimation, training, original input and job logs remain on the local Mac. The hosted viewer can still open a private world folder directly in the browser, without uploading it.

## Prepare a curated upload locally

```sh
npm ci
npm run sample
npm run package:viewer
```

To include the already reconstructed, licensed dozer result:

```sh
npm run package:viewer -- --include-reconstruction
```

That option requires `public/worlds/reconstructed/` from the local M1 run. The default package only includes Houseplant. `package:viewer` builds locally and prints a new staging directory under `data/deploy/viewer-<timestamp>/`. It copies only the HTML, hashed bundles, icon, runtime license notices, explicitly selected manifests/assets/camera metadata and dataset credits. It excludes source datasets, native tools, private footage and job logs. A SHA-256 inventory stays beside the staging directory, outside the upload.

The staging directory contains `Dockerfile`, `Caddyfile`, `railway.json`, `.dockerignore` and `www/`. Railway only packages these prebuilt files into the pinned official Caddy image. The server listens on Railway's `PORT` on all interfaces, serves `/healthz`, and leaves missing manifests and assets as real HTTP 404s. Railway terminates HTTPS. Hashed bundles use immutable caching; manifests and scene paths revalidate.

## Upload with an authenticated Railway CLI

Use an explicitly selected project/service and the exact staging path printed above:

```sh
railway up data/deploy/viewer-<timestamp> --path-as-root --no-gitignore \
  --project <project-id> --environment production --service <service-id>
railway domain --service <service-id>
```

`--no-gitignore` is only appropriate with this curated staging directory and `--path-as-root`. Do not apply it to the repository root: Git deliberately ignores reconstruction files, source captures and tools. Do not run the CLI from the repository without the explicit staging path.

This workflow does not connect GitHub auto-deployment: the checked-in repository excludes large trained scene assets, so a source-only deploy cannot reproduce the dozer without the local reconstruction step. A future deploy uses a fresh curated package and the same selected service.

Open `/` for Houseplant, and `/?world=/worlds/reconstructed/world.json` for the optional dozer. Use **Open world folder** for private local artifacts. Loading arbitrary localhost HTTP URLs from an HTTPS website is subject to browser mixed-content, CORS and local-network restrictions.

## Verification

Check deployment health, HTTP status and asset hashes, then open both scene URLs in a real WebGL2 browser and inspect screenshots. Confirm orbit, zoom and reset; a successful container start alone is not visual acceptance. Keep cloud results separate from the original local M2 benchmark.

Preparation on 2026-11-04: TypeScript, lint, 86 tests and production build PASS. Curated two-scene package: 17 listed files, approximately 25.16 MB (plus `.dockerignore`). Actual Railway deployment and public-browser checks remain **NOT RUN** until the target account is selected and authentication succeeds; both the environment token and saved local CLI login returned Unauthorized. The connected Railway tool exposes two account links and requires an explicit account selection when ambiguous.

Local native Caddy 2.11.7 configuration validation **PASS**. Serving the curated package on port 4320 passed health, manifest, license notice, byte-for-byte asset hash, cache and genuine 404 checks. Both worlds rendered in headed Chrome 156, screenshots were inspected, zoom/reset worked and no page exceptions were reported. Evidence is retained in `data/validation/deployment/`. This is local server validation, not a Railway container or public URL result. The native Caddy download was checked against upstream's SHA-512 checksum list.

Current upstream references: [Railway CLI upload/root/ignore behavior](https://docs.railway.com/cli/up), [Railway Caddy deployment](https://railway.com/guides/caddy), [config-as-code](https://docs.railway.com/config-as-code/reference), [Caddy file server](https://caddyserver.com/docs/caddyfile/directives/file_server). The Docker image is pinned to the verified available `2.11.7-alpine` manifest digest; Caddy's current release was 2.11.8 when checked, but that Docker tag was not yet available.
