# Safari paging investigation — 2026-11-07

## Outcome

**The user now reports the persistent blur is resolved on their physical
iPhone16Pro Safari and the scene looks plausible.** This is **USER REPORTED**
resolution, not an instrumented physical-device PASS. No physical iPhone was
connected for agent inspection; that validation remains NOT RUN. Preserve the
initial unresolved report and all actual desktop/WebKit evidence below.
DesktopChrome mobile emulation alone was insufficient acceptance for the report.

The current14-page/800k-target viewer refines normally in the available Safari
and WebKit environments below. These results neither disprove the user report nor
establish physical-device acceptance. No new page budget, model, reconstruction,
compression, asset or source-image changes were made. A subsequent reproducible
WebKit decoder wait was repaired as described below; the physical compact
report subsequently receives user confirmation. Whether the isolated gsplat
worker failure was exactly the physical compact cause remains unproven.

## Reproduced decoder wait and deployed workaround

After the initial observations, a controlled delay exposed a real failure in
**gsplat**: allow the first coarse chunk, hold detail responses11s, then release
them. Network transfer and checksums finish, but one worker never returns chunk2.
After35s it remains at416,335points/13pages; after another camera movement it
remains coarse. Render frames continue. The user later supplied the exact
**compact/csplat** URL and a private screenshot with conspicuous Gaussian blur;
the same delayed compact run recovered normally. Do not equate these causes.

RPC-only observation narrowed the gsplat failure: chunk2's1,667,136bytes arrive,
worker reports `loaded=total`, then no result/error for35,029ms. A different
worker completes the remaining chunks. Stream-boundary logging itself removes
the failure, so the exact stalled instruction is not proven.

With only the buffered-input branch changed to direct `decoder.push(fileBytes)`
and `decoder.finish()`, the same chunk returns65,536Gaussians in25ms and the view
reaches680,013points/14pages with all queues idle. This25ms is one instrumented
RPC observation, not a device benchmark. Matching before/after PNGs show restored
nearby window/road detail. Original, instrumented and candidate runs remain in
`worker-rpc/`, `worker-boundary/`, `worker-stream/`, `worker-direct/`
under the ignored validation root. The private user screenshot is not published.

The application now applies this narrow workaround at Vite load time, without
editing node_modules or WASM. It pins the exact Spark2.4.0 ESM SHA-256 and known
worker branch, failing builds on upstream drift. It affects already-buffered
inputs (including RAD and SPZ), leaving actual URL/chunked streaming code
unchanged. The same hook applies in dev and production. Existing MIT attribution
is retained; Groundshift's modification is in `build/spark-buffered-decode.ts`.

**Uninstrumented production-build WebKit regression: PASS4/4** — gsplat2/2
in50.4s, compact2/2 in44.7s. These run the actual app without worker wrappers or
extra worker messages. They verify moved/rotated Fly pose and FOV preservation,
local diagnostic export, progressive refinement, delayed-response indication
and recovery. The formerly failing gsplat case recovers from52,788/1page to
680,013/14pages; compact recovers to687,069/14pages. All queues idle and no page
errors. Explicit network-delay/fullscreen-unavailable fixtures are labeled;
physical touch swipes and physical iPhone GPU acceptance remain NOT RUN.

## Initial reproduction attempts

Public source version before this change: `a0400878b074157319c50bb592415625b19f8bf0`.
All counts below are observed displayed/selected Gaussians, not a percentage of
geometric correctness or an assertion that all800k should always be visible.

| Environment | Actual observation | Reported stuck-blur reproduction |
| --- | --- | --- |
| macOS Safari26.6.2, native UI |685,467points,14pages,23.02MB,15requests; street visibly renders. Responsive402×681/3× and Fly enter/exit reached680,013points. | Not reproduced in these observations |
| Playwright desktopWebKit27.2, iPhone16Pro profile | CSS402×681, DPR3; app drawing buffer603×1021 because its existing DPR cap is1.5. 156,930points initially,680,013 by17.8s,14pages/pending0/15requests/23,021,880bytes through50s; frame count advances, no page errors. | Not reproduced |
| Same WebKit, end/mid/landscape | End501,856/13pages; mid650,286/14; landscape874×402595,016/14. Each observed15s, pending0, advancing frames, no page errors. | Not reproduced |
| Same WebKit, compactRAD |687,069points/14pages/22.76MB/15requests; pending0, advancing frames. | Not reproduced |
| Installed iOS26.3 Simulator, iPhone17Pro, Safari via native UI |672,170points/14pages/23.02MB/15requests, visible street. Fly enter/exit responsive; afterwards680,946points. | Not reproduced in initial view; not a physical iPhone16Pro |
| Physical iPhone16Pro Safari | **NOT RUN** instrumented — no connected device | Initially unresolved; later USER REPORTED resolved |

The initial WebKit snapshot and matched wholeSPZ snapshot use the same pose:
RGB mean absolute difference1.33242/255, central difference1.63456/255,
central edge contrast ratio0.98394. Both visibly retain reconstruction softness
and stretched surfaces. This only compares two serving paths of the same asset;
it does not prove real-world accuracy or the user's device output.

Local evidence (ignored; not raw-log publication):
`data/validation/iphone-safari-20261107/platform/`. Baseline, path, resumed path
JSON and PNGs are retained. The first path-script timeout occurred because the
test exited Fly into Orbit and failed to reopen Camera path before looking for
the slider. Its FAIL was retained; missing cases were completed with the correct
UI sequence. Native Safari and iOS Simulator observations were direct CUA screen
inspection; their numbers are manual observations, not scripted measurements.
Simulator Korean glyphs were missing during its fresh boot; rendering was still
visible. Finger-swipe acceptance is not claimed from the Simulator observation.

