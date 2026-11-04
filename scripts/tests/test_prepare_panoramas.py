"""Projection tests use synthetic analytic images; they do not validate real SfM."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "prepare-panoramas.py"
SPEC = importlib.util.spec_from_file_location("prepare_panoramas", SCRIPT)
PANORAMA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PANORAMA)
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


class PanoramaContractTests(unittest.TestCase):
    def test_exact_pinhole_intrinsics(self):
        calibration = PANORAMA.intrinsics(512, 90)
        self.assertEqual([calibration[key] for key in ("fx", "fy", "cx", "cy")], [256] * 4)
        self.assertAlmostEqual(PANORAMA.intrinsics(600, 60)["fx"], 300 * math.sqrt(3))

    def test_invalid_field_of_view_and_duplicate_yaws(self):
        for fov in (0, 180, float("nan"), float("inf")):
            with self.subTest(fov=fov), self.assertRaises(ValueError):
                PANORAMA.intrinsics(512, fov)
        for yaws in ("0,360", "nan", "0,inf", ""):
            with self.subTest(yaws=yaws), self.assertRaises(Exception):
                PANORAMA.angles(yaws)

    def test_provenance_requires_source_license_and_attribution(self):
        valid = {"sourceType": "images", "sourceUrl": "https://example.com/panoramas",
                 "license": "CC-BY-4.0", "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
                 "attribution": "Synthetic test fixture"}
        PANORAMA.validate_provenance(valid)
        for key in ("sourceType", "sourceUrl", "license", "licenseUrl", "attribution"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                PANORAMA.validate_provenance({k: v for k, v in valid.items() if k != key})
        for url in ("https://user:secret@example.com/x", "javascript:alert(1)", "https://example.com:invalid/x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                PANORAMA.validate_provenance({**valid, "sourceUrl": url})

    def test_existing_output_and_dangling_symlink_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input"
            source.mkdir()
            output = root / "output"
            output.mkdir()
            marker = output / "keep"
            marker.write_text("original")
            command = [sys.executable, str(SCRIPT), str(source), str(output), "--provenance", "unused"]
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(list(output.iterdir()), [marker])
            self.assertEqual(marker.read_text(), "original")
            link = root / "link"
            link.symlink_to(root / "missing")
            command[3] = str(link)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertTrue(link.is_symlink())
            self.assertFalse((root / "missing").exists())


@unittest.skipUnless(cv2 is not None, "NumPy/OpenCV required; run data/tools/venv/bin/python. Projection pixels NOT RUN")
class PanoramaProjectionTests(unittest.TestCase):
    def direction_panorama(self, width=720, height=360):
        longitude = ((np.arange(width) + 0.5) / width - 0.5) * 2 * np.pi
        latitude = (0.5 - (np.arange(height) + 0.5) / height) * np.pi
        lon, lat = np.meshgrid(longitude, latitude)
        directions = np.stack((np.cos(lat) * np.sin(lon), -np.sin(lat), np.cos(lat) * np.cos(lon)), axis=-1)
        return np.rint((directions + 1) * 127.5).astype(np.uint8)

    def test_cardinal_centers_and_pitch_use_declared_axes(self):
        source = self.direction_panorama()
        expected = {(0, 0): (128, 128, 255), (90, 0): (255, 128, 128),
                    (180, 0): (128, 128, 0), (270, 0): (0, 128, 128),
                    (0, 90): (128, 0, 128), (0, -90): (128, 255, 128)}
        for (yaw, pitch), color in expected.items():
            with self.subTest(yaw=yaw, pitch=pitch):
                crop = PANORAMA.crop_panorama(source, 65, 90, yaw, pitch)
                np.testing.assert_allclose(crop[32, 32], color, atol=2)

    def test_screen_right_and_up_preserve_handedness(self):
        crop = PANORAMA.crop_panorama(self.direction_panorama(), 65, 90, 0, 0)
        self.assertGreater(int(crop[32, -1, 0]), int(crop[32, 0, 0]) + 150)
        self.assertGreater(int(crop[-1, 32, 1]), int(crop[0, 32, 1]) + 150)
        # The upper-right corner is near the normalized ray (1,-1,1).
        expected = (np.array([1, -1, 1]) / math.sqrt(3) + 1) * 127.5
        np.testing.assert_allclose(crop[0, -1], expected, atol=2)

    def test_horizontal_seam_blends_last_and_first_columns(self):
        source = np.zeros((8, 16, 3), dtype=np.uint8)
        source[:, 0] = 200
        source[:, -1] = 100
        for yaw in (-180, 180, 540):
            with self.subTest(yaw=yaw):
                crop = PANORAMA.crop_panorama(source, 1, 90, yaw, 0)
                np.testing.assert_array_equal(crop[0, 0], [150, 150, 150])

    def test_poles_clamp_instead_of_wrapping(self):
        source = np.zeros((8, 16, 3), dtype=np.uint8)
        source[0] = 200
        source[-1] = 100
        np.testing.assert_array_equal(PANORAMA.crop_panorama(source, 1, 90, 0, 90)[0, 0], [200] * 3)
        np.testing.assert_array_equal(PANORAMA.crop_panorama(source, 1, 90, 0, -90)[0, 0], [100] * 3)

    def test_overlap_same_ray_and_rotation_are_consistent(self):
        first = PANORAMA.crop_rotation(0, 0) @ np.array([math.tan(math.pi / 6), 0, 1])
        second = PANORAMA.crop_rotation(60, 0) @ np.array([-math.tan(math.pi / 6), 0, 1])
        np.testing.assert_allclose(first, second, atol=1e-12)
        rotation = PANORAMA.crop_rotation(123, -45)
        np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(rotation), 1)

    def test_rejects_non_equirectangular_shape_and_high_bit_depth(self):
        for source in (np.zeros((100, 201, 3), dtype=np.uint8),
                       np.zeros((100, 200, 3), dtype=np.uint16),
                       np.zeros((100, 200, 4), dtype=np.uint8)):
            with self.subTest(shape=source.shape, dtype=source.dtype), self.assertRaises(ValueError):
                PANORAMA.crop_panorama(source, 64, 90, 0, 0)


@unittest.skipUnless(cv2 is not None, "NumPy/OpenCV required; run data/tools/venv/bin/python. File preparation NOT RUN")
class PanoramaPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "input"
        self.source.mkdir()
        self.provenance = self.root / "provenance.json"
        self.provenance.write_text(json.dumps({"sourceType": "images", "sourceUrl": "https://example.com/panorama",
                                               "license": "Synthetic fixture", "licenseUrl": "https://example.com/license",
                                               "attribution": "Groundshift synthetic test"}))

    def prepare(self, expected=0):
        output = self.root / "prepared"
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.source), str(output),
                                 "--provenance", str(self.provenance), "--size", "64"], capture_output=True)
        self.assertEqual(result.returncode, expected, result.stderr.decode())
        report = json.loads((output / "report.json").read_text())
        return output, report

    def test_real_decode_crop_encode_hashes_and_no_fabricated_pose_files(self):
        source = self.source / "mapillary-id.png"
        cv2.imwrite(str(source), PanoramaProjectionTests().direction_panorama(360, 180))
        output, report = self.prepare()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["result"]["cropCount"], 6)
        self.assertEqual(report["result"]["colmapArguments"][3], "32,32,32,32")
        manifest = json.loads((output / "crops.json").read_text())
        self.assertEqual(manifest["sourcePanoramas"][0]["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(manifest["sourcePanoramas"][0]["sourceId"], source.name)
        for crop in manifest["crops"]:
            path = output / crop["file"]
            self.assertEqual(cv2.imread(str(path)).shape, (64, 64, 3))
            self.assertEqual(crop["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertNotIn("transform_matrix", crop)
        self.assertFalse(manifest["worldCameraPosesProvided"])
        self.assertFalse(manifest["diffusionUsed"])
        for filename in ("transforms.json", "sequence.json", "init.ply"):
            self.assertFalse((output / filename).exists(), filename)
        self.assertEqual(report["cameraEstimation"], "NOT RUN")
        self.assertEqual((output / "source-provenance.json").read_bytes(), self.provenance.read_bytes())

    def test_empty_input_is_logged_failure(self):
        output, report = self.prepare(expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("no supported", report["error"])
        self.assertIn("ValueError", (output / "execution.log").read_text())
        self.assertFalse((output / "crops.json").exists())

    def test_invalid_aspect_is_logged_failure(self):
        cv2.imwrite(str(self.source / "bad.png"), np.zeros((40, 90, 3), dtype=np.uint8))
        output, report = self.prepare(expected=1)
        self.assertIn("2:1", report["error"])
        self.assertFalse((output / "crops.json").exists())

    def test_corrupt_image_is_logged_failure(self):
        (self.source / "broken.jpg").write_bytes(b"not an image")
        output, report = self.prepare(expected=1)
        self.assertIn("Cannot decode panorama", report["error"])
        self.assertIn("broken.jpg", (output / "execution.log").read_text())
        self.assertFalse((output / "crops.json").exists())

    def test_invalid_provenance_is_logged_before_image_preparation(self):
        self.provenance.write_text("{}")
        output, report = self.prepare(expected=1)
        self.assertIn("provenance sourceType", report["error"])
        self.assertFalse((output / "images").exists())


if __name__ == "__main__":
    unittest.main()
