"""Fixed-rig and sparse pair diagnostics; no learned model quality claims."""
import importlib.util
from pathlib import Path
import sys
import unittest

try:
    import numpy as np
except ImportError:
    np = None

SCRIPT = Path(__file__).resolve().parents[1] / 'extract-panoramic-pair-anchors.py'
if np is not None:
    spec = importlib.util.spec_from_file_location('pair_anchors', SCRIPT)
    PAIR = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(PAIR)


@unittest.skipUnless(np is not None, 'NumPy required; pair sparse diagnostics NOT RUN')
class PairAnchorTests(unittest.TestCase):
    def test_crop_rotation_recovers_one_physical_panorama_pose(self):
        pose = np.eye(4)
        pose[:3, 3] = [2, 3, 4]
        yaw = np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]])
        crops, frames = [], []
        for i, rotation in enumerate((np.eye(3), yaw)):
            crop = pose.copy()
            crop[:3, :3] = pose[:3, :3] @ rotation
            crops.append({'file': f'images/crop{i}.png', 'sourceId': 'one.jpg',
                          'relativeCameraToPanoramaRotation': rotation.tolist()})
            frames.append({'file_path': f'images/crop{i}.png',
                           'transform_matrix': (crop @ np.diag([1, -1, -1, 1])).tolist()})
        _, poses, deviation = PAIR.derive_poses(crops, frames)
        np.testing.assert_allclose(poses['one.jpg'], pose)
        self.assertEqual(deviation, 0)
        frames[-1]['transform_matrix'][0][3] += .01
        with self.assertRaisesRegex(ValueError, 'co-located'):
            PAIR.derive_poses(crops, frames)

    def test_pair_geometry_uses_two_actual_centers_not_camera_orientation(self):
        first, second = np.eye(4), np.eye(4)
        second[:3, 3] = [2, 0, 0]
        ranges, angle = PAIR.pair_geometry(np.array([1., 0., 1.]), first, second)
        np.testing.assert_allclose(ranges, np.sqrt(2))
        self.assertAlmostEqual(angle, np.pi / 2)
        second[:3, :3] = np.diag([-1, 1, -1])
        np.testing.assert_allclose(PAIR.pair_geometry(np.array([1., 0., 1.]), first, second)[0], ranges)
        self.assertAlmostEqual(PAIR.pair_geometry(np.array([1., 0., 1.]), first, second)[1], angle)
        with self.assertRaises(ValueError):
            PAIR.pair_geometry(np.zeros(3), first, second)

    def test_sampling_band_exposes_weak_parallax_and_resolution_dependence(self):
        angles = np.radians([0., 1., 10., 90.])
        band = PAIR.sampling_relative_band(angles, .001)
        self.assertTrue(np.isinf(band[0]))
        self.assertGreater(band[1], band[2])
        self.assertGreater(band[2], band[3])
        higher_resolution = PAIR.sampling_relative_band(angles[1:], .001, 1092, 2184)
        self.assertTrue(np.all(higher_resolution < band[1:]))
        self.assertTrue(np.all(PAIR.sampling_relative_band(angles[1:], .002) > band[1:]))
        with self.assertRaises(ValueError):
            PAIR.sampling_relative_band(angles, .001, 546, 800)

    def test_point_holdout_is_identical_across_panorama_subsets(self):
        left, right = [13, 27, 51, 99, 17], [51, 99, 17, 70]
        for point_id in set(left) & set(right):
            self.assertEqual(PAIR.held_out(point_id), PAIR.held_out(np.int64(point_id)))
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            spec = importlib.util.spec_from_file_location('evaluate_contract', SCRIPT.with_name('evaluate-panoramic-depth.py'))
            evaluator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(evaluator)
        finally:
            sys.path.pop(0)
        point_ids = np.arange(1, 1001)
        held = np.asarray([PAIR.held_out(i) for i in point_ids])
        np.testing.assert_array_equal(held, evaluator.split_ids(point_ids))
        self.assertTrue(held.any())
        self.assertTrue((~held).any())

    def test_angular_coverage_keeps_seam_edges_distinct(self):
        coverage = PAIR.angular_coverage([{'erpNormalizedUv': [u, .5], 'latitudeDegrees': 0.} for u in (.001, .999)])
        self.assertEqual(coverage['occupiedBins'], 2)
        self.assertEqual(coverage['countsNorthToSouth'][3][0], 1)
        self.assertEqual(coverage['countsNorthToSouth'][3][-1], 1)

    def test_tolerance_record_does_not_promote_internal_fit_to_accuracy(self):
        sparse = {'createdAt': 'fixed', 'operation': 'sparse-only', 'toleranceRecommendation': {'kind': 'diagnostic'},
                  'commonTracks': 2, 'pairTriangulationDegrees': {}, 'firstOrderRelativeSamplingBand': {}}
        record = PAIR.tolerance_record(sparse)
        self.assertEqual(record['declaredAt'], 'fixed')
        self.assertTrue(record['p2Acceptance'].startswith('NOT RUN'))
        self.assertIn('insufficient for fusion acceptance', record['diagnosticDecision'])


if __name__ == '__main__':
    unittest.main()
