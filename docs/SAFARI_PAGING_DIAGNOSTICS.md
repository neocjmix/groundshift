# Safari paging investigation — 2026-11-07

## Outcome

**The reported persistent blur on a physical iPhone16Pro Safari is unresolved.**
No physical iPhone was connected for inspection. DesktopChrome mobile emulation
from the earlier fix was insufficient acceptance for this report.

The current14-page/800k-target viewer refines normally in the available Safari
and WebKit environments below. These results neither disprove the user report nor
establish physical-device acceptance. No new page budget, model, reconstruction,
compression, asset or source-image changes were made.

## Executed reproduction attempts

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
| Physical iPhone16Pro Safari | **NOT RUN** — no connected device | Unresolved |

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

Diagnostic build marker: `safari-paging-20261107-v1`.

## Source findings

Pinned Spark2.4.0 honors the explicit14-page/800k configuration on iOS; mobile
defaults do not replace it. The1.5DPR limit applies equally to wholeSPZ and LoD.
Landscape/FOV changes can alter screen-space selection and foveation. No blanket
budget increase or foveation change was justified by these observations.

[Upstream Spark issue481](https://github.com/sparkjsdev/spark/issues/481) reports
a bufferedRAD worker freeze in an iPhone immersiveAppClip. Our pinned decoder
contains the discussed bufferedReadableStream path, but applicability to ordinary
Safari here is unconfirmed. It was not patched speculatively.

DesktopWebKit device emulation is not iOS hardware testing; see
[Playwright browser documentation](https://playwright.dev/docs/browsers) and
[device emulation](https://playwright.dev/docs/emulation).

## Validation and reproduction

- PASS: TypeScript, ESLint,220unit tests, production build.
- PASS:5new diagnostic tests distinguish network completion from decode waiting,
  display stalls, hidden pages, unknown fields and healthy low selected counts.
- Browser regression and public deployment evidence: pending below until executed.
- Physical iPhone16Pro acceptance: **NOT RUN**.

```sh
npm run typecheck
npm run lint
npm test
npm run build
# Official Playwright WebKit runtime required; uses Apple GPU on this Mac.
npx playwright install webkit
HEADLESS=1 npx playwright test tests/browser/safari-paging.pw.mjs
```

To isolate the reported device, open the deployed ParisLoD world, enter Fly,
open `로딩 상태` at the blurry spot and save the diagnosticJSON before switching.
Then use `같은 위치 · 전체 SPZ 비교`. If the same spot becomes clear, the serving
path is implicated; if both remain equally blurry, that observation concerns the
asset/view or a shared renderer path. A device trace and iOS version are still
needed to select a proven root-cause repair rather than infer one from desktop
success.
