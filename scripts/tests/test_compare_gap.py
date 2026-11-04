"""Analytic RGB fixtures verify metrics; they do not establish scene quality."""
import hashlib
import importlib.util
import io
import json
import math
from contextlib import redirect_stderr
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "compare-gap.py"
SPEC = importlib.util.spec_from_file_location("compare_gap", SCRIPT)
COMPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPARE)
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


@unittest.skipUnless(cv2 is not None, "NumPy/OpenCV required; run data/tools/venv/bin/python. Pixel metrics NOT RUN")
class PhotometricComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.reference = self.save("reference.png", np.zeros((2, 2, 3), dtype=np.uint8))
        self.baseline = self.save("baseline.png", np.full((2, 2, 3), 10, dtype=np.uint8))
        completed = np.zeros((2, 2, 3), dtype=np.uint8)
        completed[:, 1] = 20
        self.completed = self.save("completed.png", completed)
        self.mask = self.save("mask.png", np.array([[255, 0], [255, 0]], dtype=np.uint8))

    def save(self, name, image):
        path = self.root / name
        self.assertTrue(cv2.imwrite(str(path), image))
        return path

    def compare(self, name="result", mask=True):
        return COMPARE.compare(self.reference, self.baseline, self.completed,
                               self.root / name, self.mask if mask else None)

    def test_known_full_and_region_metrics_and_hashes(self):
        report = self.compare()
        full, masked, unmasked = (report["regions"][x] for x in ("full", "masked", "unmasked"))
        self.assertEqual([full["pixelCount"], masked["pixelCount"], unmasked["pixelCount"]], [4, 2, 2])
        self.assertEqual(full["baseline"]["mae"], 10)
        self.assertEqual(full["baseline"]["mse"], 100)
        self.assertAlmostEqual(full["baseline"]["psnrDb"], 20 * math.log10(255 / 10))
        self.assertEqual(full["completed"]["mae"], 10)
        self.assertEqual(full["completed"]["mse"], 200)
        self.assertAlmostEqual(full["completed"]["psnrDb"], 10 * math.log10(255 ** 2 / 200))
        self.assertEqual(masked["completed"]["mae"], 0)
        self.assertEqual(unmasked["completed"]["mae"], 20)
        self.assertEqual(unmasked["completed"]["channelValueCount"], 6)
        for name, path in (("reference", self.reference), ("baseline", self.baseline),
                           ("completed", self.completed), ("mask", self.mask)):
            data = path.read_bytes()
            self.assertEqual(report["inputs"][name]["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(report["inputs"][name]["bytes"], len(data))

    def test_exact_match_psnr_is_json_null_with_explicit_flag(self):
        self.compare()
        def forbid_nonstandard(value):
            self.fail(f"Nonstandard JSON numeric constant: {value}")
        report = json.loads((self.root / "result" / "report.json").read_text(),
                            parse_constant=forbid_nonstandard)
        metric = report["regions"]["masked"]["completed"]
        self.assertIsNone(metric["psnrDb"])
        self.assertTrue(metric["exactMatch"])
        self.assertIn("positive infinity", metric["psnrInterpretation"])
        self.assertFalse(report["regions"]["full"]["baseline"]["exactMatch"])

    def test_subtraction_does_not_wrap_unsigned_pixels(self):
        reference = np.full((1, 1, 3), 255, dtype=np.uint8)
        candidate = np.zeros_like(reference)
        result = COMPARE.region_metrics(reference, candidate, np.ones((1, 1), dtype=bool))
        self.assertEqual(result["mae"], 255)
        self.assertEqual(result["mse"], 255 ** 2)
        self.assertEqual(result["psnrDb"], 0)

    def test_dimension_mismatches_and_invalid_masks_preserve_failure(self):
        cases = [
            ("wrong-size", np.zeros((1, 2), dtype=np.uint8), "dimensions"),
            ("nonbinary", np.array([[255, 0], [128, 0]], dtype=np.uint8), "binary"),
            ("rgb-mask", np.zeros((2, 2, 3), dtype=np.uint8), "single-channel"),
            ("empty-gap", np.zeros((2, 2), dtype=np.uint8), "nonempty"),
            ("empty-kept", np.full((2, 2), 255, dtype=np.uint8), "nonempty"),
        ]
        for name, image, expected in cases:
            with self.subTest(name=name):
                self.mask = self.save(f"{name}.png", image)
                with self.assertRaisesRegex(ValueError, expected):
                    self.compare(name=name)
                report = json.loads((self.root / name / "report.json").read_text())
                self.assertEqual(report["status"], "FAIL")
        self.completed = self.save("different-rgb-size.png", np.zeros((3, 2, 3), dtype=np.uint8))
        with self.assertRaisesRegex(ValueError, "dimensions"):
            self.compare(name="image-mismatch", mask=False)

    def test_no_mask_marks_regions_not_run_and_existing_output_is_preserved(self):
        report = self.compare(mask=False)
        self.assertEqual(report["regions"]["full"]["status"], "PASS")
        self.assertEqual(report["regions"]["masked"]["status"], "NOT RUN")
        self.assertEqual(report["regions"]["unmasked"]["status"], "NOT RUN")
        before = (self.root / "result" / "report.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "new directory"):
            self.compare(mask=False)
        self.assertEqual((self.root / "result" / "report.json").read_bytes(), before)
        link = self.root / "dangling"
        link.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(ValueError, "new directory"):
            self.compare(name="dangling", mask=False)
        self.assertTrue(link.is_symlink())
        self.assertFalse((self.root / "missing").exists())

    def test_nonopaque_alpha_and_16bit_images_are_rejected(self):
        rgba = np.full((2, 2, 4), 255, dtype=np.uint8)
        rgba[0, 0, 3] = 0
        for name, image, expected in (("alpha", rgba, "nonopaque"),
                                      ("16bit", np.zeros((2, 2, 3), dtype=np.uint16), "8-bit")):
            with self.subTest(name=name):
                self.completed = self.save(f"{name}.png", image)
                with self.assertRaisesRegex(ValueError, expected):
                    self.compare(name=name, mask=False)

    def test_keyboard_interrupt_retains_cancelled_report_and_traceback(self):
        with patch.object(COMPARE, "read_image", side_effect=KeyboardInterrupt("test cancellation")):
            with self.assertRaises(KeyboardInterrupt):
                self.compare()
        report = json.loads((self.root / "result/report.json").read_text())
        self.assertEqual(report["status"], "CANCELLED")
        self.assertIn("KeyboardInterrupt", report["traceback"])

    def test_cli_sigterm_handler_marks_cancelled_and_restores_previous_handler(self):
        previous = signal.getsignal(signal.SIGTERM)
        def interrupt_read(*_args):
            handler = signal.getsignal(signal.SIGTERM)
            self.assertTrue(callable(handler))
            self.assertIsNot(handler, previous)
            # Deliver to the installed handler without signalling the test host.
            handler(signal.SIGTERM, None)
        output = self.root / "interrupted-cli"
        with (patch.object(sys, "argv", [str(SCRIPT), str(self.reference), str(self.baseline),
                                         str(self.completed), str(output)]),
              patch.object(COMPARE, "read_image", side_effect=interrupt_read),
              redirect_stderr(io.StringIO())):
            self.assertEqual(COMPARE.main(), 130)
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)
        report = json.loads((output / "report.json").read_text())
        self.assertEqual(report["status"], "CANCELLED")
        self.assertIn("SIGTERM", report["error"])


if __name__ == "__main__":
    unittest.main()
