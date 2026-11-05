"""Calibration and holdout-contract fixtures, not learned-depth quality claims."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import numpy as np
    from PIL import Image
except ImportError:
    np = None

SCRIPT = Path(__file__).resolve().parents[1] / 'evaluate-panoramic-depth.py'
if np is not None:
    # The runnable script imports its small geometry sibling by module name.
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location('evaluate_panoramic_depth', SCRIPT)
        EVALUATE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(EVALUATE)
    finally:
        sys.path.pop(0)


@unittest.skipUnless(np is not None, 'NumPy and Pillow required; calibration tests NOT RUN')
class PanoramicCalibrationTests(unittest.TestCase):
    def test_da2_scale_only_preserves_radial_semantics_and_rejects_outlier_bias(self):
        prediction = np.geomspace(.2, 30, 101)
        radial = prediction * 3.25
        radial[:15] *= 100  # A minority of badly triangulated points must not set scale.
        fit = EVALUATE.fit_calibration(prediction, radial, 'da2')
        self.assertEqual(fit['convention'], 'ray-range')
        self.assertEqual(fit['units'], 'sfm-arbitrary')
        self.assertEqual(fit['offset'], 0)
        self.assertAlmostEqual(fit['scale'], 3.25, places=12)
        converted, valid = EVALUATE.apply_calibration(np.array([1., 10.]), fit)
        np.testing.assert_allclose(converted, [3.25, 32.5])
        self.assertTrue(valid.all())

    def test_dav2_recovers_affine_inverse_range_with_sparse_outliers(self):
        prediction = np.linspace(-.1, 5, 151)
        radial = 1 / (.07 * prediction + .04)
        radial[::17] *= .01
        fit = EVALUATE.fit_calibration(prediction, radial, 'dav2')
        self.assertEqual(fit['convention'], 'inverse-ray-range')
        np.testing.assert_allclose([fit['scale'], fit['offset']], [.07, .04], atol=2e-5)
        converted, valid = EVALUATE.apply_calibration(np.array([0., 2., 4.]), fit)
        np.testing.assert_allclose(converted, 1 / np.array([.04, .18, .32]), rtol=5e-4)
        self.assertTrue(valid.all())
        self.assertGreater(converted[0], converted[-1])

    def test_training_fit_rejects_invalid_pairs_and_insufficient_evidence(self):
        prediction = np.linspace(1, 5, 40)
        target = prediction * 2
        cases = [(prediction[:29], target[:29]), (prediction[:, None], target[:, None]),
                 (prediction, target[:-1]), (np.where(np.arange(40) == 5, np.nan, prediction), target),
                 (prediction, np.where(np.arange(40) == 5, np.inf, target)),
                 (prediction, np.where(np.arange(40) == 5, 0., target)),
                 (prediction, -target)]
        for x, y in cases:
            for kind in ('da2', 'dav2'):
                with self.subTest(kind=kind, xshape=x.shape, yshape=y.shape), self.assertRaises(ValueError):
                    EVALUATE.fit_calibration(x, y, kind)

    def test_da2_nonpositive_predictions_are_not_treated_as_ranges(self):
        prediction = np.linspace(1, 5, 40)
        target = prediction * 2
        for bad in (0., -1.):
            x = prediction.copy()
            x[20] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                EVALUATE.fit_calibration(x, target, 'da2')

    def test_dav2_constant_or_reversed_depth_cannot_be_calibrated(self):
        prediction = np.linspace(1, 5, 40)
        for x, y in ((np.ones(40), prediction), (prediction, 1 / (1 - .1 * prediction))):
            with self.subTest(constant=np.ptp(x) == 0), self.assertRaises(ValueError):
                EVALUATE.fit_calibration(x, y, 'dav2')

    def test_unknown_model_cannot_silently_substitute_depth_semantics(self):
        with self.assertRaises(ValueError):
            EVALUATE.fit_calibration(np.arange(1, 41), np.arange(1, 41), 'unknown')

    def test_id_holdout_is_deterministic_and_independent_of_input_order(self):
        ids = np.arange(1, 501, dtype=np.int64)
        first = EVALUATE.split_ids(ids)
        np.testing.assert_array_equal(first, EVALUATE.split_ids(ids))
        self.assertGreater(first.sum(), 0)
        self.assertLess(first.sum(), len(ids))
        order = np.random.default_rng(17).permutation(len(ids))
        np.testing.assert_array_equal(EVALUATE.split_ids(ids[order]), first[order])
        np.testing.assert_array_equal(EVALUATE.split_ids([41, 41, 83]), EVALUATE.split_ids([41, 83, 83])[[0, 0, 2]])

    def test_residuals_record_empty_and_invalid_predictions_without_fake_zero_error(self):
        empty = EVALUATE.residual_stats(np.array([]), np.array([]))
        self.assertEqual((empty['samples'], empty['validSamples'], empty['invalidSamples']), (0, 0, 0))
        for key in ('medianAbsRel', 'p90AbsRel', 'medianAbsoluteSfmUnits'):
            self.assertIsNone(empty[key])
        invalid = EVALUATE.residual_stats(np.array([np.nan, np.inf, 0., -2.]), np.ones(4))
        self.assertEqual((invalid['samples'], invalid['validSamples'], invalid['invalidSamples']), (4, 0, 4))
        self.assertIsNone(invalid['medianAbsRel'])
        json.dumps(invalid, allow_nan=False)

    def test_residuals_exclude_invalid_targets_and_reject_unpaired_shapes(self):
        stats = EVALUATE.residual_stats(np.array([2., 2., 2., 2., 4.]),
                                        np.array([np.nan, np.inf, 0., -1., 2.]))
        self.assertEqual((stats['validSamples'], stats['invalidSamples']), (1, 4))
        self.assertEqual(stats['medianAbsRel'], 1.)
        self.assertEqual(stats['medianAbsoluteSfmUnits'], 2.)
        json.dumps(stats, allow_nan=False)
        with self.assertRaises(ValueError):
            EVALUATE.residual_stats(np.array([1., 2.]), np.array([1.]))
        with self.assertRaises(ValueError):
            EVALUATE.residual_stats(np.ones((2, 2)), np.ones((2, 2)))

    def test_cli_never_fits_deliberately_disagreeing_heldout_ranges(self):
        # Exercise actual main(), serialization, masking and export. A held-out
        # target changed by 15x must stay bad; it cannot pull the fitted scale.
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            inference = directory / 'inference'
            inference.mkdir()
            yy, xx = np.indices((32, 64))
            prediction = (1 + xx / 64 + yy / 32).astype(np.float32)
            np.save(inference / 'raw.npy', prediction)
            Image.fromarray(np.full((32, 64, 3), [60, 100, 140], dtype=np.uint8)).save(inference / 'source.png')
            source_hash = hashlib.sha256((inference / 'source.png').read_bytes()).hexdigest()
            (inference / 'inference.json').write_text(json.dumps({'status': 'PASS', 'model': 'da2', 'sourceSha256': source_hash}))
            ids = np.arange(1, 201)
            held = EVALUATE.split_ids(ids)
            anchors = []
            for index, point_id in enumerate(ids):
                row, column = 2 + index // 40, index % 40
                value = float(prediction[row, column])
                anchors.append({'point3DId': int(point_id), 'erpNormalizedUv': [(column + .5) / 64, (row + .5) / 32],
                                'radialRangeSfm': value * (30 if held[index] else 2)})
            anchor_file = directory / 'anchors.json'
            anchor_file.write_text(json.dumps({'status': 'PASS', 'source': {'sha256': source_hash},
                                              'worldFromPanorama': np.eye(4).tolist(), 'anchors': anchors, 'coverage': {}}))
            output = directory / 'evaluation'
            process = subprocess.run([sys.executable, str(SCRIPT), str(inference), str(anchor_file), str(output)],
                                     capture_output=True, text=True, timeout=20)
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads((output / 'geometry.json').read_text())
            self.assertEqual(report['status'], 'PASS')
            self.assertAlmostEqual(report['calibration']['scale'], 2., places=10)
            self.assertAlmostEqual(report['training']['medianAbsRel'], 0., places=10)
            self.assertAlmostEqual(report['heldOut']['medianAbsRel'], 14 / 15, places=10)
            self.assertEqual(report['calibration']['heldOutSamples'], int(held.sum()))
            self.assertEqual(report['calibration']['trainingSamples'], int((~held).sum()))
            self.assertEqual(report['independentGeometry'], 'NOT RUN')
            self.assertGreater(report['points']['cloud'], 0)
            self.assertTrue((output / 'cloud.ply').is_file())
            self.assertLess(report['selfReprojection']['cloud']['maxPixelError'], 1e-10)


if __name__ == '__main__':
    unittest.main()
