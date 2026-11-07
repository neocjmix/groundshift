# Railway viewer deployment

**Live:** [Paris GS and paging](https://groundshift-viewer-production.up.railway.app/experiments/tourist-streaming/) · [PLY/SPZ storage comparison](https://groundshift-viewer-production.up.railway.app/experiments/compression/) · [Tangent GS only · current observation](https://groundshift-viewer-production.up.railway.app/experiments/tangent-background/) · [Final quality · actual1024px result](https://groundshift-viewer-production.up.railway.app/experiments/final-quality/) · [Model comparison · four local pipelines](https://groundshift-viewer-production.up.railway.app/experiments/model-selection/) · [Short street · seven GS results and conclusion](https://groundshift-viewer-production.up.railway.app/experiments/street/) · [Observed road anchors](https://groundshift-viewer-production.up.railway.app/experiments/stereo-anchors/) · [Perspective coverage and overlap](https://groundshift-viewer-production.up.railway.app/experiments/perspective-overlap/) · [Calibration and perspective-depth control](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-calibration/) · [Adjacent panorama comparison](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-pair/) · [One-panorama depth comparison](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-depth/) · [Without monocular depth](https://groundshift-viewer-production.up.railway.app/experiments/object-nodepth/) · [Real-only scooter comparison](https://groundshift-viewer-production.up.railway.app/experiments/object-real/) · [Chronological lab](https://groundshift-viewer-production.up.railway.app/experiments/lab/) · [Scooter experiment](https://groundshift-viewer-production.up.railway.app/experiments/object-focus/) · [Observation room](https://groundshift-viewer-production.up.railway.app/) · [Depth-guided scene report](https://groundshift-viewer-production.up.railway.app/experiments/depth-warp/) · [Photo depth maps](https://groundshift-viewer-production.up.railway.app/experiments/depth-v2/) · [65-frame panorama report](https://groundshift-viewer-production.up.railway.app/experiments/video-4to6/) · [My desk](https://groundshift-viewer-production.up.railway.app/?world=/worlds/desk/world.json) · [Estimated-camera dozer](https://groundshift-viewer-production.up.railway.app/?world=/worlds/independent/world.json) · [Supplied-camera dozer](https://groundshift-viewer-production.up.railway.app/?world=/worlds/reconstructed/world.json) · [Houseplant](https://groundshift-viewer-production.up.railway.app/?world=/worlds/sample/world.json)

The user explicitly designates Railway as an **observation surface**, not a production quality gate. Viewer changes, every distinct exported trial, and sanitized experiment evidence ship in the same workflow regardless of quality. Reconstruction, camera estimation and training remain local. Private original inputs, raw job logs and model weights stay on the Mac; explicitly licensed public comparison crops are included with attribution. The hosted viewer can open a private world folder directly in the browser, without uploading it.

**Required publication order — user instruction, 2026-11-06:** as soon as a
small result is deployable, start Railway deployment asynchronously and keep
working. Do not wait for all local tests, complete rendering verification,
benchmarks, all candidate outputs or the final experiment conclusion. Check the
minimum static build, authorized contents and artifact integrity, dispatch via
a deployment sub-agent or background process, and continue the next work in
parallel. Show provisional results and pending checks as NOT RUN; publish later
validation updates separately. Keep every prior observation in each incremental
package and retain rollback archives. Verification below describes evidence
collected after dispatch, not a reason to postpone the initial publication.

## Full-route expansion begins; user confirms Safari recovery — 2026-11-07

The user now reports persistent blur is resolved on their physical iPhone16Pro
Safari and the scene looks plausible. This is **USER REPORTED**, not an
instrumented physical-device PASS. Earlier NOT RUN/unresolved observations and
actual desktop WebKit tests remain retained. The private device attachment is
not published. Safari investigation status documentation is updated separately.

The new authorized expansion uses the **same existing Paris south-bank and
connected-street route**:876ordered source records,ranks808–1683,approximately
2.185km of source GPS polyline. The campaign is RUNNING; no new full-route native
export,geometry accuracy or browsing acceptance is claimed. Actual reconstructed
coverage remains24sources/first58m until new outputs are published. All39existing
scenes,current runtime,source/camera/binary bytes and prior evidence remain.
A distinct chronological lab observation links the campaign's rolling report.

Release `viewer-paris-route-started-2026-11-07`, archive
`groundshift-paris-route-started-20261107.tar.gz`: **23,791 bytes**, SHA-256
`ec17cc241396b8b9ba66a946df8763e5189d3948396a9f13c56f4bffb5cd4f54`.
Apply after37preceding layers. Exactly3sanitized report/timeline/catalog JSONs
change. The already verified production/runtime package is reused without
rebuilding shared dist. Privacy/JSON/39scene checks and complete base/target/
archive/composed integrity pass in4.884745s for1,280files. No new source image,
private attachment,raw log or weight is included. New metadata public-browser
checks are NOT RUN at dispatch; existing runtime acceptance is retained. Private
evidence:`data/validation/paris-full-route-20261107/publications/started/`.

Start pointer`dd736e625fe044906f242552d3cbcfe26f71fae3` deploys as
`07d23486-9978-4e05-b9f7-9ccd825328de`: created2026-11-07T08:47:23.868Z,
**SUCCESS** at08:48:15.980Z. Anonymous full archive readback passes in0.587402s.
All3changed public JSON sizes/SHA-256 pass in1.437501s after11readiness polls;
parsed report status confirms user-reported recovery and full-route export
NOT RUN. Summary is28,165bytes,SHA-256
`addd405531e79e409f244844cd326cdc12eeb4d737ccfeb33dfa3bd703a9c262`;
catalog is23,156bytes,SHA-256
`ce92d8645d6b98c456c64c9736cf9e545cd9d535bbfd15226403cc2e2537946a`.
The same previously empty-born ordinary restoration tree extends from37 to38
layers: every prior file rechecked, new archive pin verified, all1,280final
paths/sizes/SHA-256 PASS in3.714803s. No additional bulk copy or download is used.
New metadata browser acceptance remains NOT RUN here; unchanged v2 runtime
retains its already executed WebKit/Chrome checks. New native exports follow
as independent increments instead of waiting for complete route reconstruction.

### Second window: actual inputs and overlap alignment

The next report-only observation records acquired source ranks1004–1027:
24images/188,213,148bytes/202.955850s,first source-index196. Eight images overlap
previous988–1011 and16new input centers extend observed inputs; this is not an
extension of rendered GS coverage. Actual CPU SfM registers144/144virtual crops
from24physical panoramas,8,069sparse points,0.616063px mean reprojection error.
Pipeline-stage wall time is126.461858s; SfM's own elapsed report is126.234535s.

Actual image-derived relative alignment finds8shared/8inlier centers:
scale1.0090953511,maxcenter0.00507274reference-step,maxangle0.0691011degrees.
Transform-withheld ranks1005/1009 have0.00284136/0.00299061step residuals and
0.0466164/0.0530154degrees. These images participate in their separate SfM jobs;
they are withheld only from transform fitting, not independent unseen images.
Units are arbitrary SfM reference steps, not meters/GPS accuracy or proof of
street geometry. Tangent/depth/GS follow-up pipeline is RUNNING; new GS export
and browser rendering remain NOT RUN in this snapshot. Existing GS stays58m.

Release `viewer-seine-alignment-1004-1027-2026-11-07`, archive
`groundshift-seine-alignment-1004-1027-20261107.tar.gz`: **22,598bytes**, SHA-256
`27d9025a187b24357ea749da7763528d2e48db19ca74036257e7a3c1f999d5e4`.
Apply after38preceding layers. Exactly2sanitized report/timeline JSONs change;
24public source hash/dimension records are included without HDimage bytes or raw
paths/logs. The verified existing build/runtime is reused; no shared dist build
or scene change. Privacy/JSON and complete base/target/archive/composed integrity
PASS in5.314833s for1,280files. All39scenes and historical evidence remain.
Private evidence:`data/validation/paris-full-route-20261107/publications/alignment-1004-1027/`.
Rollout,public hashes and new metadata-browser checks follow dispatch.

Alignment pointer`4af187551abd0e5fb8bec8e689681b5c233b29d9` deploys as
`2fe64945-4a7c-48b1-a59c-1ccbcdb4ad90`: created2026-11-07T08:59:15.507Z,
**SUCCESS** at09:00:10.510Z. Anonymous complete archive readback passes in1.021727s;
both changed public JSON sizes/SHA-256 pass in0.998499s after11readiness polls.
Summary is40,877bytes,SHA-256
`c468eaca65310d023271988f86d494625be994f505ab4d67f97a3019c036cdae`.
The ordinary tree extends38→39layers with prior-file checks,archive pin and
every1,280final path/size/SHA-256 PASS in3.691340s. Changed restore files are
written to temporary siblings and atomically replaced, preserving any immutable
dedup hardlinks. No extra bulk copy/download is used. New report-browser
acceptance remains NOT RUN; no new GS rendering/coverage is inferred from this
metadata publication. Existing scene/runtime checks remain preserved.

### Bounded aligned-route viewer, before new native export

Source`9ccc74f` adds optional route worlds with image-derived common coordinates,
camera-driven owner selection,one Spark renderer/shared page budget and at most
two resident segment roots. Incoming work retains the previous primary until
ready,with failure/retry,stale-request disposal and same-position current-segment
wholeSPZ comparison. This is code readiness, **not real two-segment GPU boundary
or appearance acceptance**; those checks remain NOT RUN until actual new exports.
All39current worlds and all257world files(including catalog)remain byte-identical.

Release `viewer-seine-route-viewer-2026-11-07`, archive
`groundshift-seine-route-viewer-20261107.tar.gz`: **1,086,815bytes**, SHA-256
`7906cf0aadbeb3925138ce1ccfdced31c882e440ae359c84baa5ec134607c731`.
Apply after39preceding layers. A fresh production build PASS in3.41s; explicit
full curation retains17inert historical background files. ExistingSafari v2
compiled marker/direct-buffer workaround remain present. Parent-verified unit,
TypeScript,ESLint and2local existing-Safari regressions PASS; static results do
not prove real route rendering. Complete base/target/archive/composed integrity
PASS in7.136973s:6compiled/HTML/report changes,1,187target public files and
1,283composed files. Public existing-scene regression checks follow dispatch;
new actual two-segment rendering remains NOT RUN. Private evidence:
`data/validation/paris-full-route-20261107/publications/route-viewer/`.

Route-viewer pointer`23bb1ccb1d921682567dd609293cdb91c38bf455` deploys as
`c1eeed01-3ca2-42cc-af1f-3637f45c3b67`: created2026-11-07T09:04:26.866Z,
**SUCCESS** at09:05:15.117Z. Anonymous complete archive readback passes in1.206115s;
all6changed public sizes/SHA-256 pass in3.814280s after10readiness polls. RootHTML
SHA-256 is`fd96a72157264adf861b837d1b224bd4c9e1ba53d1cba37796afbde379e36d9b`.
The ordinary tree extends39→40layers,with prior-file checks,new archive pin and
all1,283final paths/sizes/SHA-256 PASS in3.852642s. Changed files use hardlink-safe
atomic replacement; no extra bulk copy/download. Public existing-compact WebKit
regression is started only after this live/hash signal; actual two-segment GPU
boundary/appearance checks remain NOT RUN until the new real scene exists.

After rollout, actual desktop WebKit27.2 with the iPhone-profile fixture passes
the existing public compact2/2 in59.9s: Fly/same-position SPZ/pose/FOV/export and
return691,107selected/14pages; held52,874/1→recovered687,069/14,22,757,488bytes,
15requests,pending0,allqueues0,allstagesidle,errors0. The collapsed-inspector PNG
is directly inspected: windows/tree detail visible,stretched-road/ghosting remains.
This is concurrent with native training,not a speed benchmark or instrumented
physical-iPhone acceptance. All owned browser processes exit. Actual two-segment
boundary/appearance remains NOT RUN. Evidence:`route-viewer/browser-public-compact/`.

### Late route work: mechanical ownership repair; native training starts

Source`5534b09` prevents retired route pages from accepting late Spark work that
could recreate disposed GPU resources. Targeted9route tests,TypeScript and
changed-source lint PASS; real two-segment GPU lifecycle/boundary checks remain
NOT RUN until exports exist. A fresh production build PASS in3.59s. All39scenes,
all257worldfiles and17inert historical files stay byte-identical. The later mobile
route-panel source`7bbe9aa` arrives after this freeze and is not in this archive.

The rolling report also records actual1004–1027 tangent inputs98.908328s,
depth362.371952s,fusion24.074309s PASS,then native Metal training RUNNING. Declared
768px/8ksteps/800kcap are targets,not completed counts. New GS export/two-segment
rendering remains NOT RUN; actual rendered coverage stays58m. The previous9ccc
public compact2/2 result is explicitly tied to that source/concurrent native
load,not mislabeled as real two-segment or instrumented-device acceptance.

Release `viewer-seine-route-ownership-fix-2026-11-07`, archive
`groundshift-seine-route-ownership-fix-20261107.tar.gz`: **1,087,885bytes**, SHA-256
`a8a5af893f7d24a5eafb5aaa08ceaf003f3eea6fa3b17e61c7b9baa481c3daac`.
Apply after40preceding layers. Complete base/target/archive/composed integrity
PASS in7.140109s:6compiled/HTML/report files,1,187target public and1,286composed
files. No native export is overwritten. Privacy/curation checks PASS; actual new
route GPU checks are NOT RUN at dispatch. Private evidence:
`data/validation/paris-full-route-20261107/publications/route-ownership-fix/`.

### Incoming-route failure recovery and mobile route status

Source`879e3d5` retains the primary when incoming metadata succeeds but its RAD
transfer fails,including mid-fade; source`7bbe9aa` keeps route status compact on
narrow screens while preserving full diagnostics. Full238unit,TypeScript and
ESLint checks PASS. Actual independently trained two-segment GPU boundary/error
recovery remains NOT RUN until export. This ready increment publishes while
native work continues; no reconstruction ETA is inferred from the old baseline.

Release `viewer-seine-route-recovery-2026-11-07`, archive
`groundshift-seine-route-recovery-20261107.tar.gz`: **1,090,616bytes**, SHA-256
`e4e829714a3406aa8c4e8573156d6543646f345fd947dfb77f2dfc65f0877dea`.
Apply after41preceding layers. Fresh production build PASS in4.95s; explicit
full39-scene curation retains all257world files and17inert historical files
byte-identically. Complete base/target/archive/composed integrity PASS in6.330432s:
7compiled/CSS/HTML/report changes,1,187target public and1,290composed files.
Public readback/render checks follow dispatch. Private evidence:
`data/validation/paris-full-route-20261107/publications/route-recovery/`.

### Reusable completed-snapshot publication

The ownership-fix rollout `be322506-4a41-42f6-ac7c-9052024f5408` and recovery
rollout `7afdc437-89b6-4c6a-9268-ebb387c995ae` reach SUCCESS. Recovery's seven
changed public files match exact sizes/SHA-256 in4.759959s. The existing ordinary
restore extends40→42archives without a full duplicate copy/download; all1,290
paths/sizes/SHA-256 PASS in4.468784s, using hardlink-safe atomic replacement.
Private evidence: `route-recovery/{public-delta-readback,ordinary-restore-42}.json`.

`scripts/publish-seine-route.py` prepares the oldest unreceipted completed
`route-world-NNN` from `route-run.json`,or an explicitly selected snapshot. It
rejects partial/unexecuted exports,camera gaps,unsafe paths,private metadata,
changed RAD size/SHA declarations,coverage regression and modification of any
already published immutable segment. It follows declared files rather than
walking raw job folders. The source snapshot remains untouched. Selected assets
are hardlinked into a new immutable publication world; canonical public files
use atomic replacement. Catalog,timeline,report and explicit observation allowlist
are updated without removing previous worlds or observations. Native export PASS
and new route/boundary GPU NOT RUN remain separate. The initial thumbnail is
explicitly the retained baseline GS preview,not new-route rendering evidence.

```sh
# Safe before the first export: prints WAITING/NO NEW status without publication.
python3 scripts/publish-seine-route.py data/jobs/seine-full-20261107
# Or select the atomically complete snapshot explicitly.
python3 scripts/publish-seine-route.py data/jobs/seine-full-20261107 \
  --snapshot data/jobs/seine-full-20261107/route-world-002
python3 -m unittest discover -s scripts/tests -p 'test_publish_seine_route.py' -v
```

A PREPARED receipt includes selected source size/SHA records and the immutable
world source path. Repeating preparation returns the same pending lineage.
The deployment owner then runs the existing fresh-build/explicit-curation/
`package-viewer-overlay.py` workflow against the latest physically composed
inventory,uploads a fresh checksum-pinned archive,updates the Git pointer,and
triggers the existing Railway service without waiting for remaining native jobs.
Only new/changed files enter each archive; repeated full-route payload archives
are avoided. After dispatch,write
`data/jobs/seine-full-20261107/publication-receipts/NNN.json` with snapshot,archive
SHA,commit/deployment IDs and actual status,then append public-hash/browser results.
This is local publication bookkeeping,not a service/queue/framework.

The helper counts final Docker COPY layers and warns at90. The publisher's hard
ceiling is110COPY instructions, not90: this bounded55-window campaign is expected
to finish at94COPY instructions. This is a conservative workflow threshold,not
an asserted Railway hard limit.
All previous release archives remain rollback evidence after consolidation.
Five focused publication-boundary tests PASS. An initial macOS temporary-path
normalization fixture fails and is corrected by resolving both compared roots;
no native/GPU success is inferred from these synthetic checks.

### Background publication through the existing branch-follow service

Attempting branch-follow without a commit pin does **not** establish working Git
autodeploy. The connector returns a null pin, but the authenticated dashboard
still shows `Connect Environment to Branch`, `Could not load branches` and
`Auto deploy unavailable`. Controlled real Docker-pointer push`e5397e8` produces
no deployment event in the bounded observation. The temporary default`main`
branch draft is discarded without applying it; existing production/configuration
is retained. Repository Edit offers GitHub App configuration. No login, permission
grant or credential extraction is attempted. The local Railway CLI remains
unauthorized both with its inherited token and saved-login fallback; no login or
credential extraction is attempted. GitHub release upload/Git push remain healthy.
The healthy existing Railway connector remains the dispatch path. The thread's
five-minute heartbeat dispatches queued pointers; this does not prove immediate
Git autodeploy. A later switch to automatic Git dispatch requires one actual
push-triggered SUCCESS. Official [Railway guidance](https://docs.railway.com/deployments/github-autodeploys)
requires a connected contributor/app and an enabled trigger branch.

Release `viewer-seine-route-watcher-2026-11-07`, archive
`groundshift-seine-route-watcher-20261107.tar.gz`: **9,915bytes**, SHA-256
`964c633748733e6dd257a239472d584c5fdb78c1d07b792bcc07aeedcea9423b`.
Apply after42preceding archives. Fresh build/full curation PASS; all39scenes and
prior reports remain. The report UI now distinguishes growing reconstructed
coverage from original24-image acquisition and baseline measurements. Exactly
3compiled/HTML files change;1,291composed paths pass complete integrity checks
in5.257823s. Anonymous complete archive readback PASS in0.579729s. New actual
two-segment GPU/boundary checks remain NOT RUN; existing GS stays58m.

`scripts/watch-seine-publication.py` is a local process, not hosted infrastructure.
It polls atomic completed exports every5seconds, selects oldest-first, validates
the existing curation boundary, builds committed runtime sources, packages the
explicit complete observation surface, uploads only changed files, verifies the
anonymous archive, appends its checksum-pinned Docker layer and pushes the branch.
In connector fallback mode, each upload/pointer push immediately writes
`publication-dispatch/NNN.json` with **DISPATCH_PENDING**, exact commit/archive/SHA
and existing connector target. The thread heartbeat triggers that pointer and
checks provider status. Git push alone is never called dispatched or live.
It checks public coverage and every changed public file before writing a delivered
receipt. Provider deployment status and browser/GPU acceptance remain NOT RUN in
background receipts until independently audited. Later cumulative snapshots can
supersede unobserved canonical metadata; their receipts say so explicitly and
verify retained immutable segment bytes rather than claiming old metadata was live.

The worker holds `data/jobs/seine-full-20261107/.static-publication.lock` for its
lifetime. **Stop it before manual publication or any competing branch push**,
then restart with `--adopt-base-inventory --base-inventory <new-composed-inventory>`.
The worker verifies all files and refuses adoption during an unfinished transaction.
Native jobs use a separate
lock and continue. Uncommitted runtime/build/curator source blocks publication;
unrelated native Python work does not. Runtime bytes are checked before/after
build/curation. All attempt logs, PID/heartbeat, retry state, pending records and
delivery receipts stay in the ignored local job. Failed packaging/upload/push or
public readback retains the pending lineage; it never retrains or fabricates a
successful delivery. Rollback archives remain unchanged. Ninety final COPY
instructions warn;110require a verified consolidation checkpoint. The43current
archives use40COPY instructions because historical archives share one stage.
Adding54new snapshots yields94COPY, plus one Caddyfile COPY and five pinned
Caddy filesystem layers:100image layers for the planned campaign. A bounded
manifest audit confirms five base filesystem layers on both amd64/arm64; the110
COPY ceiling leaves room within [Docker overlay2's documented128lower-layer range](https://docs.docker.com/engine/storage/drivers/overlayfs-driver/).
This corrects the old90gate that would prematurely stop snapshots052–055. It does
not claim an experimentally tested Railway maximum or expand reconstruction scope.
Actual pinned manifest/layer/archive audit is retained locally in
`data/validation/paris-full-route-20261107/storage/publication-layer-budget.json`.

`--reuse-inventory` verifies matching current content against the older on-disk
size/SHA before hardlinking immutable files. Changed files get separate inodes.
The controlled package shares1,184files/1,373,079,702bytes with the verified base;
it does not create another historical1.4GB copy per new segment. The assembled
overlay also shares old immutable files. Do not edit frozen package bytes in place.
Forty packaging tests and four watcher boundary tests PASS, including corrupt-base
rejection, unchanged inode reuse, changed metadata isolation, ordered completed
exports, idempotent pointers, preservation of missing historical observations and
proof that Git push alone creates only a pending queue, never a delivery receipt.
These fixtures do not prove native/GPU/browser behavior.

The initial curator retained every selected file Buffer during preflight. That
would grow with the complete route and compete with native work on16GB unified
memory. It now records source paths plus size/SHA pins after the same preflight
checks, rereads/revalidates one source at a time for writing, and verifies/reuses
old immutable files without retaining their Buffers. Only generated catalog and
ignore metadata remain buffered. This applies with and without reuse. A default
route-control duplicate is compared by its pinned hash, preserving conflict checks.

Actual full39-scene reuse curation:12.86s wall,206,766,080bytes maximumRSS and
182,276,632bytes peak footprint reported by macOS`/usr/bin/time -l`.
The plan retains23,194generated bytes and pins1,171source files without their
Buffers;1,170files/1,359,182,787bytes are hardlinked after verification. All1,170
selected public size/SHA records match the previous live composed inventory.
Forty packaging tests and lint PASS. Evidence:`branch-watcher/memory-{cli.log,
curation.json,verification.json,package-tests.log}`. This is one concurrent-native
CLI observation, with no old RSS measurement for comparison; it does not prove
that the independently observed Metal stall/host swap is fixed. No GPU launched,
no scene changed and no redundant artifact rollout is needed for this local fix.

```sh
# Actual fallback: immediate local packaging/upload/push; connector heartbeat dispatch.
python3 scripts/watch-seine-publication.py data/jobs/seine-full-20261107 \
  --base-inventory data/validation/paris-full-route-20261107/publications/branch-watcher/groundshift-seine-route-watcher-20261107.tar.inventory.json \
  --autodeploy-proof data/jobs/seine-full-20261107/static-publication/branch-autodeploy-blocked.json \
  --connector-fallback
```

The local worker handles completed native snapshots. Failure/provisional changes
without a new export use the same five-minute thread heartbeat: inspect
`route-run.json` and stage evidence, sanitize the actual blocker into the existing
report/timeline, then publish a metadata-only overlay using the current composed
inventory and healthy connector. Raw exception logs, paths and private URLs stay
local. This fallback is explicit; it is not an event-driven failure-report watcher.
Actual connector dispatch of pointer`a2ea732d800f19995da612c9f883e9929f26819e`
creates`81c7310b-3799-4412-83bf-cd5d40a630be` at09:48:12.793Z, reaches
**SUCCESS** at09:49:49.157Z. All3changed public file sizes/SHA-256 PASS after four
readiness attempts/20.043312s; this duration includes waiting for rollout, not a
download benchmark. The ordinary tree extends42→43archives: prior files are
rechecked, the new archive pin and all1,291final paths/sizes/SHA-256 PASS in
5.656241s, with no additional full copy/download. The deployed tourist bundle is
9,030bytes,SHA`1a37ec5c69b1423df49bd4bd341fd929ba5f52abd90ff00f85e26a12339b58e6`.
This is manual connector deployment, **not proof of Git autodeploy**. An initial
invalid full-SHA argument is rejected without a deployment; the exact Git-read
SHA above succeeds. No native/route GPU status is changed by these file checks.

The worker actually executes an initial one-shot scan and then starts detached
at09:47:55Z (initialPID34483), producing fresh five-second WAITING heartbeats,
no error and delivery mode`CONNECTOR QUEUE`. A bounded maintenance stop loads the
queue-gate test and safe base-adoption option. The current owned PID/start command
is retained in`data/jobs/seine-full-20261107/static-publication/process.json`,
and actual freshness/status in`heartbeat.json`; do not infer process liveness from
the old PID alone. No completed new export exists at this check, so the real
snapshot→release path is NOT RUN despite passing boundary fixtures. The239JS
tests,40packaging subset,4watcher tests and5publication helper tests PASS; new
native training and route acceptance remain independent.

## Safari reproduction and device-local diagnostics — 2026-11-07

The user reports persistent blur on physical iPhone16Pro Safari. This release
provides same-position LoD/whole-SPZ comparison and device-local diagnostic export;
it is **not a proven root-cause fix**. Physical iPhone reproduction and resolution
remain **NOT RUN**. The report and catalog now state the current14-page/917,504-slot
pool and800k selection target, distinguishing view-dependent actual counts and
historical8-page/350k measurements. No source image, training parameter, scene
binary, camera or world manifest changes. All39 scenes and prior evidence remain.

Actual M2 desktop Safari26.6.2 UI observation records685,467selected/14pages and a
street render; responsive402×681/3× records680,013. Native Safari WebDriver remains
NOT RUN because remote automation is disabled. Actual desktop Playwright WebKit27.2
with iPhone-profile viewport/touch/DPR records680,013selected/14pages after50s,
with no renderer errors. The initial path test fails on a30s slider-focus wait;
its resumed mid/landscape/compact observations pass execution and preserve that
failure. These desktop observations are not physical-iPhone GPU evidence.
An installed iPhone17Pro/iOS26.3 Simulator opened through Safari's menu records
672,170selected/14pages and a street render; Fly movement is still pending in this
frozen report. CLI license/automation blockers and this separate Simulator UI
execution are distinguished; the agent does not accept the Xcode license.

Release `viewer-safari-diagnostics-2026-11-07`, archive
`groundshift-safari-diagnostics-20261107.tar.gz`: **1,084,734 bytes**, SHA-256
`bcb1f2c28f75f623fe488f5e23824e00dcfc6017f39e386d84d37b29eca818da`.
Apply after33 preceding layers. Root's completed production build/typecheck/lint/
220unit PASS are reused at source`255a9da`; the deployment agent verifies compiled
version`safari-paging-20261107-v1` and does not rebuild shared`dist` while local
WebKit tests run. Explicit full39-scene curation,authorized metadata and complete
base/target/archive/composed integrity pass in13.544657s:9 changed compiled/HTML/
metadata files,1,188 target public files,1,276 composed files. The17 inert historical
background files remain retained. New diagnostic public-browser checks are
**NOT RUN** at dispatch. Private evidence stays under
`data/validation/iphone-safari-20261107/publications/diagnostics/`.

Initial diagnostic pointer `bdc2ce5e58df579f21454ec578201156a3ccd9f2` deploys as
`50c978ee-f1e4-4506-bd08-b822cc86c6f5`: created2026-11-07T07:28:04.547Z,
**SUCCESS** at07:28:59.113Z. Anonymous archive size/SHA readback passes in0.856425s;
all9 changed public files match exact sizes/SHA-256 in5.279947s after11 rollout
polls. Root HTML SHA-256 is
`cb5a691fb3fce07235d72da585156e0a1de65ccb59b69737fafb257d6ead89c8`;
report summary SHA-256 is
`3a7080045b5ffa5dd818521c956f7780ef38a2022e217473598c64730faebc95`.
The user identifies the compact Paris world as the affected URL; new public
browser checks prioritize that world. The private device screenshot is not
published. Rollout/file integrity does not establish physical-iPhone resolution.
The same ordinary tree that began empty for the32-layer check is extended from
33 to34 layers: every prior file is rechecked before extraction, the new archive
pin is verified, and all1,276 final file sizes/SHA-256 plus the exact path set
pass in8.967627s. No additional bulk copy or archive download is used. Evidence:
`publications/diagnostics/ordinary-restore-34.json` under the private Safari job.

### Provisional WebKit worker finding

The next report-only increment retains the initial normal desktop observations
and adds an actual delayed-network gsplat failure on desktop WebKit. After an11s
hold and35s observation, all23.02MB/15requests are received but chunk2 has no decode
result/error:13pages/416,335selected,35.029s pending RPC. An isolated worker
already-buffered direct push/finish fixture recovers chunk2 in25ms and reaches
14pages/680,013selected with idle queues. Stream instrumentation can also remove
reproduction, so the exact internal await/WASM cause is not isolated. This does
not establish the physical-iPhone compact cause or resolution. Production patch
and new public-browser checks are NOT RUN in this provisional metadata.

Release `viewer-safari-worker-evidence-2026-11-07`, archive
`groundshift-safari-worker-evidence-20261107.tar.gz`: **16,745 bytes**, SHA-256
`784aa1bdcccc215f46d30b46cc007ea9452b3527c6336dcf4beee64a19c02e6b`.
Apply after34 preceding layers. Exactly2sanitized report/timeline JSON files
change; no app/world/image bytes change. Complete base/target/archive/composed
integrity passes in8.262488s for1,276files; anonymous archive readback passes
in0.586250s. All39scenes and prior observations remain. Evidence stays private
under`data/validation/iphone-safari-20261107/publications/worker-evidence/`.

Provisional pointer`732cdd27a981bff5b99f8623ddc89ddb086dfe01` deploys as
`23ae0a97-c245-4782-af55-e71b9030b93f`: created2026-11-07T07:43:42.197Z,
**SUCCESS** at07:44:41.392Z. Both changed public JSON files match their exact
sizes/SHA-256 in1.132692s. The following app patch is dispatched without waiting
for any complete experiment conclusion.

### Buffered-worker workaround and diagnostics v2

The next source increment bypasses the synthetic ReadableStream only when the
worker already owns complete `fileBytes`: status,decoder push and finish use the
same original decoder. Actual URL streaming stays unchanged. The original
Spark2.4.0 distribution SHA and exactly one known branch are required; upstream
drift fails the build. Diagnostic v2 includes actual camera pose/FOV/mode/cursor
in a device-local downloaded JSON, with no automatic upload. No source image,
training parameter,Gaussian/camera/world-manifest bytes change.

Release `viewer-safari-worker-fix-2026-11-07`, archive
`groundshift-safari-worker-fix-20261107.tar.gz`: **1,061,445 bytes**, SHA-256
`9861fcfc0d56b739751665026dd7c71ca011b13b0519ba1a5224ab6cfec1ff94`.
Apply after35 preceding layers. Root's completed production build14.03s and
223unit/typecheck/lint PASS are reused at source`bc25334`; the actual compiled
v2 marker and direct buffered branch are verified. Full39-scene explicit curation
retains17inert background files. All256non-catalog worldfiles remain byte-identical.
Complete base/target/archive/composed integrity passes in8.785584s:5 compiled/HTML
changes,1,188target public files and1,280composed files. An initial supplemental
text probe expects an invented marker and fails; the corrected exact compiled
branch probe passes without a source change. Packaged/public workaround checks
are NOT RUN at dispatch. Physical iPhone16Pro compact cause/resolution remains
unconfirmed and NOT RUN, regardless of desktop fixture recovery.
Private evidence: `data/validation/iphone-safari-20261107/publications/worker-fix/`.

Anonymous complete archive readback passes in1.342025s. The ordinary tree is
extended from34 to36 layers after rechecking all prior files; both added archive
pins and every final1,280path,size/SHA-256 pass in4.114088s. No additional bulk
copy or download is used. Evidence:`ordinary-restore-36.json`. New public-browser
acceptance remains a separate check after rollout.

Workaround pointer`3b65f9fa03ee453d5162f7f9a769a431f00d90c1` deploys as
`a563306e-26f6-48f8-a349-aa7d8ad9e050`: created2026-11-07T07:45:41.782Z;
the healthcheck passes at07:49:48.134Z and Railway reports SUCCESS. All5changed
public files match exact size/SHA-256 in3.130459s after43readiness polls. Root
HTML SHA-256 is
`3f98a6a7231a21761c353b50e3dde423c49b685734ecb10f2db291d0e9555b3c`.
The rollout includes full image export/registry publication; no infrastructure
configuration is changed. Fresh public compact browser checks follow this live
and hash-verified signal, not the initial source dispatch.

### Executed workaround checks and final report

The final evidence increment records actual uninstrumented desktop WebKit gsplat
2/2PASS(50.4s) and compact2/2PASS(44.7s), including held-network recovery and idle
queues. The live compact page then passes2/2(43.1s+25.1s; suite1.2min): initial
679,484selected/14pages; moved/returned691,095/14; held52,874/1→recovered687,069/14,
22,757,488bytes/15requests,pending0,allqueues0,allstagesidle,errors0. The final
collapsed-inspector screenshot is actually inspected: nearby windows/trees are
visible; original stretched-road GS defects remain. The first public attempt is
intentionally interrupted to strengthen the idle criteria and stays NOT RUN/
interrupted, not an application FAIL. Physical iPhone16Pro compact same-cause and
resolution remain unconfirmed/NOT RUN.

Actual Chrome page replacement/return and matched SPZ comparison pass in55.4s
with a fixed800pxcanvas:MAE1.23159/255,center1.95758,edge0.96643,returnpixelMAE0.
The first fixture fails because sidebar text changes canvas1177→1179px; it is
retained and corrected by the declared fixed-size fixture. All224unit,
TypeScript,ESLint,production build and actual Vite HTTP dev-patch checks pass.
Dev-hook/lint/test changes`88971ac`,`77bb7f3`,`d00c2ba` produce exactly the same
5compiled/HTML sizes/SHA as live v2; no new runtime archive is necessary.

Release `viewer-safari-worker-verified-2026-11-07`, archive
`groundshift-safari-worker-verified-20261107.tar.gz`: **17,654 bytes**, SHA-256
`6c61e70512b742cc1481e7504b2f9dab0b8f4c9871e701c4b00483979fb999f0`.
Apply after36 preceding layers. Exactly2sanitized report/timeline JSON files
change; all1,280composed files and all39worlds remain retained. Complete base/
target/archive/composed integrity passes in10.433036s. App,world,image,camera and
source data bytes are unchanged. A repeat browser suite is not required for this
metadata-only increment; final rollout and exact public JSON checks follow
dispatch. Private evidence:`data/validation/iphone-safari-20261107/publications/verified/`.

Anonymous complete archive readback passes in1.928344s. The ordinary tree extends
from36 to37 layers after rechecking every prior file; the last archive pin and
all1,280final paths/sizes/SHA-256 pass in4.187134s. This reuses the same tree that
began empty for the32-layer extraction, with each later extension independently
checked; no extra bulk copy or download is needed. Evidence:`ordinary-restore-37.json`.

Final report pointer`6079c088faadae2f91daf0e9a881a9e18483315a` deploys as
`2b7940ae-f89f-4313-848e-4cf3a1ec4326`: created2026-11-07T07:55:53.400Z,
**SUCCESS** at07:56:45.327Z. After11readiness polls, exact public sizes/SHA-256
pass for both changed JSONs and the5unchanged browser-tested runtime files in
4.384597s. The final summary is25,346bytes,SHA-256
`59e97d17a094d5c073b874c9fa1c4f570ab503a502cca4733593c390ed1a5c8f`;
timeline is33,707bytes,SHA-256
`9b202b4430a981d1b95441038c423687dcbbf70c10f13c90c46fa270ed871d9e`.
Both public JSONs parse and retain explicit NOT RUN physical-device status.
All39scenes,the initial/failing observations,and37rollback archives remain
retained. Final documentation commits without another artifact rollout; the
service stays pinned to the inspected v2 runtime plus these exact report bytes.

## Mobile Fly refinement and near-detail investigation — 2026-11-07

The first increment is **interim mobile UI**, while blurry near-detail LoD loading
remains under investigation. It adjusts knob centering, adds a floating left
movement stick, replaces the right stick with direct scene touch-drag look and
places lift controls on the right. This increment makes no LoD detail/quality
acceptance claim. Browser checks are **NOT RUN** at dispatch; the main agent tests
an immutable curated package while loading investigation continues separately.
All39 scenes,17 inert historical background files and every prior observation
remain retained. No scene/report/source-image/camera/provenance bytes change;
no reconstruction, training or new hosting service is introduced.

Release `viewer-mobile-fly-ui-2026-11-07`, archive
`groundshift-mobile-fly-ui-20261107.tar.gz`: **1,060,799 bytes**, SHA-256
`10264d84cb6989df04a21a5c22654313c9955ad18c92ff8aa1eb50226607feab`.
Apply after the27 preceding layers. Fresh production build passes in3.63s;
explicit authorized curation and full base/target/archive/composed size/hash
integrity pass in5.276609s:6 changed compiled assets/HTML,1,185 target public
files and1,259 composed files. Rollout/public-file/browser checks follow dispatch.
Private publication evidence stays under
`data/validation/fly-mobile-detail-20261107/publications/mobile-ui/`.

Interim pointer `3cee4375c5cd7a310864b0f4b42b396c09aeb5a7` deploys as
`b6bd2198-4fb2-4bc3-a646-6b0f44c61a44`: created2026-11-07T01:15:53.020Z,
**SUCCESS** at01:16:48.435Z. Anonymous complete archive readback verifies size/SHA
in1.166859s. All6 changed public files match exact sizes/SHA-256 in4.023456s;
root HTML SHA-256 is
`d62284bd83afaa4e769ce231f40928f310e38d517f77f9fad6fd42f48b32d3aa`.
Full ordinary restoration is deferred to the final stable increment to avoid
unnecessary duplicate local copies; all minimum overlay/composed integrity checks
already pass. Browser interaction and detailed LoD findings remain separately
pending until executed, not inferred from this successful rollout.

The next increment publishes the near-detail refinement candidate immediately:
both existing Paris LoD manifests now declare14 pages /917,504 slots with an
800,000 selection target. The viewer adds residency diagnostics, a readable
“주변 세부 불러오는 중” state and a GPU-readback error ownership guard. Preliminary
local four-view diagnostics observe restored near/central detail; public app
checks and broader appearance acceptance are **NOT RUN** at dispatch. The earlier
8-page/350k-selection trial and its failures remain preserved in evidence and
immutable rollback releases. This is serving-policy recovery, not new training.

Release `viewer-lod-detail-refinement-2026-11-07`, archive
`groundshift-lod-detail-refinement-20261107.tar.gz`: **1,060,573 bytes**, SHA-256
`2957babd5ee4eee05b003c607a8e900a978da8078d5c13f9113944481aaeda94`.
Apply after28 preceding layers. Fresh production build passes in12.88s; authorized
curation and full base/target/archive/composed integrity pass in4.995145s, with7
changed compiled/HTML/explicit manifest files,1,185 selected public files and1,263
composed files. The only changed world files are the two LoD `world.json` files;
all255 other selected world files, including every SPZ/RAD binary, remain exactly
byte-identical. All39 scenes/reports/source images are retained. An early package
preflight ran before this agent's asynchronous build had finished and failed on
missing `dist/index.html`; no archive was created. The exact failure stays local,
and the retry after actual build completion passes without source changes.
Evidence stays under
`data/validation/fly-mobile-detail-20261107/publications/detail-refinement/`.

Detail pointer `0c316fc8e428cbe34fe4ce2f87e4fd7c0a620ff8` deploys as
`b4258d63-8297-4f83-9c15-1095cbc172cb`: created2026-11-07T01:24:04.382Z,
**SUCCESS** at01:25:00.076Z. Anonymous complete archive readback verifies its
size/SHA in1.106555s. All7 changed public files match exact sizes/SHA-256 in
4.204022s, including both explicit14-page/800k manifests. Root HTML SHA-256 is
`a98d2c4cb7dd7bb368468e4cd62ed0252302a1c881aa907a50fedc9dda3063f5`.
Actual public behavior and broader measured appearance checks follow this
successful delivery; they are not inferred from these hash checks.

Actual interaction traces show stream diagnostics intercepting Zoom clicks. The
next mechanical increment moves that panel from bottom5rem to8rem; corrected
browser interaction remains **NOT RUN** at dispatch. Release
`viewer-control-clearance-2026-11-07`, archive
`groundshift-viewer-control-clearance-20261107.tar.gz`: **1,060,931 bytes**, SHA-256
`fce177d808f18bf6d9e1c112f5bd5f6deaf9b111913f979f1bbbf812eeb7556d`.
Apply after29 preceding layers. Fresh build passes in14.70s; explicit full39-scene
curation with all include flags and complete overlay/composed integrity pass in
5.864386s (6 compiled/HTML changes,1,185 target public files,1,268 composed files).
All257 selected world files, including both14-page manifests and every scene
binary, remain byte-identical. Reports/source images and every prior observation
are retained. The unrelated accidental sample-only local package is not used.
Private evidence remains under
`data/validation/fly-mobile-detail-20261107/publications/control-clearance/`.

A provisional five-file evidence update follows without rebuilding the viewer:
the current report/timeline and three actual PNGs show the earlier8-page baseline,
refined14-page rendering and whole-SPZ control. Old8-page measurements remain
historical; final public rechecks are **NOT RUN** in this frozen observation. It
explicitly states that only the first58m of the2.19km source route is reconstructed.

Release `viewer-lod-detail-evidence-2026-11-07`, archive
`groundshift-lod-detail-evidence-20261107.tar.gz`: **3,650,321 bytes**, SHA-256
`14e0c0b77e9c1626d5d83eedbfebc0082afa0a7550c6738e65d027b2f1e1540b`.
Apply after30 preceding layers. Accepted compiled files and all worlds remain
unchanged. Explicit authorized JSON/privacy/PNG checks and complete base/target/
archive/composed integrity pass in4.082055s:exactly5changed files,1,271 composed
files. All39 scenes and earlier observations are retained. This report-only target
retains all prior inert compiled assets; it does not replace the full39-scene catalog
with the accidentally created local sample-only package. Evidence stays under
`data/validation/fly-mobile-detail-20261107/publications/report-evidence/`.

Clearance pointer `f7b16eaa821e2e3f5c9917a80dbcd6568ef3cef3` deploys as
`45d4c7a1-db85-424f-afa3-9401797dd83f`: created2026-11-07T01:32:14.863Z,
**SUCCESS** at01:35:18.509Z. Anonymous archive readback passes in0.827319s.
All6 changed public sizes/SHA-256 values match in6.654712s; root HTML SHA-256 is
`5fb77b6ede58a34ba633dd4382065fa357f1a8aef58ee1bbb9207fc6e72c1c13`.
Actual public Fly checks begin after this confirmation; public refinement follows
once that headed browser closes, avoiding concurrent GPU/input interference.

Provisional evidence pointer `33d194932022a479166c51e3e3a18f4b108ab939` deploys as
`d56187f2-51b2-4932-8d47-f43bd0813c15`: created2026-11-07T01:35:13.615Z,
**SUCCESS** at01:41:42.817Z (6min29.202s). Build/image push completed earlier,
but the container-start stage remained pending with no app logs. A bounded60-poll
public-readiness check fails before the rollout finishes; the exact pending/timeout
evidence is retained. Environment inspection reports0 warnings/criticals and0 recent
failures, exposing no underlying startup cause. A fresh post-SUCCESS readback then
verifies all5 exact public file sizes/SHA-256 in12.835168s. Anonymous complete
archive readback passes in1.514465s. The deployment delay is not a browser/quality
PASS or an invented app failure; core clearance remains available during the wait.

A two-JSON increment immediately records actual core public Fly/LoD **6/6PASS**,
keeping dedicated report-browser checks explicitly **NOT RUN** pending execution.
Release `viewer-lod-detail-verified-2026-11-07`, archive
`groundshift-lod-detail-verified-20261107.tar.gz`: **14,769 bytes**, SHA-256
`3379a9c32e88fb006fcc5b92e510ad623ebede6a7e9b83e824a8c884a53b47a7`.
Apply after31 preceding layers. JSON/privacy and base/target/archive/composed
integrity pass in6.147005s; exactly2JSON files change,1,271 composed files retained.
The accepted production build,all39 worlds,the3new comparison PNGs,source images
and all previous observations remain unchanged. Evidence stays under
`data/validation/fly-mobile-detail-20261107/publications/verified/`.

Core-status pointer `2346527975e645f851829a7b1191ab83fe4dd9db` deploys as
`59c687ac-1563-4435-9fcb-6e5fbda7600b`: created2026-11-07T01:45:59.142Z,
**SUCCESS** at01:46:52.546Z. Anonymous complete archive readback passes in0.673912s;
all2 changed public JSON sizes/SHA-256 match in0.897086s. A fresh ordinary32-layer
restore verifies all archive SHA pins and every1,271 file size/hash in10.999922s,
using1,416,495,610 bytes of extracted files and0 additional archive download bytes.
A fresh disk-space gate sees5,189,746,688 bytes available before extraction; no
original data,evidence or rollback archive is removed.

The final one-JSON increment records actual dedicated report-browser **2/2PASS in
14s** and preserves two earlier5s network-wait timeout FAILs. The30s wait correction
changes only the test allowance; report/app content remains unchanged. Together
with the6core cases, all8 distinct final public cases have passing evidence.
Release `viewer-lod-report-verified-2026-11-07`, archive
`groundshift-lod-report-verified-20261107.tar.gz`: **7,037 bytes**, SHA-256
`3eef3f791015567e37a3b3263f203e123665e1603f1d1bc1fbd1cec3937ceb4d`.
Apply after32 preceding layers. JSON/privacy and full base/target/archive/composed
integrity pass in4.490703s; exactly1summary JSON changes,1,271 composed files
retained. All39 worlds,the viewer,timeline,source imagery and3comparison PNGs stay
byte-identical. The final ordinary check is **NOT RUN** at dispatch. After dispatch, applying
the last layer to the same tree that began as a fresh empty32-layer restore and
rechecking every final file **PASS**:33 archive SHA pins and all1,271 file sizes/
hashes. The last layer plus complete file recheck takes2.027580s, following the
10.999922s initial32-layer extraction/check. No second bulk copy or download is
used. Evidence is retained in `ordinary-restore-33.json`.
No repeat GPU/browser suite is implied by this status-only publication. Physical
phone/Safari hardware and kilometer-scale reconstruction remain **NOT RUN**;
serving recovery does not establish independent geometry or a new16-view quality pass.
Private evidence stays under
`data/validation/fly-mobile-detail-20261107/publications/report-verified/`.

Final pointer `e1c0d67a79aaf38ac3926f182e1324db0db16fa1` deploys as
`aba39123-a62d-4126-a6b4-a4146cfb24e2`: created2026-11-07T01:50:04.467Z,
**SUCCESS** at01:50:52.359Z. Anonymous complete archive readback passes in0.578187s.
The exact final public summary matches16,849 bytes and SHA-256
`98008859d2aadc6f69fe8e17482882d74b4e5026d061d073873aa36abb43a2d9`
in0.489568s. Prior compiled/world/image/timeline bytes remain unchanged from the
already executed public checks. All8 final distinct public browser cases pass,
with retained earlier failures;33 archive pins and all1,271 restored file sizes/
hashes pass. Final documentation is committed without another artifact rollout,
so Railway stays pinned to these tested bytes. Implementation is recorded by
`400e053` and final evidence/tests by`0d0724f`.

## Fullscreen Fly viewer controls — 2026-11-07

The viewer adds Fly alongside Orbit, fullscreen or viewport fallback, mobile dual
virtual joysticks, WASD/mouse navigation, vertical movement, speed, reset and exit.
This is presentation-only free movement: no collision/floor geometry is inferred,
and no reconstruction or new scene artifact is produced. All39 existing scenes,
source/pose/provenance bytes, reports and17 inert historical background files are
retained unchanged. Initial browser interaction/rendering checks are **NOT RUN**
when this increment is dispatched; the main agent continues those checks in parallel.

Release `viewer-fly-controls-2026-11-07`, archive
`groundshift-fly-controls-20261107.tar.gz`: **1,060,275 bytes**, SHA-256
`d6c36d42cd00575ffb22a5516052e26a50d920d3d9cefe9195c5467e63bf87d7`.
Apply it after the23 preceding immutable layers. A fresh production build passes
in5.77s. Explicit authorized curation and complete base/target/archive/composed
integrity checks pass in5.127121s:1,185 selected public files,6 changed compiled
assets/HTML files and1,240 composed files. No public scene/report/source-image
bytes change. Anonymous complete archive readback verifies its size/SHA in0.963741s.
Public rollout/hash/browser checks follow dispatch. Private packaging evidence
stays under `data/validation/fly-20261107/publications/initial/`.

Initial pointer `3ad95c76dc946b1818949fef3e61b0b53ace240e` deploys as
`d7a20321-7d8a-44f6-9772-7972d5322f66`: created2026-11-06T23:48:46.325Z,
**SUCCESS** at23:49:40.190Z. All6 changed public files match their exact byte
sizes/SHA-256 in3.841025s. Initial local mobile dual-touch, portrait/landscape and
release checks pass; foreground desktop actions expose a real `InvalidStateError`
when pointer capture follows pointer lock. That failed evidence is retained.
A mechanical viewer-only correction follows; rollout/hash checks do not by
themselves establish Fly interaction acceptance.

The next snapshot captures fallback dragging before requesting pointer lock and
skips capture once locked; it also clears pending Orbit damping while preserving
the current pose, focuses the canvas and retains the speed selection on re-entry.
Release `viewer-fly-capture-fix-2026-11-07`, archive
`groundshift-fly-capture-fix-20261107.tar.gz`: **1,060,355 bytes**, SHA-256
`45483b2edb661f41537c6cbdf9fd33e23ac72c645004675e10c953b16ab93db7`.
Apply after the first24 layers. Fresh production build passes in4.9s; explicit
curation and full base/target/archive/composed checks pass in9.252733s. Exactly6
compiled/HTML files change, with1,185 target public and1,245 composed files.
All39 scenes and report/photo/pose/provenance files stay unchanged. Corrected
local/public interaction checks run alongside/after dispatch and are **NOT RUN**
in the frozen initial evidence for this recovery. Evidence is retained under
`data/validation/fly-20261107/publications/capture-fix/`.

Recovery pointer `273ef01c84b183cd4855745d467cdee5ea22c174` deploys as
`0e8ab334-83e2-4807-bd3b-0a7a6553044f`: created2026-11-06T23:51:47.139Z,
**SUCCESS** at23:52:39.081Z. Anonymous full recovery archive readback verifies its
size/SHA in1.829811s. All6 changed public files match exact sizes/SHA-256 in
3.996561s, including the new index SHA-256
`ae792e3d3e26bf6e748189f9f5654bdce8a44d654952b19ebc9d6f766a1444cd`.
Fresh ordinary extraction of all25 immutable archives verifies every archive
SHA and all1,245 composed file sizes/hashes in10.034810s. This restoration retains
all39 scenes and the17 inactive historical background files; it does not rerun
reconstruction or establish new geometry/streaming quality.

Post-recovery actual public-browser checks **PASS3/3 in27.5s**: native desktop
fullscreen/pointer lock, WASD/mouse/reset/Orbit handoff; mobile dual-touch in both
orientations; and the no-pose sample under forced pointer-lock denial using drag
fallback. Actual screenshots are inspected. These checks do not assert collision
or recovered navigation surfaces. Inspection identifies touch-target and help-text
layout refinements; the next viewer-only increment preserves this passed evidence.

The third viewer increment makes mode buttons44px touch targets, moves desktop
help clear of lift controls, corrects the navigation group label and keeps Exit
Fly available after rendering failure. Release
`viewer-fly-ui-recovery-2026-11-07`, archive
`groundshift-fly-ui-recovery-20261107.tar.gz`: **1,060,362 bytes**, SHA-256
`028f4272ef68c8756312a0a20ea8fe53b96e811620d2afe6d880bec928c99f43`.
Apply after the first25 layers. Fresh production build passes in3.38s; explicit
curation and full base/target/archive/composed checks pass in5.439686s, with6
compiled/HTML changes,1,185 target public files and1,250 composed files. All39
worlds and all report/source-image/camera/provenance bytes remain unchanged.
R3 public interaction and actual context-loss checks are **NOT RUN** at dispatch;
R2 passed runtime evidence remains preserved. Private publication records stay
under `data/validation/fly-20261107/publications/ui-recovery/`.

Third viewer pointer `76680889784db07885b7fb2bfcce2585098441da` deploys as
`21106896-4152-4a9c-965c-f6bc725bfc76`: created2026-11-06T23:58:04.666Z,
**SUCCESS** at2026-11-07T00:00:32.046Z. Anonymous full archive readback verifies
size/SHA in1.723770s. All6 changed public files match exact sizes/SHA-256 in
3.712296s; final root HTML SHA-256 is
`39850adc602922f126b07cca4a32118b20d32693bb3941c3b70bb835b1a60c7c`.
Fresh ordinary extraction verifies every one of26 pinned archives and all1,250
composed file sizes/hashes in12.440227s. All39 scenes and17 inactive historical
background files remain preserved; no source HD/model weights/private logs ship.

Final frozen-package browser checks pass4/4 in37.7s, including the camera-path
regression and actual forced WebGL context-loss, Exit Fly and Retry recovery.
TypeScript, lint and212 JavaScript tests pass. Physical iPhone/Safari and Android
hardware remain **NOT RUN**. Viewer movement uses world-unit heuristics and has
no collision/floor/metric-speed guarantee. See [Fly usage and retained failures](FLY.md).

The third public Fly run records2PASS/1FAIL in34.4s: desktop/native input and
mobile dual-touch pass, but the sample's forced context-loss recovery exposes a
pending Spark-owner lifecycle failure. The failed screenshot/trace/log is retained
under `data/validation/fly-20261107/browser-public-final/`. Local recovery passing
does not override this public failure. A fourth mechanical increment disposes the
Spark renderer owner immediately after stopping animation on error, so pending
jobs observe a disposed owner before Retry. Its corrected public behavior is
**NOT RUN** until freshly exercised.

Lifecycle recovery release `viewer-fly-lifecycle-fix-2026-11-07`, archive
`groundshift-fly-lifecycle-fix-20261107.tar.gz`: **1,058,517 bytes**, SHA-256
`607d60c095a32b64cf0c48fafa7262729cc81ec06899c2910e7b20281846a9c1`.
Apply after the first26 layers. Fresh production build passes in3.92s; explicit
curation and base/target/archive/composed integrity checks pass in12.394072s.
Only5 compiled/HTML files change;1,185 target public and1,254 composed files.
All39 scenes, reports, sources and camera/provenance bytes remain unchanged.
Corrected interaction checks run independently after this dispatch. Publication
evidence remains under `data/validation/fly-20261107/publications/lifecycle-fix/`.

Lifecycle pointer `fb944e02d6433363f923f1c71fb9d64d7d3c6644` deploys as
`07e2520b-e38c-4344-aee9-a91a4bb13983`: created2026-11-07T00:08:27.785Z,
**SUCCESS** at00:09:24.843Z. Anonymous complete archive readback verifies its
size/SHA in1.345970s. All5 changed public files match exact sizes/SHA-256 in
3.523859s; root HTML SHA-256 is
`91bdab7155d8376687980fedddd1c2828f0643e680740e35ea5eb130c4e47711`.
Fresh ordered extraction verifies all27 immutable archive SHA pins and all1,254
composed file sizes/hashes in12.877001s. Every prior observation and all39 worlds
remain retained. The frozen lifecycle package passes3Fly cases in27.3s; an
additional focused forced-context-loss/Exit/Retry check passes3/3 in23.2s with no
page errors. Actual desktop/portrait/landscape screenshots are inspected, with
no overlap/overflow. Final public recovery acceptance is verified separately;
local results do not erase the retained third public failure.

Final actual public lifecycle/Fly checks **PASS3/3 in35.2s** on the unchanged
SUCCESS deployment: native desktop fullscreen/pointer lock/WASD/mouse, forced
context loss followed by Exit and Retry without page errors, and simultaneous
mobile CDP sticks in portrait/landscape with the explicit fullscreen-denial
fallback fixture. Evidence stays under
`data/validation/fly-20261107/browser-public-r4/`. Actual public desktop, portrait
and landscape screenshots are inspected with no UI overlap/overflow; the sample
evidence records no page errors and successful context-loss Exit/Retry. API-denial
fixtures and CDP mobile emulation are distinguished from real-device platform acceptance; physical
iOS/Safari and Android hardware remain **NOT RUN**. No collision, geometry or
reconstruction quality claim follows from these viewer tests. Final source/test/
evidence documentation commits are pushed without another artifact deployment;
Railway remains pinned to the tested lifecycle pointer and exact same bytes.

## Paris reconstruction and spatial serving progress — 2026-11-07

The first real pipeline result is published immediately while crop/depth and
chunk-viewer implementation continue locally. Actual fixed-rig SfM registers
144/144 perspective crops from24 physical Paris panoramas, producing8,686 sparse
points with0.5964px mean reprojection error in57.833s. This diagnostic is not
surveyed/metric geometry accuracy. This increment still marks Gaussian training,
new-scene rendering and GS lazy serving **NOT RUN**.

Release `viewer-paris-sfm-2026-11-07`, archive
`groundshift-paris-sfm-20261107.tar.gz`: **3,560 bytes**, SHA-256
`97cb6eb2b9efaf7c41323a67ccf7752db31d70ca811ba8f4effdf27268e079cc`.
Apply it after the fifteen tourist/SPZ/historical layers. Exactly one dynamic
report JSON changes. All previously built static app, scene, source preview and
camera bytes remain unchanged, so this package reuses that accepted production
build rather than compiling the in-progress chunk implementation. Privacy checks
and complete base/target/decompressed-overlay/composed size/hash checks pass for
all1,157 files in3.890945s. All36 prior worlds and observation history remain
available. Source HD data, raw local logs and weights remain local. Public
deployment/hash/browser checks run after dispatch; their status is initially
NOT RUN. Private publication evidence is retained under
`data/jobs/paris-streaming-20261107/publications/sfm/`.

Pointer `1674c8e` deploys as`6cb8cd4d-350d-4208-983b-b7ca83b1447a`:
created2026-11-06T17:00:07.426Z, **SUCCESS** at17:03:03.408Z. Anonymous full
release readback passes in0.569679s; the changed public summary matches all7,769
bytes and SHA-256`570f358277aec92e39f9b1a1629cbd7406832a6a682000cc22d8f77d921e4ef8`.
These checks do not assert new GS rendering or streaming.

The next incremental report records480 actual DAV2 MPS predictions in71.916s,
309 accepted and171 rejected depth calibration fits, and186,899 initialization
points. Native768px/8k-step/800k-cap training is **RUNNING**, not completed or
visually verified, while stream-viewer code is still being implemented locally.
Relative depth/calibration diagnostics do not establish metric geometry truth.

Release `viewer-paris-depth-2026-11-07`, archive
`groundshift-paris-depth-20261107.tar.gz`: **3,735 bytes**, SHA-256
`b6e9ff323696944af80eb46c5ae8ee697e56c047a291445eb9cc28a606d4af5a`.
Apply it after the sixteen preceding layers. Exactly one dynamic report JSON
changes; all accepted compiled/static/photo/GS/camera bytes remain unchanged.
Privacy and base/target/archive/composed size/hash checks pass for all1,157 files
in5.485057s. No in-progress chunk code, weights, original sourceHD or raw logs
are published. Deployment/hash/browser checks run after dispatch; evidence stays
local under`data/jobs/paris-streaming-20261107/publications/depth/`.

Depth pointer`c728ea3` deploys as`bb2094e5-6331-4dd1-a597-a41aeb4bbc68`:
created2026-11-06T17:06:44.915Z, **SUCCESS** at17:07:46.839Z. Anonymous full
archive readback passes in0.919273s. The public summary matches all8,171bytes
and SHA-256`06984a445dfa9ab191349076874588fafa8d9b414835a109559543646a108e83`.
Native-render and lazy-serving evidence are still NOT RUN in this snapshot.

The actual native result is released before chunk comparisons finish. Local M2
Metal training completes8,000steps at768px with800,000Gaussians in1,018.286s.
The original PLY remains local; a15,921,380-byte full-SPZ derivative and an actual
first-view GS preview become the37th scene. The initial manifest has no streaming
field. Actual local first-view rendering passes (588,327 colored pixels); detailed
quality, chunk behavior and public rendering are still pending in this increment.

Release `viewer-paris-native-2026-11-07`, archive
`groundshift-paris-native-20261107.tar.gz`: **17,122,200 bytes**, SHA-256
`c686769695fa40399332eaef5f2171fac7e7615296b70668da505ab6f63d793d`.
Apply it after the seventeen preceding pinned layers. A fresh production rebuild
passes in2.81s; privacy and explicit base/target/archive/composed integrity checks
pass in4.452061s (1,128 selected public files,16changed files,1,168 composed).
All prior36 scenes,55 timeline entries and17inert backgroundfiles remain retained.
The first preflight catches the new publisher's noncanonical`spz-world` source
path and creates no archive. Recovery preserves that original and copies an exact
independent source snapshot under`publications/native/world`, respecting the
existing`.../world` publication contract; the fresh retry passes. Native/source
bytes and rendering are not fabricated by this metadata correction. RawHD,
nativePLY, raw logs and model weights remain local. Public deployment/hash/browser
checks run after dispatch; evidence is retained under
`data/jobs/paris-streaming-20261107/publications/native/`.

The next provisional snapshot adds six spatial SPZ chunks and a hash-pinned
index to the same37th world, with a configured nearest-three resident selection.
The full native SPZ/cameras/preview bytes remain unchanged and available as the
control. This frozen increment labels actual stream/appearance checks pending;
subsequent observations are separate evidence, never a reason to hide the trial.

Release `viewer-paris-stream-2026-11-07`, archive
`groundshift-paris-stream-20261107.tar.gz`: **15,890,880 bytes**, SHA-256
`6b861e6007e5987e0e3ac9388d29ea46010848680f2da7dbab6b7207955d62a3`.
Apply it after the eighteen preceding pinned layers. Production rebuild passes
in2.88s. Explicit metadata/privacy, referenced chunk count/size/hash and complete
base/target/archive/composed checks pass in5.579606s:1,135 selected public files,
11changed archive members,1,175 composed files. Source/geometry/GS training is
unchanged. RawHD/nativePLY/logs/weights remain local. Public deployment/hash and
actual browser behavior checks follow dispatch. Evidence is local under
`data/jobs/paris-streaming-20261107/publications/stream/`.

Native pointer`b0c83ce` deploys as`f5e08664-9156-4d45-b23d-bf579624a7c0`:
created2026-11-06T17:23:32.084Z, **SUCCESS** at17:24:30.707Z. All16 changed
public size/hash checks pass in28.025543s, including the actual full-SPZ and
preview. Anonymous archive readback passes in3.782807s. These are deployment
integrity checks, distinct from actual public GPU rendering and geometry.

Stream pointer`c6b6111` deploys as`37fcb203-5c9c-4eab-a241-c7c094755f34`:
created2026-11-06T17:26:05.036Z, **SUCCESS** at17:26:56.941Z. All11 changed
public sizes/hashes pass in10.400767s; anonymous archive readback passes in4.306502s.

The next report immediately records a concrete **appearance FAIL** for the
nearest-three subset: distant/sky coverage disappears, with33.45/255 mean RGB
error in the initial comparison view versus the full scene. Local4/4 browser
mechanics pass in11.5s, but that does not establish visual acceptability. The
report recommends the preserved whole-SPZ control while coverage-preserving
paging is investigated locally. No RAD/LoD output or success is claimed here.

Release `viewer-paris-subset-fail-2026-11-07`, archive
`groundshift-paris-subset-fail-20261107.tar.gz`: **4,071 bytes**, SHA-256
`5524ff5c9456257e4077717c9b392b0a1ea04b16fcf748328295bc494db736ba`.
Apply it after the nineteen preceding layers. Exactly one dynamic report JSON
changes; all accepted compiled viewer/native/chunk/photo/camera bytes stay
unchanged. Privacy/base/target/archive/composed integrity checks pass for
all1,175files in3.336672s. Publication status and hash readback follow dispatch;
quality FAIL remains even after successful publication. Evidence stays local
under`data/jobs/paris-streaming-20261107/publications/subset-fail/`.

Failure-report pointer`fa08dbc` deploys as`52f4f4e4-7c94-4a13-a23c-a6b3ae19c07a`:
created2026-11-06T17:28:37.718Z, **SUCCESS** at17:29:23.349Z. Anonymous full
archive readback passes in0.566749s. The changed public summary matches all9,080
bytes and SHA-256`a946ef71a5fff7fdd98c92f3187d2233507add121aa28695d1bf73f82c9022a8`.
This successful observation publication does not change its visible qualityFAIL.

The coverage-preserving alternative becomes a separate38th scene, retaining the
whole-SPZ control and naive-subset FAIL observation. Native Spark RAD/LoD keeps
coarse coverage across the scene with a350k selection budget and8-page/524,288-slot
pool. The initial actual headed local Chrome case passes1/1 in11.4s; first-view
RGB MAE is3.214/255 versus the full scene (nearest-three was33.45), and direct
inspection finds the black void eliminated. Broader directional/public checks
remain pending. First payload is14.88MB against15.92MB fullSPZ, so the first
configuration provides only a small transfer saving; it is not a strong network
scalability result. No retraining or source-photo background is used.

Release `viewer-paris-lod-2026-11-07`, archive
`groundshift-paris-lod-20261107.tar.gz`: **43,423,076 bytes**, SHA-256
`58b04a6f4f6d2e6716d7049315e42090f949d87115c90c206e5318e737e8d5d6`.
Apply it after the twenty preceding layers. The explicit public package includes
17 pinned RAD/RADC files (26.26MB), full-SPZ control, actual preview and new paging
viewer code. Fresh production rebuild passes in4.41s; privacy, referenced paging
file size/hash and complete base/target/archive/composed checks pass in5.446393s
(1,158selected public files,33changed members,1,203composed). All37 prior worlds,
failed observations and rollback packages remain retained. Public deployment/hash
and actual GPU/render checks follow dispatch. Evidence stays local under
`data/jobs/paris-streaming-20261107/publications/lod/`.

Initial LoD pointer`725a6db` deploys as`8eed0514-a768-431a-89f8-8caa2278bdd9`:
created2026-11-06T17:35:42.937Z, **SUCCESS** at17:37:04.770Z. Anonymous full
archive readback passes in13.033310s. All33 changed public file sizes/SHA-256
values pass in35.938344s, including all17 RAD/RADC files, controlSPZ, actual
preview and paging viewer code. Actual public GPU/browser results are separate
from this integrity checkpoint.

Subsequent actual public browser execution passes5/5 cases (approximately1.2min),
covering native LoD, naive eviction/retry and report/lab behavior. In the native
first view,349,915Gaussians and8pages are selected; sampled completed-file payload
is13.2265MB and first-view RGB MAE is3.166/255. This is not a complete cold-wire
transfer benchmark. A separate16-direction768px comparison fails the declared
quality screen (per-view MAE<=5 and changed-fraction<=0.10): naive subset average/
maximum35.199/76.165, native gsplat3.632/7.990, compact native csplat3.549/6.036.
Page counts remain bounded at8 with no recorded errors. Public execution PASS
and improved coverage do not override that directional appearance FAIL or prove
independent geometric accuracy. The compact alternative is published separately
when ready; no success is inferred from a local export alone.

The compact csplat/RAD alternative and measured report publish as soon as the
actual assets, four comparison JPEGs and report UI are ready, while final public
cases continue. It is a separate39th scene, preserving the whole-SPZ control,
naiveFAIL trial and initial nativeLoD world. Its17 pinned RAD/RADC files total
25,950,408bytes, only approximately1.2% less than the initial encoding; this is
not a major transfer breakthrough. The report explicitly keeps16-direction
appearanceFAIL distinct from actual execution/public first-viewPASS.

Release `viewer-paris-compact-2026-11-07`, archive
`groundshift-paris-compact-20261107.tar.gz`: **44,427,027 bytes**, SHA-256
`a06dca766715897016322999eb71891fb47e8798d881bc74f7c5f35c790bc226`.
Apply it after the twenty-one preceding pinned layers. A fresh production rebuild
passes in3.65s. Metadata/privacy, all declared paging-file pins and complete
base/target/archive/composed size/hash checks pass in11.321011s (1,185selected
public files,37changed members,1,235composed files). All earlier worlds/reports
and rejected observations remain available. New compact public-browser checks
and final integrity readback run after dispatch. RawHD/nativePLY/logs/weights
remain local. Publication evidence is under
`data/jobs/paris-streaming-20261107/publications/compact/`.

Compact pointer`5073c1f` deploys as`39c3c14f-9e66-41f1-8888-013ee93364d2`:
created2026-11-06T17:50:29.561Z, **SUCCESS** at17:51:52.444Z. The server verifies
`/tmp/paris-compact.tar.gz: OK` and passes healthcheck. Anonymous full archive
readback passes in69.985200s; this is an attachment readback observation, not a
controlled transfer benchmark. All37 changed public sizes/SHA-256 values pass
in34.856272s. Fresh empty-directory ordered extraction verifies all22 archive
checksums and every1,235 composed file size/hash in7.617566s. Final actual public
execution cases are run separately after rollout; directional qualityFAIL stays
explicit regardless of deployment success.

Completed actual public checks are published in a final one-JSON evidence layer:
nativeLoD/report/lab3cases pass in40.8s; compactLoD1case passes in26.9s, totaling
4/4. All four report comparison images decode and public screenshots are visually
inspected. Both first views pass their local screen, while strict16-direction
qualityFAIL remains. Actual first-ready is7.4–9.6s; sampled payload progresses
13.23MB first view→21.40MB at end→29.57MB after reversing. Re-fetch demonstrates
eviction, but the roundtrip exceeds the15.92MB fullSPZ. There is **no demonstrated
58m bandwidth saving or speed advantage**, and no completed2.19km reconstruction.

Release `viewer-paris-verified-2026-11-07`, archive
`groundshift-paris-verified-20261107.tar.gz`: **5,537 bytes**, SHA-256
`91f51c0c82ec318aefb38433aaff245b2d76742d1c94f3eb4a166513ec7f2569`.
Apply it after the twenty-two preceding pinned layers. Only dynamic report JSON
changes; all accepted app/native/paging/photo/camera bytes are identical.
Privacy and complete base/target/archive/composed size/hash checks pass for
all1,235 files in4.985727s. The first local helper attempt incorrectly requires
an exactFAIL status and stops without creating an archive; it is corrected to
accept the truthful compound execution/quality labels, with no report alteration.
Final deployment, public hash and23-layer fresh-restore checks run after dispatch;
no extra app/scene tests or quality claim is inferred from this metadata layer.
Evidence remains local under`data/jobs/paris-streaming-20261107/publications/verified/`.

Final report pointer`3945e50` deploys as`c06ca903-8976-41c9-8fc3-d8df8f0bba0a`:
created2026-11-06T17:57:30.575Z, **SUCCESS** at17:58:29.267Z. Server build logs
confirm`/tmp/paris-verified.tar.gz: OK`. Anonymous full archive readback passes
in0.624014s. The changed public summary matches all12,555bytes and SHA-256
`fced7ac128f630e214532704e55c6be8c111af8ed6f3e30882f47fc243a6b9a9`.
Fresh empty-directory ordered extraction verifies all23 archive checksums and
every1,235 composed file size/hash in7.923231s. All39worlds, prior reports,
rejected observations and rollback packages remain retained. Consolidated
publication evidence is`data/jobs/paris-streaming-20261107/publication-evidence.json`;
actual GPU/render and quality evidence remains separate from these integrity checks.
The final report-only public smoke passes **2/2 in12.2s** on this SUCCESS rollout:
all four comparison images actually decode, with poster,876-source route,
24HD acquisition/private-HD404, mobile width and lab navigation checked.
Artifacts stay local under`data/jobs/paris-streaming-20261107/browser-report-final-public/`.
No additional GPU/quality success is inferred from the final JSON-only layer.
A documentation-only commit records these completed checks without another
self-referential deployment.

## Paris tourist-route source scouting — 2026-11-07

[New source report](https://groundshift-viewer-production.up.railway.app/experiments/tourist-streaming/)
provides a new licensed source route, five actual public SD panoramas and a
Strasbourg candidate preview. It is **not a Gaussian render or GS-streaming
implementation**. The first increment explicitly marks HD acquisition, new GS
reconstruction and lazy GS serving **NOT RUN**. A separate bounded local HD
acquisition continues while this report deploys.

The selected single capture sequence contains 876 consecutive rank808–1683
Panoramax images, with all875 provider previous-image links confirmed. Its GPS
polyline is approximately2.185km (median spacing2.53m, maximum3.23m); these are
source-position priors, not surveyed geometry or full camera extrinsics.
Published source previews retain Open Licence2.0 attribution to Immergis pour la
Ville de Paris / Panoramax IGN, and Eurométropole de Strasbourg for the candidate.
Source HD images and raw acquisition logs stay local.

Release `viewer-tourist-source-2026-11-07`, archive
`groundshift-tourist-source-20261107.tar.gz`: **1,499,174 bytes**, SHA-256
`09c91393bd069225e82b03bec77d8528b191952272d73d571fef2a009231522c`.
Apply it after all thirteen SPZ/historical layers below. Production rebuild
passes in2.92s. Explicit packaging verifies all1,122 selected public files,
13changed archive members and all1,155 physically composed files in3.913488s.
All36 existing worlds, the previous18reports and17inert backgroundfiles remain
preserved; the new source report is the nineteenth. No scene/model/viewer runtime
is changed. Public deployment/hash/browser checks are initially NOT RUN and
execute after dispatch. Evidence remains local under
`data/jobs/tourist-streaming-20261107/publications/source/`.

The source pointer `4b88c82` deploys as
`88dbde1f-c2c2-4c9e-8ad0-f80577facc1b`: created
2026-11-06T16:41:12.616Z, **SUCCESS** at16:42:34.011Z. Anonymous full release
readback passes in1.181313s. All13 changed public file sizes/SHA-256 values pass
in7.626873s. Fresh empty-directory ordered extraction of all14 pinned archives
reproduces all1,155 composed files in4.957429s. The server verifies
`/tmp/tourist-source.tar.gz: OK`. Actual public report/browser interaction checks
remain separate from these publication integrity checks and new GS/streaming
remain NOT RUN.

The bounded HD-acquisition increment is published as soon as the actual source
window and sanitized evidence are ready. Local acquisition obtains24 consecutive
ranks988–1011 (approximately58.02m of source GPS path),202,545,787 bytes,
12,288×6,144JPEGs, in249.668572s. Those HD images remain local. The public
increment contains only sanitized acquisition IDs/dimensions/size/SHA evidence,
updated route/summary/timeline and a compact report metric/link. New Gaussian
reconstruction and GS lazy serving remain **NOT RUN**.

Release `viewer-tourist-acquired-2026-11-07`, archive
`groundshift-tourist-acquired-20261107.tar.gz`: **99,199 bytes**, SHA-256
`05e46898feacbaa0f3070f356d74d94e314a89c09262df8b943ea43de32e89d1`.
Apply it after the fourteen preceding pinned archives. Explicit packaging
verifies all1,123 selected public files, six changed overlay members and all1,157
composed files in3.936477s. Existing worlds, source preview JPEGs and prior
observations remain byte-identical. The production rebuild passes in4.44s.
Acquisition pointer `0a61b81` deploys as
`db32ae29-a46f-4e51-aab6-4b532656e785`: created
2026-11-06T16:47:53.583Z, **SUCCESS** at16:49:02.409Z. All six changed public
file sizes/SHA-256 values pass in5.269376s. Anonymous full release readback passes
in0.702133s. Fresh empty-directory extraction of all15 pinned archives reproduces
all1,157 composed sizes/hashes in4.948135s. Server build logs confirm
`/tmp/tourist-acquired.tar.gz: OK`. Raw source downloads and logs remain outside
the archive. The final actual headed public Chrome156.0.8078.81 run passes
**2/2 in9.5s**, checking HD24/202.5MB, all24 route hash pins, actual SD decoding
and selection, the876-point polyline, lab navigation, no canvas/GS requests,
zero page errors and mobile width. The private HD probe returns HTTP404 with no
source-image bytes. Screenshot inspection passes. The local follow-up passes
2/2 in4.0s; the initial test incorrectly expecting404 from Vite's local HTML
fallback fails and remains preserved, then its explicit HTML assertion passes.
These are report/source-presentation checks, not GS reconstruction or streaming.
Raw browser evidence is local under
`data/jobs/tourist-streaming-20261107/browser-public-acquired-r2/`; consolidated
publication evidence is `data/jobs/tourist-streaming-20261107/publication-evidence.json`.
The final documentation-only commit records completed checks without another
self-referential metadata release.

## Conservative SPZ storage observation — 2026-11-07

[PLY/SPZ observation](https://groundshift-viewer-production.up.railway.app/experiments/compression/)
· [SPZ derivative](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-tangent20-spz/world.json)
· [Preserved PLY](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-tangent20/world.json).

The first increment publishes the locally converted 15,936,671-byte SPZ v3
before actual rendering and quality comparisons finish. Those visual checks are
explicitly **NOT RUN** in this package. It preserves all 800,000 Gaussians,
SH1, camera metadata and coordinate transforms; it performs no retraining,
point pruning or background completion. Numeric quantization is lossy, and
structural/position diagnostics do not establish perceptual equivalence.

Release `viewer-spz-export-2026-11-07`, archive
`groundshift-spz-export-20261107.tar.gz`: **17,025,655 bytes**, SHA-256
`744e31f5f78825b54ea69456d8f2561e4f023a4b348111f25274e677bf8e7b7d`.
Apply it **after all ten** GS-only layers below; the separate Docker stage/COPY
preserves historical worlds, prior evidence and rollback releases. The explicit
package contains 1,104 public files, and the actual composition contains 1,137
including superseded compiled assets. All target/base files, 19 changed overlay
members and physically composed files pass local size/hash checks (4.177746 s).
The 17 inert historical background files remain preserved with no active
reference. Production build passes (2.56 s); fuller checks run asynchronously.

Publication evidence remains local under
`data/jobs/street-spz-20261107/publications/export/`. This archive contains only
selected public `www/` files; source footage, private inputs, absolute paths,
raw logs, weights and credentials are excluded. Public deployment/hash/browser
checks are initially NOT RUN and run after dispatch.

The initial pointer `d012732` deploys as
`e07261b0-9a5c-4c80-bdbe-33ed19562a84`: created
2026-11-06T16:04:41.919Z, **SUCCESS** at 16:06:04.332Z. Anonymous full
release readback passes in 5.211508 s. All 19 changed public file sizes/SHA-256
values pass in 15.152270 s, including the 15,936,671-byte SPZ. The server build
confirms `/tmp/spz-export.tar.gz: OK`. Fresh empty-directory ordered extraction
of all eleven pinned archives reproduces all 1,137 composed files in
5.127376 s. Actual public-browser rendering is still NOT RUN at this integrity
checkpoint; later evidence is recorded separately from export/HTTP checks.

The measured-evidence increment follows without waiting for public browser
verification to finish. It adds four actual PLY/SPZ comparison figures, an actual
49-frame side-by-side motion video, the actual SPZ preview and sanitized
measurement/catalog/timeline JSON. PLY/SPZ, poses, transforms and compiled viewer
bytes are unchanged. Release `viewer-spz-measured-2026-11-07`, archive
`groundshift-spz-measured-20261107.tar.gz`: **9,590,436 bytes**, SHA-256
`5750e201747c383f8237e791ff7b25be37e61c65fc41584eee13061f26edfcc5`.
Apply it after the eleven preceding layers. Explicit packaging verifies all
1,109 selected public files, nine changed archive members and all 1,142 physically
composed files in 3.524377 s. Production rebuild passes in 2.71 s. Localhost
origin URLs in the first proposed summary correctly fail the publication guard;
no archive is created for that attempt. The publisher now redacts those origins
and rejects loopback URLs reproducibly, then the fresh package passes. Actual
appearance findings are recorded in the report, separate from publication checks.
The measured pointer `fb7bc0b` deploys as
`9b424e49-7ecb-4517-b0d9-e743be0d9fe1`: created
2026-11-06T16:12:00.382Z, **SUCCESS** at 16:12:52.371Z. Anonymous release
readback passes in 3.262482 s, and all nine changed public file size/hash checks
pass in 8.645668 s. Fresh empty-directory extraction of all twelve archives
reproduces all 1,142 composed files in 4.595505 s. Actual public measured-report
verification continues separately; these checks do not assert geometry or
another full browser suite.

Completed public export checks and measured-report observations ship in a final
metadata-only overlay: release `viewer-spz-verified-2026-11-07`, archive
`groundshift-spz-verified-20261107.tar.gz`, **26,070 bytes**, SHA-256
`7ec943885054826b1dc5e62722868ba85c4c73e8f915e7274eb886837b3c5600`.
Apply it after the twelve preceding archives. Exactly three JSON files change:
summary, timeline and the reproducible evaluation-camera configuration. Native
world assets/poses/transforms, compiled viewer, preview, comparisons and movie
remain byte-identical. The explicit target has 1,110 public files; the actual
composition has 1,143 including inert superseded bundles. Every local target,
base/archive and composed size/hash passes in 3.576246 s. Current full rebuild
passes; no additional reconstruction, model evaluation sweep or geometry claim
is introduced. Final pointer `2df7875` deploys as
`910b6065-f924-4d03-b75a-783951562e6d`: created
2026-11-06T16:17:26.731Z, **SUCCESS** at 16:18:11.856Z. All three changed
public file sizes/SHA-256 values pass in 1.751347 s. Anonymous full release
readback passes in 0.949417 s. Fresh empty-directory extraction of all thirteen
pinned archives reproduces every one of the 1,143 composed file sizes/hashes in
4.490582 s. Server build logs confirm `/tmp/spz-verified.tar.gz: OK`.
The final actual public-report case passes **1/1 in 9.8 s**: all four comparison
images, mobile layout, lab discovery/report links and decoded movie-frame change
from media time 0.2 to 2.3 s are checked. The earlier actual scene/interaction
and matched-render evidence remains unchanged by these three JSON files. This
metadata release does not imply another full GPU or growing browser-suite run.
Final browser evidence stays local under
`data/jobs/street-spz-20261107/browser-public-final/`; the consolidated three-phase
publication evidence is `data/jobs/street-spz-20261107/publication-evidence.json`.
The final documentation-only commit records checks without publishing a fourth
self-referential metadata release.

## Current GS-only display — 2026-11-07

The user rejects the panorama/depth-shell background completion because it
misaligns during horizontal translation. The current viewer removes its
controls, loading and rendering. `street-tangent20/world.json` omits the
background reference. Its PLY, camera poses, coordinate transform, preview and
source license are byte-identical; no new inference or training is run.
Historical background comparisons and all prior releases remain available as
rejected UX evidence. Old files in the immutable layers are not enabled views.

The user observes that the wider angular GS coverage feels more immersive.
This subjective observation is recorded separately from the earlier six
horizontal held-view RGB errors, which still favor `street-final-hires` for
photographic matching. Those errors did not measure full-sphere immersion.
Both GS scenes remain available; this display removal changes neither model.

The ninth overlay is released immediately after the production build, explicit
public content and basic integrity checks. Public verification is initially
**NOT RUN** and then runs after dispatch while local checks continue. The first
deployment `72ebfada-8097-463b-b1a4-9395279ed533` reaches SUCCESS at
2026-11-06T15:28:28.821Z (created 15:27:02.230Z; pointer `2804c07`).
All 21 changed public file hashes pass. Actual headed public Chrome 4/4 cases
pass in 152.619449 s,0skipped/flaky/failed. Two actual GS cases render 993,176
colored pixels each, translate and look up/down, with 0 background requests and
0 page errors. Only the retired metadata reference is a fixture in one case;
the Gaussian bytes and poses are actual. The current local targeted 8/8 cases
pass in 42.965094 s; 180 JS tests, typecheck and lint pass. Full current 80-case
browser rerun, independent geometry and unrestricted walking are NOT RUN. An initial build
caught an obsolete Retry-button background setter; it is removed and the fresh
production retry passes (Vite 2.67 s). The failed log is preserved. A premature
package attempt against old dist stops at an integrity assertion and emits no
archive; the successful package uses the completed fresh build.

Release `viewer-gs-only-2026-11-07`, archive
`groundshift-gs-only-20261107.tar.gz`: **1,073,680 bytes**, SHA-256
`41683c73ac684d7367bac8df1ac651e7534f26921122ff818dea6675db4a4697`.
Apply it after the eight archived layers below. The restoration command in
that section includes this GS-only override before it copies public files.

An actual fresh empty-directory extraction of all nine local immutable archives
reproduces every 1,122 composed file and hash: **PASS, 4.836610 s**. Anonymous
full attachment readback also passes (1,073,680 bytes, 2.184168 s). The explicit target has 1,095
files, including the exact 17 unreferenced historical background files retained
from the preceding pinned inventory. The actual composition has 1,122 files;
27 superseded compiled files remain inert. All composed files match size/hash
on disk and the decompressed overlay matches 21 changed files. This is not a
fresh network readback of the full surface or a geometry acceptance claim.

The completed checks ship immediately in a tenth, metadata-only overlay:
release `viewer-gs-only-verified-2026-11-07`, archive
`groundshift-gs-only-verified-20261107.tar.gz`, **12,406 bytes**, SHA-256
`d708a008e31932fd1d03a775c64ba7e0e95822b75ad9bbe900490facf8214ca8`.
It changes exactly the summary and timeline JSON, preserving all viewer,
photo, native GS, poses and historical background bytes. Deployment `68d0656a-1a63-4387-ba51-edf86c8bce43` reaches SUCCESS at
2026-11-06T15:35:20.933Z (created 15:33:50.894Z; pointer `654cec2`). The server
checks the archive checksum. Both changed public hashes pass; anonymous full
attachment readback passes in 1.838428 s. A fresh public report case passes 1/1
in18.184869s. Fresh empty-directory extraction of all ten immutable
archives matches all 1,122 composed files in 4.919464 s. Later metadata does not
change any compiled viewer, scene, camera, photograph or background bytes;
it does not imply another full GPU or 80-case rerun.

The publisher now rejects stale `backgroundDir` inputs and always strips an
inherited background reference rather than silently reactivating it. The
existing native export, poses, preview, source license and prior best world
are checked byte-for-byte. Current private evidence is under
`data/jobs/street-gs-only-20261107/`; archives contain only selected public
`www/` assets, without raw logs, original footage, weights or credentials.

## Tangent directions and explicit backgrounds — historical bounded run

The following records the original execution and retired background modes.
Current controls/loading/rendering are removed by the GS-only update above;
photographic matching and user-reported full-sphere immersion are distinct.

[Results and limits](https://groundshift-viewer-production.up.railway.app/experiments/tangent-background/)
· [New observed 3D](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-tangent20/world.json)
· [Retained best 3D](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-final-hires/world.json)
· [Protocol, actual execution and evidence](TANGENT_BACKGROUND.md).

35 Gaussian scenes, 17 reports, 52 chronological entries. The user explicitly
reopened **one** 20-direction/cropped-depth/background combination after the
previous campaign. Its **six-horizontal-view photographic matching screen
fails; street-final-hires remains the photo reference**. 300 matched actual GS-only renders show
held-view RGB MAE 24.414430→26.202616 at 512 output and 24.344902→25.980609
at 1024 output, with 0/6 directions improving at either size. Historical
background controls worked, but visual completion was limited and nadir/opaque
artifacts remained. The later user observation and removal are recorded above.
Independent geometry and unrestricted walking remain NOT RUN. No further
same-data configuration search or training followed the negative result.

Publication starts with a plan, then actual inputs during MPS inference, actual
calibrated depth during Metal training, the native world during matched renders,
and measured comparisons during the full local browser run. Full validation is
never a prerequisite for these observation releases. Every earlier scene/report
and immutable phase release remains retained.

| Increment | Pointer | Railway deployment | Created UTC → SUCCESS UTC, 2026-11-06 |
|---|---|---|---|
|Plan, explicit NOT RUN stages|`b33e697`|`f6879798-f8da-4fbf-911d-9f655710aa7c`|14:13:33.558→14:19:03.691|
|Actual 20-direction crops during MPS inference|`e80df0f`|`99e39d04-45ed-4579-87eb-34c13829f53f`|14:20:49.173→14:22:06.107|
|Actual calibrated depth during Metal training|`4531243`|`290d191b-3a0a-4f58-9af1-77a10e68d57e`|14:25:08.882→14:30:26.879|
|Optional-background resource cleanup|`8c2cf12`|`ed7ee100-286f-45d1-b42a-68588fe0cc6a`|14:34:04.400→14:35:57.592|
|Actual native scene and background assets|`71aacbe`|`aed1ec83-b2cc-4934-838b-453dbe48e625`|14:45:48.791→14:47:02.589|
|Measured regression while local suite runs|`98645e2`|`4a97c19c-7213-4740-af61-ae703e04eab6`|14:49:49.558→14:51:32.172|
|Actual background limits and mobile repair|`46aa349`|`8260dfd4-ebad-40ad-8708-a9d0f31ec69d`|14:58:35.908→14:59:23.562|
|Verified status; actual results first|`50dd8c5`|`41cf2731-9060-487f-9d67-d80442906a14`|15:04:10.076→15:04:50.959|

The actual native run finishes at 14:42:37.359 UTC, after 1188.250442 s. Native packaging
begins as soon as export, background assets and the first actual preview are
ready, while 300 GS-only renders/measurements continue. The full local browser
suite runs for 243.164141 s; the measured-evidence deployment is dispatched during
that run. The native and later packages retain the exact 73,600,652-byte
800,000-Gaussian PLY with SHA-256
`b9213464d654d8fbda1721a1a86415fa4670cb50c4b9ce5107791b7906f94a3e`.
The old best world remains byte-identical.

**PASS:** production builds, TypeScript and lint; 243 distinct Python tests across
two local environments; 182 JS tests including 33 packaging cases. 79/79 headed
local browser cases pass on the immutable native package, 0 skipped/flaky/failed.
That local scope includes 35 scene deep links/reloads and actual new GS/three
background modes. The fixture uses `GS_EXPECTATION_ROOT` to pin its expected
summary to the immutable served package while publication continues.

**PASS:** one targeted headed public Chrome 156 actual scene case in 31.040908 s
checks GS-only default, no background image/mesh requests before selection,
989,694 colored pixels in an actual GS-only canvas with UI hidden, both optional
background modes, route movement and return to GS-only. Background pixels do
not count toward the GS render gate. The same-pose public captures record
clear-color-like fractions 0.3359%/0.2246%/0.2260% for GS/panorama/shell; these
are display-color statistics, not geometric completeness. Root-owned actual
four-position and up/down comparisons show remaining orange source artwork and
nonuniform dark-pixel improvement. See the report's explicitly labeled sheets.

**FAIL then PASS:** the measured report's first static public run passes 1/2;
a compact numeric paragraph expands 354 px to 501 px on a 390 px display. A scoped
report-only wrapping fix is deployed immediately; a fresh 2/2 headed public run
passes in 18.089818 s, covering mobile width, all actual images, decoded movie
frame, four metric rows, error handling and retained chronology. The initial
failure/trace is retained. Full 79-case public rerun is NOT RUN. Initial synthetic
fixture/CLI mistakes and the reproduced local-background cancellation cleanup
gap remain recorded separately from actual model execution and quality.

**PASS:** public changed-file size/SHA checks cover 13/32/17/7/67/17/9/2 files
across the eight phases. This is incremental readback, **not** a fresh network
readback of all 1,117 files. Every composed file is verified on disk. All release
attachments are read back anonymously with the same full-byte checksums.
Final server logs confirm `/tmp/tangent-verified.tar.gz: OK`; service SUCCESS
and a fresh public report case (1/1 PASS in 12.685574 s) are checked after dispatch. The final 12,479-
byte overlay changes exactly two JSON files. It reorders existing references so
actual GS 512/detail/route/offpath and two background sheets appear before input/
depth diagnostics; every image/movie/compiled-code/scene/background byte is
unchanged. Three distinct targeted public cases have passing evidence; later
metadata-only inspection does not imply another full GPU run.

### Current 39-world restoration

Apply the four immutable final-quality layers in the preceding campaign's
restoration table, followed by these **four** tangent layers, the two GS-only
layers, the three SPZ layers, the two tourist-source layers and the eight Paris
reconstruction/paging layers and the nineteen viewer/observation updates, in order. The command below includes all forty-two
layers for the current surface. The complete native overlay supersedes
the earlier tangent plan/input/depth/viewer overlays; those early archives remain
available for rollback but are **not** required to restore the final surface.

| Layer | Release / archive | Bytes | SHA-256 |
|---|---|---:|---|
|5·native and selected background assets|`viewer-tangent-native-2026-11-06` / `groundshift-tangent-native-20261106.tar.gz`|88,819,810|`8c09b353a96551ea5fa7eab357ebe67bc61961b0237858fbee5aa94e8ed306da`|
|6·actual measured comparisons/movie|`viewer-tangent-evidence-2026-11-06` / `groundshift-tangent-evidence-20261106.tar.gz`|8,979,570|`55b2e885924bb007338a56b0e5c660df242bb2ee49e478006bc3163fccc0a15b`|
|7·background limits and mobile repair|`viewer-tangent-limits-2026-11-06` / `groundshift-tangent-limits-20261106.tar.gz`|1,228,928|`d08bfc7ffd29de440870a2c8fd4b001d4c09204ed8688559fb999c4e29f71463`|
|8·verified status and results-first order|`viewer-tangent-verified-2026-11-06` / `groundshift-tangent-verified-20261106.tar.gz`|12,479|`d8de6034d83f9fb3abdd1f0a99db148a1ea1d11a244c4a4bcaea329502cc4842`|

```sh
(
  set -e
  gs_restore_dir=$(mktemp -d)
  gs_restore_layer() {
    curl --fail --location --output "$gs_restore_dir/$2" \
      "https://github.com/neocjmix/groundshift/releases/download/$1/$2"
    printf '%s  %s\n' "$3" "$gs_restore_dir/$2" | shasum -a 256 -c -
    tar -xzf "$gs_restore_dir/$2" -C "$gs_restore_dir"
  }
  gs_restore_layer viewer-model-selection-2026-11-06 \
    groundshift-model-selection-20261106-v2.tar.gz \
    cf8f223f78d4438de3f3d8cb1223269dbec983ac83066dd97263128e3a56b13d
  gs_restore_layer viewer-final-quality-export-2026-11-06 \
    groundshift-final-quality-export-20261106.tar.gz \
    a278ecd09b7c1bddf74195161e2a75d1afa1757bb6626e0e59b9b981a9440c9c
  gs_restore_layer viewer-final-quality-evidence-2026-11-06 \
    groundshift-final-quality-evidence-20261106.tar.gz \
    070d3b51b9224bd0dd9fa0815ef4be82d6c2e5f5a8e2d03e6f56083142e52abd
  gs_restore_layer viewer-final-quality-verified-2026-11-06 \
    groundshift-final-quality-verified-20261106.tar.gz \
    e3a848b1d39e3fcff330358b102de40e1d1e1ecd64ad5d9b8927cdf64a047f48
  gs_restore_layer viewer-tangent-native-2026-11-06 \
    groundshift-tangent-native-20261106.tar.gz \
    8c09b353a96551ea5fa7eab357ebe67bc61961b0237858fbee5aa94e8ed306da
  gs_restore_layer viewer-tangent-evidence-2026-11-06 \
    groundshift-tangent-evidence-20261106.tar.gz \
    55b2e885924bb007338a56b0e5c660df242bb2ee49e478006bc3163fccc0a15b
  gs_restore_layer viewer-tangent-limits-2026-11-06 \
    groundshift-tangent-limits-20261106.tar.gz \
    d08bfc7ffd29de440870a2c8fd4b001d4c09204ed8688559fb999c4e29f71463
  gs_restore_layer viewer-tangent-verified-2026-11-06 \
    groundshift-tangent-verified-20261106.tar.gz \
    d8de6034d83f9fb3abdd1f0a99db148a1ea1d11a244c4a4bcaea329502cc4842
  gs_restore_layer viewer-gs-only-2026-11-07 \
    groundshift-gs-only-20261107.tar.gz \
    41683c73ac684d7367bac8df1ac651e7534f26921122ff818dea6675db4a4697
  gs_restore_layer viewer-gs-only-verified-2026-11-07 \
    groundshift-gs-only-verified-20261107.tar.gz \
    d708a008e31932fd1d03a775c64ba7e0e95822b75ad9bbe900490facf8214ca8
  gs_restore_layer viewer-spz-export-2026-11-07 \
    groundshift-spz-export-20261107.tar.gz \
    744e31f5f78825b54ea69456d8f2561e4f023a4b348111f25274e677bf8e7b7d
  gs_restore_layer viewer-spz-measured-2026-11-07 \
    groundshift-spz-measured-20261107.tar.gz \
    5750e201747c383f8237e791ff7b25be37e61c65fc41584eee13061f26edfcc5
  gs_restore_layer viewer-spz-verified-2026-11-07 \
    groundshift-spz-verified-20261107.tar.gz \
    7ec943885054826b1dc5e62722868ba85c4c73e8f915e7274eb886837b3c5600
  gs_restore_layer viewer-tourist-source-2026-11-07 \
    groundshift-tourist-source-20261107.tar.gz \
    09c91393bd069225e82b03bec77d8528b191952272d73d571fef2a009231522c
  gs_restore_layer viewer-tourist-acquired-2026-11-07 \
    groundshift-tourist-acquired-20261107.tar.gz \
    05e46898feacbaa0f3070f356d74d94e314a89c09262df8b943ea43de32e89d1
  gs_restore_layer viewer-paris-sfm-2026-11-07 \
    groundshift-paris-sfm-20261107.tar.gz \
    97cb6eb2b9efaf7c41323a67ccf7752db31d70ca811ba8f4effdf27268e079cc
  gs_restore_layer viewer-paris-depth-2026-11-07 \
    groundshift-paris-depth-20261107.tar.gz \
    b6e9ff323696944af80eb46c5ae8ee697e56c047a291445eb9cc28a606d4af5a
  gs_restore_layer viewer-paris-native-2026-11-07 \
    groundshift-paris-native-20261107.tar.gz \
    c686769695fa40399332eaef5f2171fac7e7615296b70668da505ab6f63d793d
  gs_restore_layer viewer-paris-stream-2026-11-07 \
    groundshift-paris-stream-20261107.tar.gz \
    6b861e6007e5987e0e3ac9388d29ea46010848680f2da7dbab6b7207955d62a3
  gs_restore_layer viewer-paris-subset-fail-2026-11-07 \
    groundshift-paris-subset-fail-20261107.tar.gz \
    5524ff5c9456257e4077717c9b392b0a1ea04b16fcf748328295bc494db736ba
  gs_restore_layer viewer-paris-lod-2026-11-07 \
    groundshift-paris-lod-20261107.tar.gz \
    58b04a6f4f6d2e6716d7049315e42090f949d87115c90c206e5318e737e8d5d6
  gs_restore_layer viewer-paris-compact-2026-11-07 \
    groundshift-paris-compact-20261107.tar.gz \
    a06dca766715897016322999eb71891fb47e8798d881bc74f7c5f35c790bc226
  gs_restore_layer viewer-paris-verified-2026-11-07 \
    groundshift-paris-verified-20261107.tar.gz \
    91f51c0c82ec318aefb38433aaff245b2d76742d1c94f3eb4a166513ec7f2569
  gs_restore_layer viewer-fly-controls-2026-11-07 \
    groundshift-fly-controls-20261107.tar.gz \
    d6c36d42cd00575ffb22a5516052e26a50d920d3d9cefe9195c5467e63bf87d7
  gs_restore_layer viewer-fly-capture-fix-2026-11-07 \
    groundshift-fly-capture-fix-20261107.tar.gz \
    45483b2edb661f41537c6cbdf9fd33e23ac72c645004675e10c953b16ab93db7
  gs_restore_layer viewer-fly-ui-recovery-2026-11-07 \
    groundshift-fly-ui-recovery-20261107.tar.gz \
    028f4272ef68c8756312a0a20ea8fe53b96e811620d2afe6d880bec928c99f43
  gs_restore_layer viewer-fly-lifecycle-fix-2026-11-07 \
    groundshift-fly-lifecycle-fix-20261107.tar.gz \
    607d60c095a32b64cf0c48fafa7262729cc81ec06899c2910e7b20281846a9c1
  gs_restore_layer viewer-mobile-fly-ui-2026-11-07 \
    groundshift-mobile-fly-ui-20261107.tar.gz \
    10264d84cb6989df04a21a5c22654313c9955ad18c92ff8aa1eb50226607feab
  gs_restore_layer viewer-lod-detail-refinement-2026-11-07 \
    groundshift-lod-detail-refinement-20261107.tar.gz \
    2957babd5ee4eee05b003c607a8e900a978da8078d5c13f9113944481aaeda94
  gs_restore_layer viewer-control-clearance-2026-11-07 \
    groundshift-viewer-control-clearance-20261107.tar.gz \
    fce177d808f18bf6d9e1c112f5bd5f6deaf9b111913f979f1bbbf812eeb7556d
  gs_restore_layer viewer-lod-detail-evidence-2026-11-07 \
    groundshift-lod-detail-evidence-20261107.tar.gz \
    14e0c0b77e9c1626d5d83eedbfebc0082afa0a7550c6738e65d027b2f1e1540b
  gs_restore_layer viewer-lod-detail-verified-2026-11-07 \
    groundshift-lod-detail-verified-20261107.tar.gz \
    3379a9c32e88fb006fcc5b92e510ad623ebede6a7e9b83e824a8c884a53b47a7
  gs_restore_layer viewer-lod-report-verified-2026-11-07 \
    groundshift-lod-report-verified-20261107.tar.gz \
    3eef3f791015567e37a3b3263f203e123665e1603f1d1bc1fbd1cec3937ceb4d
  gs_restore_layer viewer-safari-diagnostics-2026-11-07 \
    groundshift-safari-diagnostics-20261107.tar.gz \
    bcb1f2c28f75f623fe488f5e23824e00dcfc6017f39e386d84d37b29eca818da
  gs_restore_layer viewer-safari-worker-evidence-2026-11-07 \
    groundshift-safari-worker-evidence-20261107.tar.gz \
    784aa1bdcccc215f46d30b46cc007ea9452b3527c6336dcf4beee64a19c02e6b
  gs_restore_layer viewer-safari-worker-fix-2026-11-07 \
    groundshift-safari-worker-fix-20261107.tar.gz \
    9861fcfc0d56b739751665026dd7c71ca011b13b0519ba1a5224ab6cfec1ff94
  gs_restore_layer viewer-safari-worker-verified-2026-11-07 \
    groundshift-safari-worker-verified-20261107.tar.gz \
    6c61e70512b742cc1481e7504b2f9dab0b8f4c9871e701c4b00483979fb999f0
  gs_restore_layer viewer-paris-route-started-2026-11-07 \
    groundshift-paris-route-started-20261107.tar.gz \
    ec17cc241396b8b9ba66a946df8763e5189d3948396a9f13c56f4bffb5cd4f54
  gs_restore_layer viewer-seine-alignment-1004-1027-2026-11-07 \
    groundshift-seine-alignment-1004-1027-20261107.tar.gz \
    27d9025a187b24357ea749da7763528d2e48db19ca74036257e7a3c1f999d5e4
  gs_restore_layer viewer-seine-route-viewer-2026-11-07 \
    groundshift-seine-route-viewer-20261107.tar.gz \
    7906cf0aadbeb3925138ce1ccfdced31c882e440ae359c84baa5ec134607c731
  gs_restore_layer viewer-seine-route-ownership-fix-2026-11-07 \
    groundshift-seine-route-ownership-fix-20261107.tar.gz \
    a8a5af893f7d24a5eafb5aaa08ceaf003f3eea6fa3b17e61c7b9baa481c3daac
  gs_restore_layer viewer-seine-route-recovery-2026-11-07 \
    groundshift-seine-route-recovery-20261107.tar.gz \
    e4e829714a3406aa8c4e8573156d6543646f345fd947dfb77f2dfc65f0877dea
  mkdir -p public/worlds public/experiments
  cp -R "$gs_restore_dir/www/worlds/." public/worlds/
  cp -R "$gs_restore_dir/www/experiments/." public/experiments/
  for gs_entry in experiments/*/index.html; do
    rm -f "public/$gs_entry"
  done
)
npm ci
npm run dev
```

**PASS:** ordinary ordered extraction of all eight local immutable release
archives into an empty directory reproduces all 1,117 final file sizes/hashes in
4.440193 s. The fresh target inventory has 1,095 public files; 22 superseded compiled
files remain inert in the actual layer composition. This is not a target-only
absence proof. The separate historical/native/evidence/limits/status COPY layers
in `deploy/Dockerfile.github` merge the same `www/` paths and keep later tiny
observations from invalidating the historical 1.1 GB copy. The preceding Docker
pointer is preserved by commit `8c2cf12` and the early phase releases; no new
hosting or reconstruction service was introduced. Display restoration does not
repeat model inference or training. A fresh-source/full reconstruction rerun
of this final artifact is NOT RUN.

## Final same-data quality release — 2026-11-06

[New best observed3D](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-final-hires/world.json)
· [Actual comparisons, movie and limits](https://groundshift-viewer-production.up.railway.app/experiments/final-quality/)
· [Execution evidence and stop rule](FINAL_QUALITY.md).
34 Gaussian scenes,16 reports,50 chronological entries. Retain all previous
worlds and reports. Same-data quality tuning is CLOSED; the improved appearance
does not accept measured geometry or unrestricted walking.

Publication is incremental: actual1024px input evidence ships while training
runs; native export packaging begins while matched renders continue, with full
browser checks still NOT RUN; measured comparisons ship while the full local
browser suite is still running. Each
phase retains an immutable release and explicit pending statuses. The first
inputs-only overlay is superseded by the export overlay; it is **not** required
in the final restoration chain.

| Publication phase | Source pointer | Railway deployment | Created UTC → SUCCESS UTC |
|---|---|---|---|
|Actual inputs while native training runs|`1cca577`|`9a014c19-1c89-4c49-9a8c-a64e81407c03`|11:53:57.620 →11:55:34.595|
|Actual800k native world, quality verdict pending|`54f1531`|`0770c34a-b9b9-444c-9a8f-cc776796b336`|12:18:28.022 →12:20:17.313|
|Measured comparisons while local suite runs|`819b654`|`58cd663b-46eb-4c96-830d-54436d5016fc`|12:22:27.164 →12:23:49.102|
|Verified public-browser status, metadata only|`6d23be3`|`221b650d-f410-4fdb-b57b-22e29522b09d`|12:33:25.400 →12:35:34.006|

Native training runs11:51:18.972–12:15:34.629 UTC. Native publication preparation
starts12:16:25 while the1024 render batch continues until12:17:54; its metrics
finish12:18:15 during packaging/upload. The full local75-case browser run starts
12:21:24.989; measured-evidence deployment is dispatched during that run, without
waiting for its result. Explicit latest-branch connector triggers were used;
push-only autodeploy remains unverified.

**PASS:** server logs verify each added archive checksum. The final service
reports SUCCESS and `/healthz` returns200/`ok`. Each new release attachment is
read back anonymously with the same full-byte checksum. Post-dispatch public
changed-file checks pass19/25/12/2 files across the four phases. A complete
phase3 readback separately checks **all1,046 public file sizes/SHA-256 hashes**
in449.290s, zero mismatches; phase4 changes only two metadata files and their
fresh public hashes match. The other1,044 composed files are unchanged. Four
missing/private-path probes return404.

**PASS:**75 distinct local browser cases have passing evidence (initial74/75,
a failed paused-callback retry retained, then actual-playback corrected1/1).
Seven targeted public headed Chrome cases pass in2.0min as rounded by the CLI;
exact public-run seconds were not recorded. They cover the new actual scene's
render/path change, decoded report images/video and metrics,34 gallery previews,
mobile/error handling, chronology and shared older reports. A full75-case public
rerun is **NOT RUN**. After the metadata-only update, one fresh static public
Chrome case passes in11.318682s (Playwright stats), confirming the final phase
and published validation scope without repeating GPU scene tests. [Public new scene](evidence/final-quality-public.jpg) ·
[Final public report](evidence/final-quality-report-public.jpg) ·
[Sanitized evidence](evidence/final-quality.json). Full execution/test failures
and precise acceptance limits are in [FINAL_QUALITY.md](FINAL_QUALITY.md).

The final status overlay is10,846 bytes and changes only
`experiments/final-quality/summary.json` and `experiments/lab/timeline.json`.
It reuses the exact earlier scene, camera, comparison JPEGs, movie, metric values
and compiled code. Full geometry accuracy and unrestricted walking remain
unaccepted after successful execution, publication and browser interaction.

### Current34-world display restoration

The complete current display consists of the following immutable layers, applied
**in order**. Each archive contains only selected public `www/` files; no original ERP
photos, private footage, weights or raw native logs are restored. Explicitly
licensed comparison crops remain included with attribution.

| Layer | Release / archive | Bytes | SHA-256 |
|---|---|---:|---|
|1 · model-selection base|`viewer-model-selection-2026-11-06` / `groundshift-model-selection-20261106-v2.tar.gz`|928,736,619|`cf8f223f78d4438de3f3d8cb1223269dbec983ac83066dd97263128e3a56b13d`|
|2 · final native export|`viewer-final-quality-export-2026-11-06` / `groundshift-final-quality-export-20261106.tar.gz`|77,310,230|`a278ecd09b7c1bddf74195161e2a75d1afa1757bb6626e0e59b9b981a9440c9c`|
|3 · measured evidence|`viewer-final-quality-evidence-2026-11-06` / `groundshift-final-quality-evidence-20261106.tar.gz`|4,198,465|`070d3b51b9224bd0dd9fa0815ef4be82d6c2e5f5a8e2d03e6f56083142e52abd`|
|4 · verified public status|`viewer-final-quality-verified-2026-11-06` / `groundshift-final-quality-verified-20261106.tar.gz`|10,846|`e3a848b1d39e3fcff330358b102de40e1d1e1ecd64ad5d9b8927cdf64a047f48`|

In a fresh checkout of this feature branch:

```sh
(
  set -e
  gs_restore_dir=$(mktemp -d)
  gs_restore_layer() {
    curl --fail --location --output "$gs_restore_dir/$2" \
      "https://github.com/neocjmix/groundshift/releases/download/$1/$2"
    printf '%s  %s\n' "$3" "$gs_restore_dir/$2" | shasum -a 256 -c -
    tar -xzf "$gs_restore_dir/$2" -C "$gs_restore_dir"
  }
  gs_restore_layer viewer-model-selection-2026-11-06 \
    groundshift-model-selection-20261106-v2.tar.gz \
    cf8f223f78d4438de3f3d8cb1223269dbec983ac83066dd97263128e3a56b13d
  gs_restore_layer viewer-final-quality-export-2026-11-06 \
    groundshift-final-quality-export-20261106.tar.gz \
    a278ecd09b7c1bddf74195161e2a75d1afa1757bb6626e0e59b9b981a9440c9c
  gs_restore_layer viewer-final-quality-evidence-2026-11-06 \
    groundshift-final-quality-evidence-20261106.tar.gz \
    070d3b51b9224bd0dd9fa0815ef4be82d6c2e5f5a8e2d03e6f56083142e52abd
  gs_restore_layer viewer-final-quality-verified-2026-11-06 \
    groundshift-final-quality-verified-20261106.tar.gz \
    e3a848b1d39e3fcff330358b102de40e1d1e1ecd64ad5d9b8927cdf64a047f48
  mkdir -p public/worlds public/experiments
  cp -R "$gs_restore_dir/www/worlds/." public/worlds/
  cp -R "$gs_restore_dir/www/experiments/." public/experiments/
  for gs_entry in experiments/*/index.html; do
    rm -f "public/$gs_entry"
  done
)
npm ci
npm run dev
```

This restores the public display; it does not repeat native reconstruction.
Overlay assembly preserves the base files and verifies every target hash. Six
superseded compiled bundle files remain inert in the final assembled surface;
the current target inventory contains1,040 files, while the actual layer
composition contains1,046. Do not report a target-only absence proof. Historical
observation data remains included; no previous scene was removed.

**PASS:** ordinary ordered extraction of all four checksum-verified local release
archives into an empty directory reproduced all1,046 composed file sizes/hashes
in4.593s. This tests display restoration; a fresh-source/npm-ci reconstruction
of this current package and another native training are NOT RUN.


## Alternative-model observation release — 2026-11-06 KST

[All four new models, actual motion and comparisons](https://groundshift-viewer-production.up.railway.app/experiments/model-selection/) ·
[Incumbent DAV2 world](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-dense/world.json) ·
[New MoGe candidate](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-model-moge/world.json).
33 Gaussian scenes,15 reports,48 chronological entries. The observed conclusion
is **no clear qualitative breakthrough**: MoGe mean RGB error27.587 versus
DAV2 27.751,0.6% lower; retain DAV2. See [actual measurements](MODEL_SELECTION.md).

| Check | Actual evidence |
|---|---|
| Source implementation | `96857d4`; bounded PanDA repair `8880560`, model adapters/tests `1e70d75` |
| Deployment pointer | `1149e42a5ff78b9666f4899fdafce6aaf2fc41e8` |
| Publication-order instruction | `fce2da9`: immediate asynchronous partial publication in AGENTS/README/implementation/deployment docs |
| Release | [viewer-model-selection-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-model-selection-2026-11-06) |
| Archive | `groundshift-model-selection-20261106-v2.tar.gz`,928,736,619 bytes |
| Archive SHA-256 | `cf8f223f78d4438de3f3d8cb1223269dbec983ac83066dd97263128e3a56b13d` |
| Explicit static package | 1,019 public files /1,030,866,148 bytes; all787 previous dataset files unchanged |
| Anonymous full release download | PASS,928,736,619 bytes and identical SHA;274.420s |
| Railway | `8e189237-8508-4c91-a2e3-d4baa50ac70e`,SUCCESS at11:25:01.242UTC |
| Server build checksum | PASS,`/tmp/viewer.tar.gz: OK` at11:23:41.655UTC |
| Public health | PASS,`/healthz`200 /`ok` |
| Public browser | PASS,11 focused headed Chrome checks in2.1min; four new actual GS render/path checks, comparison video/depth,33 decoded gallery previews and shared older report regressions |
| Public file hashes | PASS,all1,019 files match /1,030,866,148 bytes in414.040s; three unshipped private paths return404 |

A deployment sub-agent committed/pushed the fresh pointer and explicitly
connected the existing repository/feature branch. No new service, cloud
reconstruction or GPU backend was introduced. The previous street release and
rollback deployment remain. Push-only automatic deployment remains unverified;
the explicit connector trigger is recorded.

The user corrected the workflow during this run: small results must publish
immediately in parallel with continuing work. This run's local checks had already
completed before that correction; do not claim they were deferred. After the
correction the deployment was dispatched while the full anonymous archive
readback remained in flight, and public verification started after SUCCESS.
Future partial results must ship before waiting for all tests or all candidates.

TypeScript/lint/production build PASS;166 JS and224 distinct Python tests PASS.
Local browser evidence covers71 distinct cases: initial70/71, then7/7 targeted
checks after serializing build/test and correcting model-history links. The
initial old-scene reload404 coincided with our package rebuild removing preview
files and is retained, not hidden. Full inference/training, failed strict loads,
PanDA cancellation/one repair, DepthMaster dependency stop and runtime confounds
are in [MODEL_SELECTION.md](MODEL_SELECTION.md).

Post-publication browser scope: an initial broad public suite recorded13 passes,
one gallery timeout and one interrupted case,56 NOT RUN. Its trace shows200
preview responses including one5.380s response beyond the5s assertion timeout.
Allow30s for public-network image decode without changing pixel/completion
criteria. The gallery retry and all ten new/shared-interface release checks pass
(11/11 in2.1min). Public evidence covers24 distinct cases in total; a complete
public71-case rerun is **NOT RUN**, not claimed. All71 distinct cases have local
passing evidence. The broader public run was stopped to focus on changed/new
surfaces rather than repeatedly downloading unchanged historical worlds.

[Actual public report](evidence/model-selection-public.jpg) ·
[Actual public MoGe viewer](evidence/model-selection-moge-public.jpg) ·
[Sanitized execution evidence](evidence/model-selection.json). Original full-res
photos, weights and raw logs remain local. DepthMaster predictions/code/weights
are excluded from the archive. Public comparison crops retain CC BY-SA4.0
attribution. No independent metric geometry or unrestricted-walking acceptance.

## Short-street reconstruction conclusion — 2026-11-06 KST

[Recommended street3D](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-dense/world.json) ·
[All seven controls, source comparisons and motion](https://groundshift-viewer-production.up.railway.app/experiments/street/) ·
[Chronological lab](https://groundshift-viewer-production.up.railway.app/experiments/lab/).
29 Gaussian scenes,14 reports,43 chronological entries. All previous outputs
remain. [Actual native evidence and limits](STREET_CONCLUSION.md): a recognizable
short route works on M2, with thin-structure ghosting and unverified unrestricted
walking/accurate geometry. Dense8k is the recommended observed result; longer
training and more filtering did not beat its mean held RGB error.

| Item | Verified value |
|---|---|
| Implementation | `0801d91e98f7aec9b84b8b65905456225a849351` (native core `3474a2f`) |
| Release | [viewer-street-conclusion-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-street-conclusion-2026-11-06) |
| Archive | `groundshift-street-conclusion-20261106-v2.tar.gz`,685,081,601 bytes |
| SHA-256 | `d84cae2eabef73c1898963a3a42a44e4f3865b7a3eda52a799d374d4c3b4ef4f` |
| Static archive | 827 `www/` files,777,890,271 bytes |
| Staged inventory | 830 files,777,890,958 bytes including three support files |
| Pointer | `da2956e74be211502e5f8115a3fd60f22ee48f97` |
| Railway deployment | `f70d833a-d15d-41c8-b23e-b4f963ea4819`, SUCCESS at08:29:24.860 UTC |
| Trigger | Explicit existing repo/feature-branch connector, no commit pin |

**PASS:** all archive members read back against the inventory;524 prior
world/report data hashes remain unchanged. GitHub's uploaded size/digest match;
a complete anonymous public download also matches in160.165s. Server-side
SHA-256 remains mandatory before image assembly. Railway logs report `/tmp/viewer.tar.gz: OK` at08:27:38.398 UTC; health is200/`ok`, and the actual seven-model public report serves the expected recommendation.

**PASS:** actual7 Metal exports and525 matched Chrome/Spark renders,166 JS
tests,217 distinct Python tests across their required environments, TypeScript,
lint and production build. All three HDR tests actually ran with the existing
HDR FFmpeg. All61 local headed Chrome checks pass in240.066s, covering all29
scenes and old reports. After moving the recommended3D action above the long
explanation,11 street checks pass again in57.6s on the final build. Actual decoded
video, matching source images/metrics, on-demand3D, path playback/free look,
mobile and labeled failure fixtures are included. Three displayed one-second
FPS samples per new scene were60 at the initial route view/1440×1000; this is
single-session UI sampling, not a controlled benchmark or the movie's6fps rate.

**PASS:** all827 public file sizes/SHA-256 hashes match (274.268s), including
all29 scene binaries/manifests,14 reports, compiled bundles and source comparison
images. Three unshipped input/log/weight-path probes return404. All20 targeted
public **headed Chrome156** cases pass in227.532s with no retries/flaky cases:
all7 new real GS worlds, decoded/seekable motion, source/metric controls,
chronological lab, mobile and9 previous report regressions. Public screenshots
of all7 new worlds and the report were inspected. Thin branches/rails visibly
streak and walls can double; a browser PASS does not approve geometry. The full
61-case suite was run locally; a full61-case public rerun is NOT RUN.
[Sanitized release evidence](evidence/street-release.json) ·
[Actual public viewer screenshot](evidence/street-public.jpg).

A tracked-source0801d91 restore plus the exact archive, isolated offline `npm ci`
(201 packages), production build and full package reproduces **all830 staged
file hashes identically**. This is display reconstruction, not another native
training run. Original photos, private footage, checkpoints and raw job logs
remain local. All103 pinned baseline hashes remain unchanged.

Rollback remains the immutable `viewer-road-third-view-2026-11-06` release,
archiveSHA `d512f227c301bfc1da6a52fcc2248c2587d5ca30e0e8677b4679fa5c91f1e11a`,
previous deployment `1e6d8e96-9e61-4ce8-8c25-dd3987a320d9`.
Automatic push-only deployment remains unverified; this explicit trigger was used.

## Third observed panorama road diagnostics — 2026-11-06 KST

[New public report](https://groundshift-viewer-production.up.railway.app/experiments/road-third-view/)
adds actual third-RGB overlays,24 deterministic real-image examples, interactive
291-old/44-new sparse triangulations and frozen-calibration comparisons.35 lab
entries:22 prior Gaussian scenes and13 reports. All earlier outputs remain.
[Native experiment and limitations](ROAD_THIRD_VIEW.md). Execution/publication
are separate from full-street geometry, which remains **NOT ACCEPTED**.

| Item | Verified value |
|---|---|
| Implementation | `4d125f280f79dd9f1a62fdb452d9b46b8bae5757` |
| Release | [viewer-road-third-view-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-road-third-view-2026-11-06) |
| Archive | `groundshift-road-third-view-20261106.tar.gz`,337,976,806 bytes |
| SHA-256 | `d512f227c301bfc1da6a52fcc2248c2587d5ca30e0e8677b4679fa5c91f1e11a` |
| Static archive | 561 `www/` files,416,556,684 bytes |
| Staged inventory | 564 files,416,557,371 bytes including three support files |
| Pointer commit | `3d8654d91782e92a7d0beaaf8c5922c772aef217` |
| Railway deployment | `1e6d8e96-9e61-4ce8-8c25-dd3987a320d9`, SUCCESS at04:29:28 UTC |
| Trigger | Explicit connector request for existing branch-backed service, no commit pin |

**PASS:** every archive member matches the curated inventory; public GitHub
re-download matches size/hash(85.075s); Railway checksum log reports
`/tmp/viewer.tar.gz: OK` at04:28:52 UTC. Health returns200/`ok`.514 prior packaged
world/experiment data hashes are unchanged; compiled HTML/bundle references and
appended lab timeline are separately updated. All103 pinned scooter/input hashes
and21 pre-execution protocol hashes remain unchanged.

**PASS:** TypeScript/lint/build, JS166 tests, Python199 distinct passes across two
environments. Three HDR checks **NOT RUN**. Nine local headed Chrome156 checks
pass(30.8s), with manual sparse-cloud/overlay/screenshot inspection. All250
selected public file sizes/hashes match(43.728s), including all12 new report
assets/entry, earlier panorama reports, compiled bundles, lab/catalog and preserved
scooter assets. Full561-file public recrawl **NOT RUN**. All nine public headed
Chrome156 checks pass(CLI rounded1.4m); real cloud/source/color/orbit/reset,
measured subsets, diagnostic images, downloads and lab ordering are exercised.
Simulated failure/race checks are labeled separately in the suite. Manual review
of public sparse-cloud/overlay/report screenshots confirms actual rendering;
this is not an accuracy acceptance gate.
[Sanitized release evidence](evidence/road-third-view-release.json) and
[public rendered cloud screenshot](evidence/road-third-view-browser.png).

Rollback remains the prior immutable `viewer-stereo-anchors-2026-11-06` release,
archiveSHA `30844c802fff4546dd14a9672e4e62b7e3534d8390ca335e14b810a65db7c0b0`,
previous deployment `b02ac482-b711-41db-90a0-f6d5451019dc`.
Automatic push deployment remains unverified; the explicit trigger above was used.
No raw source photographs, private footage, weights or raw job logs were uploaded.

## Observed road anchors and calibration — 2026-11-06 KST

[New public report](https://groundshift-viewer-production.up.railway.app/experiments/stereo-anchors/)
exposes five cloud controls and20 evidence images. It retains SIFT-only failures,
the inadequate256px stereo search and the512px correction that recovers291 road
candidates. The lab has34 entries (22 prior GS scenes,12 reports). All previous
reports/worlds remain. [Native results and limits](STEREO_ANCHORS.md).
Execution/publication **PASS**; full P2 geometry **NOT ACCEPTED**.

| Item | Verified value |
|---|---|
| Implementation | `1cd6913b91aaf749a0064448199631a70500bbf1` |
| Release | [viewer-stereo-anchors-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-stereo-anchors-2026-11-06) |
| Archive | `groundshift-stereo-anchors-20261106.tar.gz`,336,387,809 bytes |
| SHA-256 | `30844c802fff4546dd14a9672e4e62b7e3534d8390ca335e14b810a65db7c0b0` |
| Static archive | 547 `www/` files,414,570,400 bytes |
| Staged inventory | 550 files,414,571,087 bytes including three support files |
| Pointer commit | `1ca35a0c48442aece9fb5ab95a712790bd7a428e` |
| Railway deployment | `b02ac482-b711-41db-90a0-f6d5451019dc`, SUCCESS at03:12:58 UTC |
| Trigger | Explicit connector request for existing branch-backed service, no commit pin |

**PASS:** full archive readback matches every curated inventory member; public
GitHub re-download matches bytes/hash (81.225s); Railway build log reports
`/tmp/viewer.tar.gz: OK` at03:12:15 UTC. Health is200/`ok`. All236 selected public
file hashes/sizes match, including all75 new report assets/entry, earlier panorama
reports, lab, common bundles, catalog and preserved scooter assets. All332 checked
prior static experiment source files retain their hashes, excluding the appended
lab timeline. Full547-file public recrawl **NOT RUN**.

Seven targeted **headed Chrome156** public checks PASS; CLI reports **1.3min**
(rounded). This covers all five actual clouds, rendered pixels, source/camera
controls, diagnostic images, match gallery, prior panorama reports, chronological
lab and simulated-failure recovery. No public retries were required. Public
screenshots were inspected: recognizable lower scene, but crop wedges/strips and
offset layers remain. Pixel/rendering PASS is not geometry PASS. Local checks
PASS in28.2s. Full historical browser regression **NOT RUN**.

TypeScript, lint, production build,166 JS tests and190 distinct Python tests PASS;
three unrelated HDR tests **NOT RUN**. Nine new tests include a real CPU SGBM
execution on a synthetic known320px shift, separate from real-panorama evidence.
All103 baseline hashes are unchanged. New depth-model inference, pose refinement,
fusion and GS training **NOT RUN**; prior MPS predictions are reused.

Local evidence: `data/jobs/stereo-validation-20261106/` contains archive/release
readbacks, GitHub digest, Railway status/log,236 public hashes, health, no-overwrite
checks and local/public browser evidence. Matching, disparity, calibration and
raw diagnostic jobs are listed in [the experiment](STEREO_ANCHORS.md).
[Compact evidence](evidence/stereo-anchors.json). Raw1024px crops, disparity/raw
depth arrays, logs, private inputs/URLs and model weights are excluded from the
archive. The previous perspective-overlap release below remains the rollback
package. Push-only autodeploy remains unverified.

## Dense perspective coverage and overlap — 2026-11-06 KST

[New public report](https://groundshift-viewer-production.up.railway.app/experiments/perspective-overlap/)
compares four actual spherical cloud controls: level crops, level plus downward
crops, same-center disagreement filtering and the existing ERP control. All22
earlier GS scenes and prior reports remain; the lab has33 chronological entries
(22 scenes,11 reports). [Measurements and limitations](PERSPECTIVE_OVERLAP.md).
Execution/publication **PASS**, P2 geometry **NOT ACCEPTED**; fusion/GS **NOT RUN**.

| Item | Verified value |
| --- | --- |
| Implementation | `e146c8bdcc3a36b618e2171f8edc2bd15d5361fd` |
| Release | [viewer-perspective-overlap-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-perspective-overlap-2026-11-06) |
| Archive | `groundshift-perspective-overlap-20261106.tar.gz`,318,838,080 bytes |
| SHA-256 | `29c22636d18d3c197c58289c3402d8674214a3861ddf49b32d1ab7f047f6a83c` |
| Static archive | 472 `www/` files,378,434,557 bytes |
| Staged inventory | 475 files,378,435,244 bytes including three support files |
| Deployment-pointer commit | `e0febee172c5c38eda5d9d7a8211932089b3c4e2` |
| Railway deployment | `8fa29bf9-31a0-4bc7-a201-3f83f0da086c`, SUCCESS at02:29:56 UTC |
| Trigger | Explicit connector request for the existing branch-backed service; no commit pin |

**PASS:** every archive member matches the curated inventory; public GitHub
re-download matches length/hash; Railway build log reports
`/tmp/viewer.tar.gz: OK` at02:29:23 UTC. Health returns200/`ok`. All161 selected
public file sizes/hashes match (including all48 new report assets/entry, prior
panorama pages, lab, shared bundles, catalog and preserved scooter assets).
All285 prior static experiment source files checked are unchanged, excluding
the intentionally appended lab timeline. Full472-file public recrawl **NOT RUN**.

Six targeted **headed Chrome156** public checks PASS in59.1s. All four clouds
render actual colored pixels; source/camera changes and diagnostic images work;
the prior pair/one-panorama and calibration reports, chronological ordering and
simulated-error recovery remain operational. Public screenshots were inspected:
crop wedges and stretched points remain despite recognizable pavement and
objects. No public test retry was required. Full historical browser suite
**NOT RUN**. Local targeted checks also PASS (20.5s); the initial local path/test
failures and corrections are retained separately.

TypeScript, lint, production build,166 JS tests and181 distinct Python tests
across the two existing environments PASS; three unrelated HDR checks are
**NOT RUN**. All103 frozen baseline hashes remain unchanged. Actual native
inference and CPU measurements are in the experiment document.

Local evidence: `data/jobs/perspective-overlap-input-20261106/`, including archive
readback, GitHub asset/digest, download, Railway status/log, health,161 public
hashes, initial/final local and final public browser evidence. Numerical arrays,
calibration/projected holdout rows and PLYs remain in
`data/jobs/perspective-overlap{,-audited,-verified}-20261106/`; new model inference
is in `data/jobs/perspective-overlap-inference-20261106/`.
[Compact evidence](evidence/perspective-overlap.json). Original images, weights,
raw arrays and logs are excluded from the archive. The previous calibration
release below remains the rollback target. Push-only autodeploy is unverified.

## Common calibration and perspective depth — 2026-11-06 KST

The [new report](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-calibration/)
shows the original/common784 calibration comparison, actual photo feature-error
mosaics and an additional DAV2 perspective-depth control on 12 actual local MPS
inputs. High-parallax held-out median pixel errors improve from about 7px to
2.2–2.6px in that control. New displayed clouds belong to the common-fit ERP
experiment; perspective dense fusion and new GS remain **NOT RUN**.
All 22 previous GS scenes remain. The chronological lab has 32 entries: 22 scenes,
ten reports. [Measurements and limits](PANORAMIC_CALIBRATION.md).

| Item | Verified value |
| --- | --- |
| Experiment/report source | `3fee797` |
| Release | [viewer-panoramic-calibration-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-panoramic-calibration-2026-11-06) |
| Archive | `groundshift-panoramic-calibration-20261106.tar.gz`, 309,450,561 bytes |
| SHA-256 | `1e486d418be4c0391e033a2f6fd2fb43e580d34baa1f588817094d5b00dee15f` |
| Static archive contents | 424 `www/` files, 355,408,740 bytes |
| Staged inventory | 427 files, 355,409,427 bytes including three deployment-support files |
| Deployment-pointer commit | `461eb00` |
| Railway deployment | `7563f716-a903-4609-b2ef-d4325dcb60d5` — SUCCESS at 2026-11-06 00:13:47 UTC |
| Trigger | Explicit connector request for existing branch-backed service, no commit pin |

**PASS:** full local archive readback matches its curated inventory; GitHub
re-download matches byte length and SHA-256; Railway build log independently
reports `/tmp/viewer.tar.gz: OK` at 00:12:59 UTC. `/healthz` is 200/`ok`. All 113
selected new/shared public files match staged sizes/hashes, covering new and
prior panorama reports, lab, bundles, catalog and preserved scooter assets.
A full 424-file public recrawl is **NOT RUN**.

Five targeted headed Chrome 156 tests pass at the public origin in 50.5s: actual
original/common cloud pixels and controls, perspective images and numeric
tables, parallax/longitude strata, simulated 503 recovery, lab sorting and
preserved pair/one-panorama rendering. Actual public screenshots were inspected;
source-colored layers remain offset and perspective output is not a fused cloud.
Existing bounded 60-second remote asset waits were sufficient; no public retry
was needed in this release. The full historical browser suite is **NOT RUN**.

TypeScript, lint, build and 166 JS tests pass. Python discovers 175 tests in each
existing environment, skips 5/31, and executes 172 distinct tests across their
union. Three unrelated HDR/FFmpeg tests are **NOT RUN**. Thirteen new camera,
calibration and depth-conversion tests are included. All 103 frozen baseline
hashes are unchanged, and expected no-overwrite rejections preserve existing
reports. Native inference and runtime measurements are in the experiment doc.

Local evidence: `data/jobs/panoramic-calibration-input-20261106/` (release,
Railway status/checksum, 113-file hashes, health, logs and browser evidence),
`data/jobs/panoramic-calibration-20261106/`,
`data/jobs/panoramic-perspective-depth-20261106/`, and
`data/jobs/panoramic-perspective-control-audited-20261106/`.
[Compact record](evidence/panoramic-calibration.json). Original-resolution
inputs, raw arrays, weights, private URLs and local logs are excluded from the
archive. Documentation-only changes retain this release and its rollback
predecessor below. Push-triggered autodeploy remains unverified.

## Adjacent panorama depth — 2026-11-06 KST

The [two-panorama report](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-pair/)
compares actual locally inferred DA²/DAV2 clouds in the preserved fixed-rig frame.
It offers source colors, individual clouds, capture cameras, directional range/RGB
comparisons and regional limitations. All 22 previous GS scenes remain; the lab
has 31 entries (22 scenes, nine reports), newest first. [Experiment](PANORAMIC_PAIR_P1.md).
No fusion or Gaussian training occurs, and geometry is not accepted for fusion.

| Item | Verified value |
| --- | --- |
| Experiment/report source | `73e63e6` |
| Release | [viewer-panoramic-pair-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-panoramic-pair-2026-11-06) |
| Archive | `groundshift-panoramic-pair-20261106.tar.gz`, 287,123,649 bytes |
| SHA-256 | `d0000f6be2998163665c31900cbb9ae144dc160fd5d29406d09581aff008e2ac` |
| Static archive contents | 410 `www/` files, 326,969,233 bytes |
| Local inventory | 413 files, 326,969,920 bytes including three deployment-support files |
| Deployment-pointer commit | `5192031` |
| Railway deployment | `ff2b8ff3-64aa-43af-acf6-b4eeaeebad12` — SUCCESS at 2026-11-05 20:39:08 UTC |
| Trigger | Explicit connector request for the existing branch-backed service; no commit pin |

**PASS:** every local archive file matches its curated inventory; re-downloaded
GitHub release bytes/hash match; Railway build logs show `/tmp/viewer.tar.gz: OK`
at 20:38:35 UTC. `/healthz` returns 200/`ok`. All 99 selected new/shared public
files match their staged sizes/hashes, including both panorama reports, lab,
shared bundles, catalog and preserved scooter assets. A full 410-file public
recrawl and full historical browser regression are **NOT RUN**.

The first public targeted Chrome attempt failed three 5-second assertions while
cloud downloads were still pending. Its logs/traces are retained. After using an
explicit bounded 60-second remote asset wait, all three targeted tests passed:
real point-cloud pixels and controls, image decoding, delayed-response protection,
simulated HTTP503 recovery, lab ordering, and the preserved one-panorama render.
The pixel checks exclude the overlaid status-text band, and actual public
screenshots were separately inspected. Cloud offsets, stretching and partial
coverage remain; rendering PASS is not geometry PASS. No web artifact was
changed to address the test timeout.

TypeScript, lint, production build and 166 JS tests pass. Both Python environments
run 162 tests (5 / 31 skips); their union executes 159 distinct tests, including
22 new pair/sparse geometry tests. Three unrelated HDR/FFmpeg tests are **NOT RUN**.
All 103 frozen baseline file hashes remain unchanged. Large raw arrays, original
panoramas, weights and logs stay local.

Evidence: `data/jobs/panoramic-pair-20261106/` (inference/calibration/pair logs,
archive/release readback, 99-file public hashes, initial failed traces and final
public screenshots) and `data/jobs/panoramic-pair-ui-20261106/` (earlier manual
local browser inspection). [Compact record](evidence/panoramic-pair-p1.json).
Documentation/test-only updates retain this immutable archive and its rollback
predecessor below. Push-triggered autodeploy remains unverified.

## One-panorama full-sphere depth — 2026-11-06 KST

The [new P0/P1 report](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-depth/)
shows one real panorama, DA² and DAV2-Small raw-depth visualizations, explicit
SfM radial calibration, conservative masks and interactive colored point clouds.
Both models actually execute on M2 MPS; no Gaussian training occurs. The existing
22 GS scenes remain unchanged. The chronological lab now has 30 entries:
22 scenes and eight reports. [Experiment](PANORAMIC_DEPTH_P1.md) ·
[model/license findings](PANORAMIC_DEPTH_MODELS.md) · [baseline preservation](PANORAMIC_BASELINE.md).

| Item | Verified value |
| --- | --- |
| Experiment/report source | `5336744` |
| Release | [viewer-panoramic-depth-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-panoramic-depth-2026-11-06) |
| Archive | `groundshift-panoramic-depth-20261106.tar.gz`, 277,842,996 bytes |
| SHA-256 | `312eade1493ba7e289e37cad7c7d68b59c19f7a0eaf0b87e6d154054e1c53d66` |
| Static archive contents | 379 `www/` files, 311,508,601 bytes |
| Local package inventory | 382 files, 311,509,288 bytes including three deployment-support files |
| Deployment-pointer commit | `04964ab` |
| Railway deployment | `b7a76e45-d253-4dd9-b6d6-3acc36bb6a42` — SUCCESS at 2026-11-05 19:59:29 UTC |
| Trigger | Explicit connector request for the existing branch-backed service |

**PASS:** pinned archive checksum verified in Railway build logs; health endpoint
returns `ok`; all 68 selected new/shared public files match staged bytes and
SHA-256 hashes. Headed Chrome156 actually renders both models' point clouds,
switches filtered/full data, capture/overview views and point size, decodes source,
depth, range and mask images, verifies lab sorting/newest entry and opens the
preserved scooter report. Public cloud/report screenshots were inspected with
no page errors. Downloadable PLYs are ordinary colored points, not GS exports.

TypeScript, lint, build and 166 JS tests pass. Python suites each ran 140 tests,
with five OpenCV-environment skips and 31 PyCOLMAP-environment skips; 137 distinct tests
execute across their union. Three unrelated HDR/FFmpeg tests remain NOT RUN in
both environments. The 34 new spherical/calibration tests are included in that
total. The full historical browser regression suite and a 379-file public recrawl
are NOT RUN. Inference/browser PASS does not establish geometry acceptance.
Independent geometric accuracy and cross-panorama consistency are NOT RUN.

Existing baseline 103 file hashes were checked again after execution and remained
unchanged. Evidence lives under `data/jobs/panoramic-baseline-20261106/`,
`data/jobs/panoramic-depth-{da2,dav2}-20261106/` and
`data/jobs/panoramic-depth-input-20261106/`. A compact measurement record is
tracked at [evidence/panoramic-depth-p1.json](evidence/panoramic-depth-p1.json).
Raw logs, original-resolution panoramas, model weights and absolute local paths
are not in this archive. Documentation-only commits retain this release.

## Scooter without learned depth — 2026-11-05

The [new comparison](https://groundshift-viewer-production.up.railway.app/experiments/object-nodepth/)
keeps the exact nine real training image files and camera matrices, removes
learned-depth inference/calibration/fusion, and initializes from 115 triangulated
SfM object points. M2 Metal training takes 116.339 seconds for 5,000 steps and
exports 569 full / 237 object Gaussians. The observed result is strongly blurred
and stretched, with no recognizable-complete-object acceptance. Both outputs
are published unchanged. [Method and limitations](OBJECT_NO_DEPTH.md).

The catalog now has 22 scenes and the chronological laboratory has 29 entries
(22 scenes, seven reports). Previous results remain accessible.

| Item | Verified value |
| --- | --- |
| Viewer/report source | `bad9de4` |
| Release | [viewer-object-nodepth-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-object-nodepth-2026-11-05) |
| Archive | `groundshift-object-nodepth-20261105.tar.gz`, 271,912,916 bytes |
| SHA-256 | `38fdfbe601a9941e8310e29c321dacd9c4082caf3fb79128a88a5a3505d58d26` |
| Static archive contents | 359 `www/` files, 295,673,111 bytes |
| Local package inventory | 362 files, 295,673,798 bytes including three deployment-support files outside `www/` |
| Deployment-pointer commit | `95d6ce9` |
| Railway deployment | `659f40c5-1317-4979-ac79-68cf091d89cd` — SUCCESS at 12:39:36 UTC |
| Trigger | Explicit existing-service connector request for the latest branch |

**PASS:** actual local M2 Metal training, exact training image/camera equality,
TypeScript, production build, lint and 165 JS tests. Python suites each ran 106
tests, with five dependency skips in OpenCV and 31 in PyCOLMAP. Local Chrome
rendered both worlds; the report's initial comparison-image wait timed out, but
an unchanged rerun passed. These tests do not replace native execution evidence.

Railway verified the archive checksum (`/tmp/viewer.tar.gz: OK`).
**Public PASS:** all 64 selected new/shared public files match staged byte lengths
and SHA-256 values, and `/healthz` returns `ok`. Headed Chrome 156 renders both
new worlds (60 fps displayed at the sampled home views), decodes both comparison
previews, operates the original-image selector and point-cloud selector, checks
newest/oldest lab ordering and opens the previous report's new comparison link.
The public summary has nine observed images, zero generated images and zero
depth maps, with both input-equality flags true. Actual public screenshots were
inspected; no page errors occurred. FPS is a sampled UI counter, not a controlled
benchmark. The prior report and current report use the same display camera
parameters; no quantitative quality claim is made from the screenshots.

**FAIL:** this result does not achieve a recognizable complete scooter; substantial
blurring/stretched splats remain. **NOT RUN:** independent geometry accuracy,
quantitative quality comparison, full historical browser regression and an
all-359-file public recrawl. Intentionally omitted stages are not test failures.

Evidence: `data/jobs/object-no-depth-20261105/` retains input SHA records,
`training/job.json`, native logs, browser screenshots, `browser-public.json`,
`public-files.json`, `release.json`, Python logs and `railway-deployment.json`.
Documentation-only updates do not replace the deployed archive.

## Real-only scooter comparison — 2026-11-05

The [new comparison](https://groundshift-viewer-production.up.railway.app/experiments/object-real/)
removes all intermediate image generation: **nine real images, zero RIFE frames,
zero diffusion frames**. The same original-image camera solution and relative-depth
predictions are reused; nine-map fusion and 5,000-step M2 Metal training run again.
The native training takes 160.298 s and exports 46,807 Gaussians, with 43,268 in
the object selection. Both new worlds are in the 20-scene catalog, and the lab
lists 26 entries (20 scenes, six reports). [Method, control limits and evidence](OBJECT_REAL_ONLY.md).

| Item | Verified value |
| --- | --- |
| Viewer/report source | `301c4be` |
| Release | [viewer-object-real-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-object-real-2026-11-05) |
| Archive | `groundshift-object-real-20261105.tar.gz`, 266,917,532 bytes |
| SHA-256 | `16fa51ef8275314ac46111387a4814c696056d160489b5a50769fec25dbda42d` |
| Static payload | 335 files, 289,569,944 bytes |
| Deployment-pointer commit | `305426d` |
| Railway deployment | `3d43f792-2338-43d2-94d0-863e992b1b86` — SUCCESS |
| Trigger | Explicit existing-service connector request for the latest branch |

**PASS:** local M2 Metal execution, TypeScript, production build, lint and all
165 JS tests. Python tests ran in both available environments: 106 with 31 skips
in PyCOLMAP, and 106 with five skips in OpenCV. Native training is separately
proven by its actual adapter log and export, not these tests.

**Public PASS:** Railway checked the pinned archive (`/tmp/viewer.tar.gz: OK`)
and reached SUCCESS at 11:30:27 UTC. All **62 selected new/shared public files**
matched the staged byte lengths and SHA-256 values; `/healthz` returned `ok`.
Headed Chrome 156 rendered both new worlds, decoded the comparison images,
operated the nine-frame selector and point-cloud comparison, and checked lab
newest/oldest ordering. It also opened the preceding 65-frame report and its new
comparison link. The nine-frame public summary has zero synthetic records.
Actual public render/report screenshots were inspected, with no page errors.

This was a focused check after publication, not an all-335-file recrawl or rerun
of the full historical browser suite. Geometry accuracy and matched-camera
quality improvement remain **NOT RUN**. The post-run byte-equality control found
COLMAP preprocessing differences confined to the one-pixel image border;
interior pixels, original camera solution and training options matched. This
limitation is recorded in [the experiment](OBJECT_REAL_ONLY.md), rather than
calling the run a perfect pixel-identical control.

Evidence: `data/jobs/object-focus-real-only-20261105/` contains `ablation.json`,
`control-check.json`, native reports/logs, `browser-public.json`, `public-files.json`,
`railway-deployment.json` and actual screenshots. The initially misunderstood
RIFE-only trial was cancelled during pose estimation, before training; it is not
part of the result. Documentation-only updates do not replace this archive.

## Object-focused scooter observation release — 2026-11-05

The [chronological lab](https://groundshift-viewer-production.up.railway.app/experiments/lab/)
lists all 18 worlds and five reports, with newest/oldest sorting. The
[object experiment](https://groundshift-viewer-production.up.railway.app/experiments/object-focus/)
shows all 65 candidate images, relative-depth previews, original-only and
augmented point clouds, and both new Gaussian exports. The local result is
recognizable but blurred and streaked. Publication is not a quality pass.

| Item | Value |
| --- | --- |
| Viewer implementation / publication metadata | `68ab2d3` / `a3551c8` |
| Release | [viewer-object-focus-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-object-focus-2026-11-05) |
| Archive | `groundshift-object-focus-20261105.tar.gz`, 253,063,372 bytes |
| Archive SHA-256 | `40508f73cd0a87714d556cc305e21d46444eaf5eea8f0ce8ddb261025e0866d5` |
| Static payload | 300 files, 272,548,845 bytes; 18 scene entries |
| Deployment-pointer commit | `5d32ce9` |
| Railway deployment | `d3cf2adb-b133-4923-a894-63184246132c` — SUCCESS |
| Trigger | Existing-service connector request for the latest branch |

The result-first local run completed 56 whole-image MPS diffusion candidates
in 757.964 s, registered 47/65 cameras (all nine real photographs), and accepted
34 depth maps for a 93,595-point object initialization. Brush trained 5,000
steps on Apple M2 Metal in 610.514 s and exported 93,941 Gaussians; object-center
selection retained 93,101. Eighteen images failed registration and 13 registered
synthetic depth maps failed calibration. These exclusions are visible rather
than described as full registration. See [method and reproduction](OBJECT_FOCUS_EXPERIMENT.md).

Local TypeScript/build, actual Chrome rendering of both new worlds, interactive
point clouds and lab ordering passed before publication. Railway verified the
archive checksum in its build log and reached SUCCESS at 08:42:40 UTC.

**Post-publication PASS:** both new GS worlds render in headed Chrome 156 at the
public origin; their actual screenshots and the experiment page were inspected.
The image/depth selector, point-cloud display and newest/oldest lab ordering
executed without page errors. All **163 new/shared public files** matched staged
lengths and SHA-256 values; `/healthz` returned `ok`, and every lab-card thumbnail
returned HTTP 200. The shared-file check is not an all-300-file recrawl.
Lint and **165 JS tests** passed. The PyCOLMAP environment ran **106 Python tests,
31 skipped**; the OpenCV environment ran **106, five skipped**. Dependency-specific
skips are not GPU validation. The new native stages separately executed on the
actual M2 as recorded above.

The old full browser regression suite and independent geometry/comparative
quality measurements are **NOT RUN** for this release. Focused public checks
were performed after the user could already open the result. Raw evidence is
retained under ignored `data/jobs/object-focus-20261105/`: `browser-public.json`,
`public-files.json`, `railway-deployment.json`, stage reports, test logs and actual
render screenshots. This documentation update does not change the deployed archive.

## Depth-guided generated-view observation release — 2026-11-05

The [depth-guided comparison page](https://groundshift-viewer-production.up.railway.app/experiments/depth-warp/)
places three licensed real 512px crops, corrected stereo, raw and
source-consistent depth warps, the MPS inpainted image and two matched
Chrome-rendered GS comparisons side by side. The new
[Gaussian scene](https://groundshift-viewer-production.up.railway.app/?world=/worlds/beijing-depth/world.json)
is the 16th catalog entry. Its 10,000-step M2 Metal execution **PASS**ed, but
3D visual quality improvement **FAIL**ed: direction-01 MAE 38.900→39.874 and
direction-03 MAE 23.903→26.028 against withheld real RGB. The scene remains
visible because this service is an observation surface. The image-generation
pose and sparse initialization used all-image SfM, so this is an appearance
holdout, not independent geometry evidence. See [the local method,
measurements and reproduction commands](DEPTH_WARP_EXPERIMENT.md).

| Item | Verified value |
| --- | --- |
| Viewer/report source | `e8c4203` (core warp code `7c85279`) |
| Release | [viewer-depth-warp-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-depth-warp-2026-11-05) |
| Archive | `groundshift-depth-warp-20261105.tar.gz`, 204,273,508 bytes |
| Archive SHA-256 | `bc1c75ccfdbcd7cc27f5b972ac15f9eab9d7286ca9699b98a5fa6c0d3e5a3aca` |
| Static payload | 142 `www/` files, 219,096,620 bytes; 16 scene entries |
| Deployment-pointer commit | `672db60` |
| Railway deployment | `c7b440f4-ae49-43c2-98bc-6e51937e3033` — SUCCESS |
| Actual trigger | Explicit latest-branch Railway connector request; push-only autodeploy was not relied on |

**Local PASS:** TypeScript, lint, 165 JS tests, production build,
28 headed Chrome tests including all 16 scene renders and the new report.
The PyCOLMAP environment ran 106 Python tests with 31 dependency-specific
skips; the OpenCV environment ran 106 with five skips. The depth-calibrated
source warp, inpainting on MPS and Brush training on Metal executed separately.
The augmented job took 979.402 s, exported 150,000 splats in a 13,800,652-byte
PLY and logged the Apple M2 Metal adapter. Its actual two-direction Chrome
renders were inspected: geometry remained blurred or doubled and both matched
photo errors increased. Package contents passed a private-path text scan,
and each of the 142 archived web files matched the staged length and SHA-256.
The fresh GitHub release download matched the local archive length and hash.

**Railway/public PASS:** The build log verified `/tmp/viewer.tar.gz: OK`;
the new container reached SUCCESS with no pending work. All 142 public files
matched the staged byte length and SHA-256; `/healthz` returned 200/`ok`.
Five missing/private-source paths returned 404, including the local job
report, raw depth and model-weight names. All 28 public headed Chrome tests
passed in 4.8 minutes, including decoded report images, actual splat rendering
and reload of every catalog scene, gallery controls, camera paths, video
playback and error recovery. The public report screenshot was inspected.
Raw evidence is retained locally under ignored `data/validation/deployment/`
as `depth-warp-archive.json`, `railway-depth-warp-http.json` and
`railway-depth-warp-browser.json`. Successful publication does not change
the **FAIL** visual-quality or **NOT RUN** independent-geometry verdicts.

## Three-photo depth observation release — 2026-11-05

The earlier [depth report](https://groundshift-viewer-production.up.railway.app/experiments/depth-v2/)
shows three licensed observed 512px crops beside local M2/MPS relative-depth
predictions. The 15 Gaussian worlds and previous experiment reports remain
available. Depth prediction and its internal sparse-point ordering check are
**PASS**; metric depth, cross-view consistency and depth-assisted GS improvement
are **NOT RUN**. See [the local experiment](DEPTH_EXPERIMENT.md).

| Item | Verified value |
| --- | --- |
| Viewer/report source | `19c1d539f21efb79a904b8e1d239823d536da5d1` |
| Release | [viewer-depth-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-depth-2026-11-05) |
| Archive | `groundshift-depth-20261105.tar.gz`, 184,298,462 bytes |
| Archive SHA-256 | `59107b247c429ec4153f534c357711fc2410e23b8dd7eae9564261a7e8d03941` |
| Static payload | 120 `www/` files, 198,141,306 bytes; 15 scene entries and eight depth-report files |
| Deployment-pointer commit | `a43958fc1944b56d95499393c15b7aba81217a80` |
| Railway deployment | `9aa61c0c-eb21-4eab-9937-3188b04411b1` — SUCCESS |
| Actual trigger | Explicit latest-branch connector trigger; no push-triggered deployment appeared before it |

**Local PASS:** TypeScript, lint, 165 JS tests, production build and all 26
headed Chrome cases including the new six-image depth report and every actual
Gaussian scene. The available Python environments each ran 102 native tests:
the OpenCV environment had five missing-dependency skips, the PyCOLMAP
environment had 44; the actual three-image depth inference and sparse-point
check completed separately. The local archive readback matched every selected
file's exact length and SHA-256; the fresh GitHub release download matched the
local archive byte for byte. Railway's build log reported
`/tmp/viewer.tar.gz: OK` at the pinned checksum, and the service reached
SUCCESS with no pending work.

**Public HTTP PASS:** all 120 public files matched exact length and SHA-256,
`/healthz` returned 200/`ok`, and nine private/missing paths returned 404,
including depth arrays and raw inference logs. The first public headed-Chrome
depth case timed out at its 5-second image readiness assertion while the full
file crawl was running. Direct requests then returned all six images with 200,
the complete hash crawl passed, and the same public page passed after a test-only
30-second image wait. The deployed page and archive were unchanged for that
retry. The screenshot was inspected; it shows all three real photos paired with
three relative-depth maps. Evidence is retained in ignored
`data/validation/deployment/railway-depth-http.json` and the public Playwright
test output. **All 26 public headed-Chrome cases passed** in 5.5 minutes,
including actual render and reload of all 15 scenes, gallery controls, both
older reports, MP4 play/seek, camera-path controls and error recovery. The 15
public scene screenshots were inspected together in
`data/validation/deployment/depth-public-scenes-contact.jpg`; the older
Beijing scenes still visibly streak or blur. Browser success does not change
their recorded quality failures or prove a depth-assisted GS world exists.

## Two-endpoint panorama observation release — 2026-11-05

The new catalog contains **15 distinct scenes**, including both matched
10,000-step Beijing Gaussian worlds. The new
[65-frame panorama report](https://groundshift-viewer-production.up.railway.app/experiments/video-4to6/)
contains the actual 2048×1024 H.264 video, 10 selected licensed or generated
comparison images, an exploratory MPS inpaint and clear LTX **NOT RUN** status.
The previous Mapillary report remains available and now lists 79 summarized
stages. The generated-view GS renders, but its visual quality **FAILS** to
improve the real-only baseline. Publication does not change that verdict.

| Item | Value |
| --- | --- |
| Viewer and experiment source | `8e4fc0c0a9b3420aa59b9fe8a823b974a4d1c037` |
| Release | [viewer-panorama-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-panorama-2026-11-05) |
| Archive | `groundshift-panorama-20261105.tar.gz`, 182,419,689 bytes |
| Archive SHA-256 | `1d7def29ae1cf39b7cdca927fa01e4c3aacc9c834c39d36831145118cd954ab3` |
| Static payload | 112 `www/` files, 196,253,479 bytes; 15 scene entries |
| Deployment-pointer commit | `d2e94c309cc1aa30662f17f658d8d79e1b794301` |
| Railway deployment | `0caccf5b-9e98-49dc-8160-4b3f6becd544` — SUCCESS; public browser verification below |
| Actual trigger | Explicit latest-branch connector trigger; push autodeploy did not appear before triggering |

**Local PASS:** TypeScript, lint, 165 JS tests, production build, 25 headed
Chrome tests (including all 15 actual scene renders and MP4 playback), and
native adapter tests in the available dependency-specific environments. Both
new Brush jobs ran 10,000 steps on the M2 Metal adapter and exported distinct
13,800,652-byte PLYs. The 65-frame RIFE/MLX video ran locally; LTX-2.3 video
diffusion was **NOT RUN** because model acquisition was impractical at the
observed transfer rate. The generated-view GS quality is **FAIL**: two matched
headed-Chrome target-direction renders had higher photo error and visible
streaking. See [the experiment record](PANORAMA_VIDEO_EXPERIMENT.md).

The 115-file local package inventory includes `Dockerfile`, `Caddyfile` and
`.dockerignore`; the release archive contains only its 112 `www/` files. Every
file in a local archive readback matched the curated inventory's exact size
and SHA-256. A fresh GitHub release download matched the local 182,419,689-byte
archive SHA-256. Railway's build log independently reported
`/tmp/viewer.tar.gz: OK`, followed by Caddy startup and deployment SUCCESS.
The large originals, model weights, source job reports and
private desktop footage are outside the archive. The report itself is rebuilt
from selected status fields and downscaled, attributed images. Remote archive
readback and public-origin checks are recorded below.

| Public observation check | Result | Evidence |
| --- | --- | --- |
| Railway build and health | PASS | Exact pointer commit deployed; archive checksum OK in build log; Caddy starts; `/healthz` returns 200/`ok` |
| Public file integrity | PASS | All 112 `www/` files match the release inventory's exact bytes and SHA-256 |
| Missing/private paths | PASS | Seven probes return genuine 404, including the raw video experiment training log and unshipped inference log |
| Public video playback and 15-scene rendering | PASS after one test-only retry | The first 25-case run had 24 PASS / 1 missing-manifest wording assertion FAIL. The public server correctly returned HTTP 404; the local Vite server instead returned HTML/200. After accepting both visible error states, that case passed on the public origin. All 25 distinct cases passed; a focused four-case rerun captured the new public video, both GS views and gallery |

The public-origin browser run covered 15 direct scene routes and reloads,
gallery filters/search, 390px mobile layout, the old Mapillary comparisons,
actual MP4 playback/seeking, and viewer controls/error recovery. The initial
test failure was an assertion about the missing-world message, not a broken
deployment. The application and release archive were unchanged for the
targeted retry. The four-case public capture rerun passed; the inspected
screenshots show the video and both real Gaussian canvases, including their
visible quality faults. Local evidence is retained in
`data/validation/deployment/railway-panorama-http.json`,
`panorama-public-{report,baseline,rife,gallery}.png` and the corresponding
`panorama-public-*-checks.json` files. The new release has no pending Railway
changes. Browser success does not make the synthetic scene geometrically
accurate or visually accepted.

## Previous 13-scene observation release — 2026-11-05

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
| Deployment-pointer commit | `85bdd37e2fa1e9d26c803656e8dbaad63facd653` |
| Railway deployment | `f8f8c010-8774-4079-86e8-8ad138856424` — SUCCESS; public-browser verification recorded below |
| Deployment timing | Created 2026-11-04 23:48:04 UTC; SUCCESS 23:48:49 UTC (2026-11-05 KST) |
| Actual trigger | Explicit latest-branch connector trigger; push autodeploy remains unverified |

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
public file inventory. The published archive was downloaded again and its
SHA-256 matched the local file. Every new Gaussian PLY matches the existing local job
SHA-256, and coordinates/navigation are unchanged. The report is rebuilt from
explicit selected fields and an image allowlist; raw job logs, private footage,
private frames, model weights and local paths are not included.

| Public observation check | Result | Evidence |
| --- | --- | --- |
| Railway build and health | PASS | Exact pointer commit deployed; archive checksum OK in build log; Caddy server starts and healthcheck succeeds |
| Public file integrity | PASS | All 89 files match expected byte length and SHA-256; `/healthz` returns 200/`ok` |
| Missing/private paths | PASS | Five probes return genuine 404s, including private job/video paths and an unshipped inference log |
| Source/comparison display | PASS | Public report manually inspected; GS case switch visibly updates input, mask, generated output and metrics |
| Full public render regression | PASS after one targeted retry | 18 distinct cases covered: initial run 17 PASS / 1 download-timeout FAIL; the 69 MB scene passes render and reload with a longer public-download wait |
| Individual visual inspection | PASS | All 13 public-origin scene screenshots inspected; visible output and quality limitations recorded separately |
| Report and gallery interactions | PASS | Both comparison cases, actual images/masks, slider endpoints, 72 history records, all 13 scene links, search/filter, return/history and 390px mobile layout |

The initial public headed Chrome run finished with **17 PASS / 1 FAIL** in
4.8 minutes. The 69 MB `beijing-20k` scene was still downloading at 52.4 MB when
the 30-second readiness assertion expired; it had not reached a render result.
Only that case was rerun, with a 90-second public readiness wait and 180-second
test limit. It passed actual rendering and reload in **55.5 seconds** (58.5-second
runner duration). Localhost retains its original 30/60-second limits. These
durations include network transfer, rendering and test actions; they are not
GPU or cold-cache benchmarks. No application code or scene bytes changed for
the retry. All 13 scene captures were individually inspected. No page errors
were captured by the scene/report tests. TypeScript and lint passed again after
the test-only change.

Raw evidence is retained locally under `data/validation/deployment/`:
`railway-observations-http.json`, `railway-observations-status.json`,
`railway-observations-final-logs.json`, `observations-public-browser.log`,
`observations-public-large-retry.log`, both corresponding browser output folders,
and `observation-public-visual-review.json`. The original failed attempt and trace
remain preserved. The public report screenshot is
`data/validation/deployment/railway-observations-overview.png`; these local
evidence files are excluded from Git. Final service readback reports live,
the same successful deployment, and no staged changes.

**Quality remains FAIL** for the Mapillary reconstruction/completion experiment;
generated-view multi-view consistency remains **NOT RUN**. Publication and browser
rendering PASS do not change those acceptance results. The final documentation
and test-timeout commit does not replace the immutable viewer archive above.

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

1. As soon as a small authorized result is deployable, prepare its minimum static build/content/integrity checks and dispatch asynchronously. Do not wait for all local tests, browser checks, benchmarks or the final conclusion. Mark pending verification NOT RUN and update it afterward. FAIL quality is published rather than filtered out.
2. Inventory all exported worlds and experimental outcomes as they appear. Publish each distinct scene with public metadata and an actual render preview when available; any temporary neutral preview must be explicitly labeled NOT RUN. Record failed/cancelled/unexecuted stages and duplicate-export lineage in the report. Keep downloaded samples, measured/supplied-pose reconstructions, original video and generated-input trials distinct.
3. Build the curated static package locally using the explicit inclusion flags below. Inspect its complete inventory for private source paths, URLs, footage, frames and raw logs. Only explicitly allowlisted licensed public crops/comparisons belong in the report. Do not upload the repository or raw `dist/` directory.
4. Archive only `www/`, record its SHA-256, publish it under a fresh GitHub release tag, then download it and compare the hash. Keep the prior archive available.
5. Update the release URL/checksum in `deploy/Dockerfile.github`, commit the reviewable deployment pointer, and push it to the connected branch as part of the same workflow. A source-code push without this step leaves the old package live.
6. Observe Railway's deployment history, revision and healthcheck. A source-connection response is insufficient evidence of push-triggered deployment. If the expected new deployment does not appear, explicitly trigger the latest intended branch revision through the connector, continue validation, and record which trigger actually worked. The standing instruction already authorizes this routine fallback.
7. After dispatch, run the remaining relevant TypeScript, lint, automated, build and browser checks. Compare public files with the curated inventory, record any reused historical checks, verify missing/private paths return404, and inspect actual rendering/navigation. Do not claim a partial public check as a full inventory or full browser pass.
8. Record the release tag, source/deployment revisions, archive hash, Railway deployment ID and public-browser evidence here. Report any failed or unexecuted gate accurately; completion requires a verified live result.

### Branch request and explicit deployment fallback

The requested source is `feat/local-viewer-reconstruction` without a commit pin, with watch paths `/deploy/**` and `/.dockerignore`. Keep repository root as the build context and `deploy/Dockerfile.github` as the Dockerfile path. Native reconstruction and the production web build stay local; Railway downloads the already validated static archive and runs Caddy.

Railway documents branch autodeploy and watch patterns, but this service did not visibly deploy the release-pointer push during observation. The connector accepted the branch request and returned `commitSha: null`; later settings readback confirmed the watch patterns but only exposed `source.repo`. That does not prove a functioning GitHub push trigger. Its cause is not diagnosed. See [GitHub autodeploys](https://docs.railway.com/deployments/github-autodeploys) and [watch paths](https://docs.railway.com/deployments/monorepo#watch-paths).

The working release procedure must observe a new deployment and use an explicit latest-revision connector trigger when needed. Record that fallback rather than calling webhook autodeploy successful. The standing user instruction is to finish verified deployment in the same workflow; it does not depend on this unverified automatic trigger. Ordinary source/docs work must still produce a fresh archive and update the deployment pointer before any release is complete.

## Restore scene assets in a fresh checkout

The catalog/recipe are tracked; generated scenes and comparison images are
ignored. `npm run sample` supplies only Houseplant. The historical29-world
snapshot below remains reproducible. For the current34-world surface use the
four-layer restoration above. Restore only in a **fresh checkout**. These commands
replace the named generated paths; keep personal variants elsewhere.

```sh
(
  set -e
  gs_release_dir=$(mktemp -d)
  gs_archive=groundshift-street-conclusion-20261106-v2.tar.gz
  curl --fail --location --output "$gs_release_dir/$gs_archive" \
    "https://github.com/neocjmix/groundshift/releases/download/viewer-street-conclusion-2026-11-06/$gs_archive"
  printf '%s  %s\n' \
    'd84cae2eabef73c1898963a3a42a44e4f3865b7a3eda52a799d374d4c3b4ef4f' \
    "$gs_release_dir/$gs_archive" | shasum -a 256 -c -
  tar -xzf "$gs_release_dir/$gs_archive" -C "$gs_release_dir"
  mkdir -p public/worlds public/experiments
  cp -R "$gs_release_dir/www/worlds/." public/worlds/
  cp -R "$gs_release_dir/www/experiments/." public/experiments/
  # Tracked Vite entries must use source HTML during development.
  for gs_entry in experiments/*/index.html; do
    rm -f "public/$gs_entry"
  done
)
npm ci
npm run dev
```

**PASS:** tracked-source/archive restoration and isolated offline dependency
installation/build/package reproduced all830 staged hashes. The development
entry/module/summary smoke check is PASS (tracked source HTML, transformed module and exact summary hash; HTTP smoke only). This restores the29
worlds and14 reports; it does not reproduce native camera estimation/training.

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

Compare the archive contents against the staging inventory before publishing. The inventory JSON is retained beside the local staging directory; it is not part of the public `www/` archive. Re-download the published archive and verify the checksum before connecting Railway.

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

<!-- seine-snapshot-002 -->

### Automated route snapshot 002

Release `viewer-seine-route-002-1794047703065085000`, archive `groundshift-seine-route-002-1794047723732148000.tar.gz`, 99,960,013bytes, SHA-256 `ba0f7dc4c6f8b4bc58141622e92c3237b70c42defcf0f4f7bc28346cff45b120`. Apply after every previously pinned archive, in Docker COPY order. Explicit curation, complete base/overlay/composed checks and anonymous full archive readback PASS. 55 changed files; 1343 composed files. Git push dispatches the verified branch-follow service asynchronously. Provider status, public hashes and new GPU boundary/browser checks are NOT RUN at this source commit; private publication receipts record later actual readback without inventing acceptance.
