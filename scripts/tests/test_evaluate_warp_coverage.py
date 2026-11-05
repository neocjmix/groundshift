"""Support sets must be compared on the same pixels, not by raw MAE alone."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


SPEC = importlib.util.spec_from_file_location('evaluate_warp_coverage', Path(__file__).resolve().parents[1] / 'evaluate-warp-coverage.py')
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)


@unittest.skipUnless(cv2 is not None and np is not None, 'NumPy/OpenCV required; warp evaluation NOT RUN')
class WarpEvaluationTests(unittest.TestCase):
    def test_common_and_new_coverage_are_reported_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stereo, learned = root / 'stereo', root / 'learned'
            stereo.mkdir(); learned.mkdir()
            target = np.full((2, 2, 3), 100, dtype=np.uint8)
            a = np.zeros_like(target); a[0, 0] = 100
            b = np.zeros_like(target); b[0, 0] = 80; b[0, 1] = 100
            c = b.copy(); c[0, 1] = 0
            am = np.array([[0, 255], [255, 255]], dtype=np.uint8)
            bm = np.array([[0, 0], [255, 255]], dtype=np.uint8)
            cm = np.array([[0, 255], [255, 255]], dtype=np.uint8)
            for path, value in ((root / 'target.png', target), (stereo / 'warp.png', a),
                                (stereo / 'mask.png', am), (learned / 'warp.png', b),
                                (learned / 'mask.png', bm), (learned / 'warp-consistent.png', c),
                                (learned / 'mask-consistent.png', cm)):
                self.assertTrue(cv2.imwrite(str(path), value))
            result = EVAL.evaluate(root / 'target.png', stereo, learned, root / 'out')
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['variants']['stereo']['projectedSourcePixels'], 1)
            raw = result['variants']['learnedRaw']['vsStereo']
            self.assertEqual((raw['commonPixels'], raw['learnedOnlyPixels']), (1, 1))
            self.assertEqual(raw['stereoOnCommon']['mae255'], 0)
            self.assertEqual(raw['learnedOnCommon']['mae255'], 20)
            self.assertEqual(result['variants']['learnedSourceConsistent']['projectedSourcePixels'], 1)


if __name__ == '__main__':
    unittest.main()