Safari WebDriver was unavailable because remote automation was disabled. No
preference was changed. Xcode command-line device tools were license-blocked; no
agreement was accepted. Safari's existing Open in Simulator action independently
started the installed Simulator and public page. The owned desktopSafari tab was
closed afterwards.

## Implemented isolation aids and comparison fix

The previous wholeSPZ comparison reset the camera. It could not answer whether
the currently blurry spot differed between LoD and whole loading. Switching now
retains position, direction, field of view, camera-path cursor and navigation
mode, including Fly. Playback pauses for a stable comparison.

`로딩 상태` is available within Fly. It shows actual displayed points, resident
pages, bytes and processing stage. `진단 JSON 저장` saves a local bounded trace
of the latest120samples at500ms intervals (about one minute). Nothing is uploaded.
It contains browser/GPU identification, viewport/drawing-buffer dimensions,
runtime budgets, queue counts, frame heartbeat and numeric progress. It excludes
asset URLs, private local paths, raw errors and image data.

Sampling is independent of the rendering loop so a paused renderer can be
noticed. Network pending alone is insufficient: buffered data can still be
waiting for decoding, LoD traversal, GPU upload or sorting. A10s unchanged stage
is labeled a wait, **not a confirmed hang**. Hidden-page throttling is distinct.
Idle queues/`settled` do not mean full detail or acceptable image quality.

Diagnostic build marker: `safari-paging-20261107-v2` (initial diagnostic-only release was v1).

## Source findings

Pinned Spark2.4.0 honors the explicit14-page/800k configuration on iOS; mobile
defaults do not replace it. The1.5DPR limit applies equally to wholeSPZ and LoD.
Landscape/FOV changes can alter screen-space selection and foveation. No blanket
budget increase or foveation change was justified by these observations.

[Upstream Spark issue481](https://github.com/sparkjsdev/spark/issues/481) reports
a bufferedRAD worker freeze in an iPhone immersiveAppClip. Our pinned decoder
contains the discussed bufferedReadableStream path, but applicability to ordinary
Safari on the user's compact scene is unconfirmed. A later independent WebKit
reproduction justified testing and adopting its buffered-input workaround; see above.

DesktopWebKit device emulation is not iOS hardware testing; see
[Playwright browser documentation](https://playwright.dev/docs/browsers) and
[device emulation](https://playwright.dev/docs/emulation).

## Validation and reproduction

- PASS: TypeScript, ESLint, all 224 unit tests (including four decoder-patch tests)
  and the production build. ESLint explicitly covers the new build helper and
  Vite/Vitest configuration. The final production build took 12.72s on this Mac.
- PASS: actual Vite dev HTTP module loading, including its cache-query module ID;
  raw distribution hash verification runs before Vite strips the source-map comment.
- PASS:5new diagnostic tests distinguish network completion from decode waiting,
  display stalls, hidden pages, unknown fields and healthy low selected counts.
- PASS: local production-build WebKit4/4 (gsplat2, compact2), including delayed-detail recovery.
- PASS: Chrome LoD regression (55.4s), actual forward/reverse page replacement and
  matched-pose SPZ comparison. RGB MAE 1.23159/255, central MAE 1.95758/255 and
  central edge ratio 0.96643; return-to-start pixel difference 0. The first run
  failed because sidebar text changed canvas height from 1177 to 1179px. That
  evidence is retained; the comparison now declares a fixed 800px canvas-height
  fixture so pixel comparisons use identical projections.
- PASS: Railway decoder-patch deployment
  `a563306e-26f6-48f8-a349-aa7d8ad9e050`, with all five changed public files
  matching the packaged sizes and SHA-256 checksums.
- PASS: public compact WebKit regression 2/2 (43.1s and 25.1s; suite 1.2m).
  The strengthened test waits for `settled`, every queue at zero and every
  processing stage idle. The held-detail case recovers from 52,874 points/1 page
  to 687,069 points/14 pages; 22,757,488 bytes, 15 requests, no pending requests
  or page errors. Moved/rotated Fly view and SPZ comparison return to exactly the
  same pose/FOV, displaying 691,095 points. The collapsed-inspector screenshot
  visibly retains window and tree detail; stretched road surfaces remain.
  Evidence: `platform/browser-v2-public-compact-r2/`. The first public run was
  deliberately interrupted to strengthen the queue assertions; its interrupted
  and NOT RUN records are preserved, not reported as an application failure.
- Physical iPhone16Pro acceptance: **NOT RUN**.

```sh
npm run typecheck
npm run lint
npm test
npm run build
# Official Playwright WebKit runtime required; uses Apple GPU on this Mac.
npx playwright install webkit
HEADLESS=1 npx playwright test tests/browser/safari-paging.pw.mjs
# Exercise the user's exact compact world as well.
HEADLESS=1 GS_SAFARI_WORLD=/worlds/paris-58m-lod-compact/world.json \
  npx playwright test tests/browser/safari-paging.pw.mjs
```

To isolate the reported device, open the deployed ParisLoD world, enter Fly,
open `로딩 상태` at the blurry spot and save the diagnosticJSON before switching.
Then use `같은 위치 · 전체 SPZ 비교`. If the same spot becomes clear, the serving
path is implicated; if both remain equally blurry, that observation concerns the
asset/view or a shared renderer path. A device trace and iOS version are still
needed to select a proven root-cause repair rather than infer one from desktop
success.
