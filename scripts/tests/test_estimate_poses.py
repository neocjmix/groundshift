"""Real subprocess/signal lifecycle tests with a fake, non-GPU COLMAP stage."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "estimate-poses.py"
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


if __name__ == "__main__":
    unittest.main()
