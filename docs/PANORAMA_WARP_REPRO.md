# Reproduce the wide-FOV panorama gap warp

Run from the repository root. This CPU-only recipe recreates the two 768×768,
120° source crops used by the corrected stereo trial. It retains the estimated
world poses from the six-camera rig and projects into panorama 5's existing
512×512, 90° target camera. It does not read target RGB pixels or invent a pose.

Use the NumPy/OpenCV environment described in [M1.md](M1.md) and the PyCOLMAP
environment in [MAPILLARY_EXPERIMENT.md](MAPILLARY_EXPERIMENT.md). If the source
sample and rig dataset do not already exist, prepare them with:

```sh
python3 scripts/fetch-mapillary-sample.py data/samples/mapillary-beijing
data/tools/venv/bin/python scripts/prepare-panoramas.py \
  data/samples/mapillary-beijing/images data/jobs/mapillary-beijing-crops \
  --provenance data/samples/mapillary-beijing/provenance.json
data/tools/colmap-venv/bin/python scripts/estimate-panorama-poses.py \
  data/jobs/mapillary-beijing-crops data/jobs/mapillary-beijing-rig-poses-v2 \
  --threads 4
```

Preparation and pose estimation require new output directories. Skip completed
steps; do not overwrite retained experiments. A fresh SfM run may estimate
different poses and therefore different stereo coverage. The exact retained
trial used a `dataset/transforms.json` SHA-256 of
`eb4f8cbfc38ef8be860e337cfa4dc8be037143f7e87a36f143be7a78c117b106`.

The pinned source manifest is
[scripts/samples/mapillary-beijing.json](../scripts/samples/mapillary-beijing.json).
It records Cicero101's Mapillary photographs, their Wikimedia Commons download
URLs, hashes and CC-BY-SA-4.0 attribution. This recipe verifies both observed
originals against that manifest and copies the acquisition provenance. Source
and target selection is fixed:

| Role | Original panorama | Rig view | Pixels used in warp preparation |
| --- | --- | --- | --- |
| A | `003_1677293342921360.jpg` | `pano_000004_view_04.png` | Yes |
| B | `004_679966948337536.jpg` | `pano_000005_view_04.png` | No; target camera metadata only |
| C | `005_23989291350709625.jpg` | `pano_000006_view_04.png` | Yes |

All three views have yaw 180° and pitch 0° relative to their own panorama
spheres. Widening A/C changes their analytic projection intrinsics, not their
estimated world rotations or camera centers. These poses were estimated using
all nine panoramas, including B. This is an **appearance holdout**, not an
independent camera or geometry holdout.

The following command creates `data/jobs/mapillary-beijing-wide-stereo-input-repro`
and refuses to overwrite an existing directory. It imports the existing crop
math instead of duplicating projection equations:

