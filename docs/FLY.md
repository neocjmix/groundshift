# Fly navigation — 2026-11-07

Choose **Fly ↗** beside **Orbit** in any world. Fly fills the screen and starts
from the current camera position and heading. It uses the same renderer,
Gaussian assets and streaming session; switching modes does not reload the world.

| Input | Action |
| --- | --- |
| Left joystick | Forward/backward and strafe, relative to heading |
| Right joystick | Turn and look up/down |
| ↑ / ↓ hold buttons | Rise / descend |
| WASD (or arrow keys) | Horizontal movement |
| Click the scene, then move mouse | Pointer-locked look where permitted |
| Mouse drag | Look fallback if pointer lock is unavailable/denied |
| E / Space, Q / Control | Rise, descend |
| Shift | Temporary3× speed |
| Speed selector |0.25×,0.5×,1×,2×,4× |
| ↺ | Restore the position/heading at Fly entry |
| Exit / Escape | Return to Orbit at the explored position |

Movement remains horizontal when looking up/down; height is explicit. There is
no collision, gravity, floor, eye-height inference or surface constraint. This
implements the user's unrestricted camera UX request, not safe walking geometry.
Speed uses viewer-world units: median positive marked camera-edge spacing per
second when available, otherwise one quarter of the orbit viewing distance.
These are usability heuristics, not inferred meters/second.

Two independent pointer owners allow simultaneous touch movement/look. Pointer
capture/cancel/release, key-up, window blur and hidden-document events clear
held input. Movement is time-based, diagonal speed is normalized and suspended
frame deltas are capped. Joystick updates use refs/direct knob transforms;
React does not rerender the Gaussian view per input sample. Entry clears leftover
Orbit damping without changing position. Exit hands the explored camera back to
Orbit; selecting Camera path explicitly returns to the recorded route.

The [native fullscreen request](https://developer.mozilla.org/en-US/docs/Web/API/Element/requestFullscreen)
starts from the Fly click. Fixed viewport CSS remains usable if native fullscreen
is unavailable or denied. The scene click separately requests
[pointer lock](https://developer.mozilla.org/en-US/docs/Web/API/Element/requestPointerLock),
with drag look retained on failure. The top toolbar and thumb controls respect
safe-area insets and portrait/landscape viewport sizes. Browser/host permissions
still determine whether native fullscreen and pointer lock are granted.

## Actual validation and retained failures

- PASS production build,TypeScript,lint without warnings,212JS tests
  (including5navigation checks for heading/up,movement timing,normalized input,
  reset,frame cap and world-unit speed). No collision tests were added.
- PASS existing local camera-path and viewer regression4cases: real scene
  rendering,Orbit/reset/zoom,folder replacement,context-loss recovery and path
  controls with explicitly synthetic continuity markers.
- PASS initial mobile emulation: actual CDP simultaneous two-touch input,
  movement+look,release stopping,390×844portrait and844×390landscape. Native
  fullscreen denial is an explicit test fixture exercising viewport fallback.
  This is **not physical iPhone/Safari evidence**.
- Initial desktop pointer-lock check FAIL: Chrome rejected it with
  `WrongDocumentError` despite secure context/user activation. Bringing the
  actual test tab to the foreground then acquires native lock and mouse look.
  That uncovered a real `setPointerCapture InvalidStateError`: pointer capture
  happened after pointer lock owned the mouse. Recovery captures fallback drag
  before requesting lock and skips capture when already locked.
- One combined rerun hit transient root HTTP404 while the asynchronous publisher
  rebuilt the shared `dist/` directory. The other5cases passed. Subsequent tests
  use the immutable curated publication directory,not a concurrently rebuilt
  development output. The original failure/trace is retained.
- PASS corrected immutable-package Fly3/3 in16.1s: real native fullscreen,
  actual pointer lock and mouse look,WASD,lift,reset,position-preserving Orbit
  handoff,one retained canvas and no wholeSPZ fetch in native paging mode;
  actual CDP dual-touch portrait/landscape; denied-lock drag fallback on a real
  sample without camera metadata; Escape exit. The API-denial cases are labeled
  fixtures,not claims of native platform rejection on those devices.
- PASS actual public r2 Fly3/3 in27.5s on Railway: native desktop input,
  real sample fallback,CDP mobile dual touch/portrait/landscape. Public file
  integrity is separately verified for6changed files; all39world assets remain
  unchanged.
- PASS r3 frozen-package4/4 in37.7s: prior camera-path regression plus
  all3Fly cases; the sample fallback case also forces a WebGL context-loss
  event,exits Fly while the renderer is in error,and retries rendering.
  Mode buttons now have44px minimum touch targets and the desktop help text
  sits above the lift buttons.
- FAIL r3 final public run:2PASS/1FAIL in34.4s. Desktop input and mobile
  dual touch passed; the forced context-loss/Exit/Retry case restored rendering
  but emitted an uncaught `undefined` error. The final error assertion caught
  it. Inspection of pinned Spark2.4.0 found that pending renderer jobs suppress
  cancellation errors only after their owner is disposed. The viewer now
  disposes Spark immediately on renderer failure, rather than leaving its jobs
  alive until Retry. No global exception suppression was added.
- PASS r4 immutable-package Fly3/3 in27.3s, including the final no-pageerror
  assertion after forced WebGL context loss. A focused repeat of the recovery
  case also passed3/3 in23.2s.
- PASS final actual public r4 Fly3/3 in35.2s: native fullscreen, pointer lock,
  WASD/mouse, lift/reset, position-preserving Orbit handoff, sample drag
  fallback, forced context-loss/Exit/Retry without page errors, and CDP dual
  touch in both orientations. Actual public desktop/portrait/landscape
  screenshots were inspected. Railway reports SUCCESS; all5changed public
  files match the pinned package. Fresh27-layer restore passes with1,254files.
- Physical iOS/Safari and Android hardware: **NOT RUN**. No new reconstruction,
  Gaussian quality,collision or kilometer-scale acceptance is claimed.

Local evidence remains in ignored `data/validation/fly-20261107/` with the initial
failures,diagnostic traces,frozen-package checks and actual screenshots. All39
worlds and prior reports/rollback assets are retained. Publication started before
browser checks completed; see[DEPLOYMENT.md](DEPLOYMENT.md) for pinned releases
and actual public integrity/interaction evidence.
The compact checked-in record is [evidence/fly-navigation.json](evidence/fly-navigation.json).

## Reproduce

```sh
npm run typecheck
npm run lint
npm test
npm run build
npx playwright test tests/browser/fly.pw.mjs
```

Run local browser checks while `dist/` is stable. During asynchronous publication,
serve a frozen package with `npm run preview -- --port 4342 --outDir PACKAGE/www`,
then set `GS_BASE_URL=http://127.0.0.1:4342` for Playwright. Public checks use
`GS_BASE_URL=https://groundshift-viewer-production.up.railway.app`.
The default Fly test uses the actual Paris native-LoD world; source assets must
be restored for local testing. Desktop tests explicitly foreground the test tab
before native pointer-lock interaction.
