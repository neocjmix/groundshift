import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seine_alignment import (fit_pose_alignment, transform_points, transform_pose,
                             compose_alignment, load_physical_poses)


def rz(degrees):
    theta = np.radians(degrees)
    return np.array([[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])


def fixture():
    source = {}
    for i in range(8):
        pose = np.eye(4)
        pose[:3, 3] = [i, 0, 0]  # Deliberately collinear: centers alone cannot resolve roll.
        pose[:3, :3] = rz(2 * i)
        source[f'{1000 + i:05d}_real.jpg'] = pose
    angle = np.radians(37)
    rotation = rz(71) @ np.array([[1, 0, 0], [0, np.cos(angle), -np.sin(angle)], [0, np.sin(angle), np.cos(angle)]])
    transform = dict(scale=2.4, rotation=rotation.tolist(), translation=[12, -3, 7])
    return source, {key: transform_pose(pose, transform) for key, pose in source.items()}, transform


class SeineAlignmentTests(unittest.TestCase):
    def test_collinear_centers_use_actual_orientations_to_recover_roll(self):
        source, reference, expected = fixture()
        result = fit_pose_alignment(source, reference)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['inlierCount'], 8)
        self.assertEqual(len(result['heldCheck']['poses']), 2)
        for key in expected:
            np.testing.assert_allclose(result['transform'][key], expected[key], atol=1e-12)
        for record in result['heldCheck']['poses']:
            self.assertLess(record['centerErrorSteps'], 1e-12)
            self.assertLess(record['orientationErrorDegrees'], 1e-10)

    def test_one_training_pose_outlier_is_reported_and_cannot_bias_scale(self):
        source, reference, expected = fixture()
        key = sorted(reference)[3]
        reference[key] = reference[key].copy()
        reference[key][:3, 3] += [20, -50, 12]
        reference[key][:3, :3] = rz(30) @ reference[key][:3, :3]
        result = fit_pose_alignment(source, reference)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['inlierCount'], 7)
        self.assertFalse(next(row for row in result['residuals'] if row['sourceId'] == key)['inlier'])
        self.assertAlmostEqual(result['transform']['scale'], expected['scale'])

    def test_small_independent_pose_noise_passes_without_exact_fit_claim(self):
        source, reference, _ = fixture()
        rng = np.random.default_rng(17)
        for pose in reference.values():
            pose[:3, 3] += rng.normal(0, 0.01, 3)
            pose[:3, :3] = rz(rng.normal(0, 0.05)) @ pose[:3, :3]
        result = fit_pose_alignment(source, reference)
        self.assertEqual(result['status'], 'PASS')
        self.assertGreater(max(row['centerErrorSfm'] for row in result['heldCheck']['poses']), 0.001)

    def test_bad_held_pose_retains_fail_even_if_final_refit_finds_consensus(self):
        source, reference, _ = fixture()
        reference[sorted(reference)[1]][:3, 3] += [0, 10, 0]
        result = fit_pose_alignment(source, reference)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['heldCheck']['status'], 'FAIL')
        self.assertEqual(result['inlierCount'], 7)

    def test_stationary_shared_centers_do_not_define_scale(self):
        source, reference, _ = fixture()
        for pose in source.values():
            pose[:3, 3] = 0
        with self.assertRaisesRegex(ValueError, 'Degenerate'):
            fit_pose_alignment(source, reference)

    def test_nonrigid_inconsistent_overlap_is_rejected(self):
        source, reference, _ = fixture()
        for i, pose in enumerate(reference.values()):
            pose[:3, 3] += [0, 8 * (i % 2), i * i]
        with self.assertRaises(ValueError):
            fit_pose_alignment(source, reference)

    def test_reflected_rotation_nonfinite_and_nonpositive_scale_rejected(self):
        source, reference, transform = fixture()
        for wrong in [np.diag([-1, 1, 1, 1]), np.full((4, 4), np.nan)]:
            with self.assertRaises(ValueError):
                transform_pose(wrong, transform)
        with self.assertRaises(ValueError):
            transform_points([[1, 2, 3]], {**transform, 'scale': -1})
        reflected = {key: value.copy() for key, value in reference.items()}
        for pose in reflected.values():
            pose[:3, 3] *= -1
        with self.assertRaises(ValueError):
            fit_pose_alignment(source, reflected)

    def test_composition_order_and_pose_rotation_do_not_include_scale(self):
        source, _, first = fixture()
        second = dict(scale=0.3, rotation=rz(-33).tolist(), translation=[-4, 6, 10])
        combined = compose_alignment(first, second)
        pose = next(iter(source.values()))
        result = transform_pose(pose, combined)
        np.testing.assert_allclose(result, transform_pose(transform_pose(pose, second), first), atol=1e-12)
        np.testing.assert_allclose(result[:3, :3].T @ result[:3, :3], np.eye(3), atol=1e-12)
        points = np.array([[1., 2, 3], [-2, 4, -9]])
        before = points.copy()
        np.testing.assert_allclose(transform_points(points, combined), transform_points(transform_points(points, second), first))
        np.testing.assert_array_equal(points, before)

    def test_partial_source_overlap_and_changed_local_indexes_use_source_ids(self):
        source, reference, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_job(root, source, reverse=True)
            poses, hashes = load_physical_poses(root)
            self.assertEqual(set(poses), set(source))
            self.assertEqual(len(hashes), 8)
            self.assertEqual(fit_pose_alignment(poses, reference)['status'], 'PASS')
            report_path = root / 'sfm/report.json'
            report_path.write_text(json.dumps(dict(status='PASS', fullRegistration='FAIL')))
            with self.assertRaisesRegex(ValueError, 'complete'):
                load_physical_poses(root)

    @staticmethod
    def write_job(root, poses, reverse=False):
        for folder in ['sfm', 'sfm-inputs', 'anchors']:
            (root / folder).mkdir(parents=True)
        keys = sorted(poses, reverse=reverse)
        (root / 'sfm/report.json').write_text(json.dumps(dict(status='PASS', fullRegistration='PASS')))
        (root / 'anchors/report.json').write_text(json.dumps(dict(status='PASS')))
        (root / 'sfm-inputs/crops.json').write_text(json.dumps(dict(
            sourcePanoramas=[dict(sourceId=key, sha256=f'{i:064x}') for i, key in enumerate(sorted(poses))],
            crops=[dict(sourceIndex=i, sourceId=key) for i, key in enumerate(keys)])))
        (root / 'anchors/physical.json').write_text(json.dumps({str(i): dict(pose=poses[key].tolist()) for i, key in enumerate(keys)}))

    def test_cli_hash_mismatch_preserves_failure_without_overwriting_models(self):
        source, reference, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_job(root / 'source', source)
            self.write_job(root / 'reference', reference, reverse=True)
            path = root / 'reference/sfm-inputs/crops.json'
            changed = json.loads(path.read_text())
            changed['sourcePanoramas'][0]['sha256'] = 'f' * 64
            path.write_text(json.dumps(changed))
            before = path.read_bytes()
            output = root / 'result.json'
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'seine_alignment.py'),
                       str(root / 'source'), str(root / 'reference'), str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            report = json.loads(output.read_text())
            self.assertEqual(report['status'], 'FAIL')
            self.assertIn('different original bytes', report['error'])
            self.assertEqual(len(report['inputDigests']['source']), 4)
            self.assertEqual(path.read_bytes(), before)
            previous = output.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), previous)


if __name__ == '__main__':
    unittest.main()