```sh
data/tools/venv/bin/python - <<'PY'
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")

spec = importlib.util.spec_from_file_location("panorama", "scripts/prepare-panoramas.py")
panorama = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panorama)
sample = Path("data/samples/mapillary-beijing")
manifest_path = Path("scripts/samples/mapillary-beijing.json")
manifest = json.loads(manifest_path.read_text())
pinned = {item["image_id"]: item for item in manifest["images"]}
crop_path = Path("data/jobs/mapillary-beijing-crops/crops.json")
crops = {Path(item["file"]).name: item for item in json.loads(crop_path.read_text())["crops"]}
poses_path = Path("data/jobs/mapillary-beijing-rig-poses-v2/dataset/transforms.json")
poses = json.loads(poses_path.read_text())
frames = {Path(item["file_path"]).name: item for item in poses["frames"]}
target_name = "pano_000005_view_04.png"
target = copy.deepcopy(frames[target_name])
assert (target["w"], target["h"], target["fl_x"], target["fl_y"], target["cx"], target["cy"]) == (512, 512, 256, 256, 256, 256)
assert crops[target_name]["yawDegrees"] == 180 and crops[target_name]["pitchDegrees"] == 0
calibration = panorama.intrinsics(768, 120)
output = Path("data/jobs/mapillary-beijing-wide-stereo-input-repro")
output.mkdir(parents=True, exist_ok=False)
(output / "images").mkdir()
report = {
    "scope": "Observed A/C pixels only; target B camera metadata only",
    "targetImagePixelsRead": False,
    "poseScope": "All-image rig SfM; appearance holdout only",
    "sourceTransformsSha256": sha256(poses_path),
    "sourceCropMetadataSha256": sha256(crop_path),
    "sourceManifestSha256": sha256(manifest_path),
    "sourceProvenanceSha256": sha256(sample / "provenance.json"),
    "projectionScriptSha256": sha256(Path("scripts/prepare-panoramas.py")),
    "opencvVersion": cv2.__version__,
    "sources": [],
}
prepared = []
for index, filename in [(4, "003_1677293342921360.jpg"), (6, "005_23989291350709625.jpg")]:
    source = sample / "images" / filename
    entry = pinned[source.stem.split("_", 1)[1]]
    source_hash = sha256(source)
    assert source_hash == entry["sha256"], f"Source hash mismatch: {filename}"
    name = f"pano_{index:06}_view_04.png"
    crop = crops[name]
    assert crop["sourceId"] == filename and crop["yawDegrees"] == 180 and crop["pitchDegrees"] == 0
    pixels = cv2.imread(str(source), cv2.IMREAD_COLOR)
    assert pixels is not None and pixels.shape[:2] == (entry["height"], entry["width"])
    result = panorama.crop_panorama(pixels, 768, 120, crop["yawDegrees"], crop["pitchDegrees"])
    destination = output / "images" / name
    assert cv2.imwrite(str(destination), result), f"Could not write {destination}"
    frame = copy.deepcopy(frames[name])
    frame.update(file_path=f"images/{name}", w=768, h=768,
                 fl_x=calibration["fx"], fl_y=calibration["fy"],
                 cx=calibration["cx"], cy=calibration["cy"])
    prepared.append(frame)
    report["sources"].append({"file": filename, "sha256": source_hash,
        "crop": name, "cropSha256": sha256(destination), "intrinsics": calibration,
        "commonsPage": entry["commons_page"], "author": entry["author"],
        "license": entry["license"], "licenseUrl": entry["license_url"]})
prepared.append(target)
write_json(output / "transforms.json", {"camera_model": "PINHOLE", "frames": prepared})
(output / "provenance.json").write_bytes((sample / "provenance.json").read_bytes())
write_json(output / "preparation.json", report)
assert not (output / target["file_path"]).exists()
print(output)
PY
```

Prepared metadata remains in the COLMAP/corner-origin convention: pixel centers
are `(column + 0.5, row + 0.5)`. A/C use `fx=fy=221.702503368816`, `cx=cy=384`;
B retains `fx=fy=cx=cy=256`. The corrected warp script subtracts **0.5 from
both principal-point coordinates once**, when constructing OpenCV intrinsics
for each source and the target. Do not pre-subtract it in `transforms.json`.

Run the corrected warp with the same settings as the selected trial:

```sh
data/tools/venv/bin/python scripts/warp-panorama-gap.py \
  data/jobs/mapillary-beijing-wide-stereo-input-repro \
  data/jobs/mapillary-beijing-stereo-gap-view04-widefov-repro \
  --left pano_000004_view_04.png \
  --right pano_000006_view_04.png \
  --target pano_000005_view_04.png \
  --max-disparity 512
```

The output is a 512×512 `warp.png`, a binary grayscale `mask.png` (255 means
unknown), rectified observations, depth/disparity arrays and `report.json`
containing input hashes, settings and measured coverage. No diffusion runs in
this command. Preserve the black unknown regions and mask for later inpainting;
they are not observed black surfaces.

The original corrected trial is retained locally at
`data/jobs/mapillary-beijing-stereo-gap-view04-widefov-v2`, using inputs from
`data/jobs/mapillary-beijing-wide-stereo-input`. It measured 65,214 known pixels
out of 262,144 (24.88%), leaving **75.12% unknown**. This is a partial experimental
warp, not an accepted reconstruction. Fresh runs must report their own coverage.
Any comparison with B's actual RGB must happen separately, after warp creation;
photometric comparison does not establish 3D accuracy.

The documented recipe and warp command were executed locally: both source PNGs,
the camera metadata, output warp PNG and mask PNG matched the retained corrected
trial exactly. The repeat took 1.78 s for the warp and reproduced 65,214 known
pixels; target RGB remained absent from its input directory.
