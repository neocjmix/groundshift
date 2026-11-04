"""Real subprocess/signal lifecycle tests with a fake, non-GPU COLMAP stage."""
import json
import importlib.util
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "estimate-poses.py"
SPEC = importlib.util.spec_from_file_location("estimate_poses", SCRIPT)
ESTIMATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ESTIMATOR)
FAKE_COLMAP = '''
import time
__version__ = "test-double"
has_cuda = False
class Options:
    def __init__(self, values): pass
ImageReaderOptions = FeatureExtractionOptions = Options
class CameraMode:
    SINGLE = "single"
    AUTO = "auto"
class Device:
    cpu = "cpu"
def extract_features(*args, **kwargs):
    print("FAKE_STAGE_READY", flush=True)
    time.sleep(60)
'''


class EstimatePosesCancellationTests(unittest.TestCase):
    def run_cancellation(self, signum):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "images"
            images.mkdir()
            for i in range(3):
                (images / f"image{i}.jpg").write_bytes(b"test-double-input")
            (root / "pycolmap.py").write_text(FAKE_COLMAP)
            output = root / "result"
            environment = {**os.environ, "PYTHONPATH": str(root)}
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), "--images", str(images), "--output", str(output)],
                env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                deadline = time.monotonic() + 10
                log = output / "execution.log"
                while time.monotonic() < deadline:
                    if log.exists() and "FAKE_STAGE_READY" in log.read_text():
                        break
                    if process.poll() is not None:
                        self.fail(f"Process exited before signal: {process.communicate()}")
                    time.sleep(0.02)
                else:
                    self.fail("Test stage did not start")
                process.send_signal(signum)
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 128 + signum, (stdout, stderr))
                report = json.loads((output / "report.json").read_text())
                self.assertEqual(report["status"], "CANCELLED")
                self.assertEqual(report["cancellationSignal"], signal.Signals(signum).name)
                self.assertEqual(report["stages"][0]["status"], "CANCELLED")
                self.assertIn("finishedAt", report)
                self.assertGreaterEqual(report["elapsedSeconds"], 0)
                self.assertIn("FAKE_STAGE_READY", log.read_text())
                self.assertEqual(len(list(images.iterdir())), 3)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_sigterm_preserves_cancelled_report(self):
        self.run_cancellation(signal.SIGTERM)

    def test_sigint_preserves_cancelled_report(self):
        self.run_cancellation(signal.SIGINT)


class EstimatePosesDiagnosticsTests(unittest.TestCase):
    def test_provenance_distinguishes_calibration_from_local_pose_estimation(self):
        calibrated = ESTIMATOR.reconstruction_note("536,534,752,500", True, 120, 30468)
        self.assertIn("Provided lens calibration", calibrated)
        self.assertIn("kept fixed", calibrated)
        self.assertIn("120 camera poses and 30468 sparse points were estimated locally", calibrated)
        refined = ESTIMATOR.reconstruction_note("536,534,752,500", False, 120, 30468)
        self.assertIn("allowed to refine", refined)
        estimated = ESTIMATOR.reconstruction_note("", False, 120, 30468)
        self.assertIn("No lens parameters were supplied", estimated)
        self.assertIn("image metadata/default initialization", estimated)
        self.assertNotIn("Provided lens calibration", estimated)

    def test_no_reconstruction_marks_mapping_failed_and_keeps_input_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images, output = root / "images", root / "output"
            images.mkdir()
            for i in range(3):
                (images / f"{i}.jpg").write_bytes(b"input")
            fake = FAKE_COLMAP + '''
import sqlite3
from types import SimpleNamespace
FeatureMatchingOptions = Options
def IncrementalPipelineOptions(values):
    return SimpleNamespace(mapper=SimpleNamespace())
def extract_features(database, images, image_names, **kwargs):
    with sqlite3.connect(database) as connection:
        connection.executescript("CREATE TABLE images(image_id INTEGER, name TEXT);"
                                 "CREATE TABLE keypoints(image_id INTEGER, rows INTEGER);"
                                 "CREATE TABLE matches(pair_id INTEGER, rows INTEGER);"
                                 "CREATE TABLE two_view_geometries(pair_id INTEGER, rows INTEGER);")
        connection.executemany("INSERT INTO images VALUES (?, ?)", enumerate(image_names, 1))
def match_exhaustive(*args, **kwargs): pass
def incremental_mapping(*args, **kwargs): return {}
'''
            (root / "pycolmap.py").write_text(fake)
            result = subprocess.run([sys.executable, str(SCRIPT), "--images", str(images),
                                     "--output", str(output)], capture_output=True,
                                    env={**os.environ, "PYTHONPATH": str(root)})
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["fullRegistration"], "FAIL")
            self.assertEqual(report["stages"][-1]["status"], "FAIL")
            self.assertEqual(report["registeredImages"], [])
            self.assertEqual(len(report["unregisteredImages"]), 3)
            self.assertEqual(len(report["inputFileHashes"]), 3)
            self.assertFalse((output / "dataset").exists())

    def test_match_graph_keeps_disconnected_images_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory).resolve() / "database.db"
            with sqlite3.connect(database) as connection:
                connection.executescript("CREATE TABLE images(image_id INTEGER, name TEXT);"
                                         "CREATE TABLE keypoints(image_id INTEGER, rows INTEGER);"
                                         "CREATE TABLE matches(pair_id INTEGER, rows INTEGER);"
                                         "CREATE TABLE two_view_geometries(pair_id INTEGER, rows INTEGER);")
                connection.executemany("INSERT INTO images VALUES (?, ?)",
                                       [(1, "001.jpg"), (2, "002.jpg"), (3, "003.jpg")])
                connection.executemany("INSERT INTO keypoints VALUES (?, ?)", [(1, 100), (2, 200), (3, 150)])
                connection.executemany("INSERT INTO two_view_geometries VALUES (?, ?)",
                                       [(2147483647 + 2, 35), (2147483647 + 3, 0)])
                connection.executemany("INSERT INTO matches VALUES (?, ?)",
                                       [(2147483647 + 2, 60), (2147483647 + 3, 20)])
            report = ESTIMATOR.database_diagnostics(database)
            self.assertEqual(report["verifiedPairs"], 1)
            self.assertEqual(report["verifiedPairInliers"]["mean"], 35)
            self.assertEqual(report["matchGraphComponents"], [["001.jpg", "002.jpg"], ["003.jpg"]])
            self.assertEqual(report["featuresByImage"]["003.jpg"], 150)
            self.assertEqual(report["rawMatchedPairs"], 2)
            self.assertEqual(report["rawPairMatches"]["mean"], 40)

    def test_invalid_matching_budget_fails_before_dependency_import(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--images", "unused", "--output", "unused",
                                 "--matching", "sequential", "--overlap", "0"], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"positive threads/overlap", result.stderr)

    def test_existing_output_preserves_user_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images, output = root / "images", root / "output"
            images.mkdir()
            output.mkdir()
            marker = output / "original.txt"
            marker.write_text("preserve")
            for i in range(3):
                (images / f"{i}.jpg").write_bytes(b"input")
            result = subprocess.run([sys.executable, str(SCRIPT), "--images", str(images),
                                     "--output", str(output)], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"Output already exists", result.stderr)
            self.assertEqual(marker.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
