"""Adapter/mask checks; these never execute or certify GPU diffusion."""
import importlib.util
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "inpaint-gap.py"
spec = importlib.util.spec_from_file_location("inpaint_gap", SCRIPT)
inpaint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inpaint)
try:
    from PIL import Image
except ImportError:
    Image = None


@unittest.skipUnless(Image, "Pillow not installed; pixel validation NOT RUN")
class InpaintGapTests(unittest.TestCase):
    def inputs(self, root, value=255):
        image = Image.new("RGB", (64, 64), (21, 42, 63))
        mask = Image.new("L", (64, 64), 0)
        mask.paste(value, (20, 20, 40, 40))
        image.save(root / "image.png")
        mask.save(root / "mask.png")
        return root / "image.png", root / "mask.png"

    def test_known_pixels_are_preserved_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.inputs(root)
            image, mask, metadata = inpaint.prepare_inputs(*paths, 512)
            result = inpaint.compose_preserving_reference(Image.new("RGB", image.size, "red"), image, mask)
            self.assertEqual(result.getpixel((0, 0)), (21, 42, 63))
            self.assertEqual(result.getpixel((30, 30)), (255, 0, 0))
            self.assertEqual(metadata["syntheticPixels"], 400)

    def test_nonbinary_or_empty_mask_is_rejected(self):
        for value in (128, 0):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temporary:
                paths = self.inputs(Path(temporary), value)
                with self.assertRaises(ValueError):
                    inpaint.prepare_inputs(*paths, 512)

    def test_failed_inference_preserves_log_and_never_reports_gpu_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image, mask = self.inputs(root)
            output = root / "job"
            with (patch.object(inpaint, "infer", side_effect=RuntimeError("mock failure; no GPU executed")),
                  redirect_stdout(io.StringIO())):
                code = inpaint.main([str(image), str(mask), str(output), "--prompt", "test fixture"])
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(code, 1)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["gpuInference"], "NOT RUN")
            self.assertTrue(report["synthetic"])
            self.assertEqual(report["multiViewConsistency"], "NOT RUN")
            self.assertIn("mock failure", (output / "inference.log").read_text())
            self.assertFalse((output / "completed.png").exists())


class InpaintArgumentsTests(unittest.TestCase):
    def test_existing_evidence_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            sentinel = output / "report.json"
            sentinel.write_text("existing evidence")
            with redirect_stderr(io.StringIO()):
                code = inpaint.main(["unused.png", "unused-mask.png", str(output), "--prompt", "test"])
            self.assertEqual(code, 2)
            self.assertEqual(sentinel.read_text(), "existing evidence")

    def test_invalid_settings_fail_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "job"
            for option, value in (("--guidance", "nan"), ("--max-edge", "1024"),
                                  ("--strength", "0.001"), ("--seed", "-1")):
                with self.subTest(option=option), redirect_stderr(io.StringIO()):
                    code = inpaint.main(["unused.png", "unused-mask.png", str(output),
                                         "--prompt", "test", option, value])
                self.assertEqual(code, 2)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
