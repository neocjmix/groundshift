"""Rig contract tests; synthetic poses are fixtures, not reconstruction evidence."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'estimate-panorama-poses.py'
spec = importlib.util.spec_from_file_location('estimate_panorama_poses', SCRIPT)
RIG = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RIG)
try:
    import numpy as np
except ImportError:
    np = None
try:
    import pycolmap
except ImportError:
    pycolmap = None


def fixture():
    return {'schemaVersion': 1, 'kind': 'panorama-pinhole-crops',
            'intrinsics': RIG.PREPARE.intrinsics(512, 90),
            'crops': [{'file': f'images/pano_{p}_view_{view}.png', 'sourceId': f'pano_{p}',
                       'yawDegrees': yaw, 'pitchDegrees': 15,
                       'relativeCameraToPanoramaRotation': RIG.PREPARE.crop_rotation(yaw,15).tolist()}
                      for p in range(3) for view, yaw in enumerate((20,80,140))]}


@unittest.skipUnless(np is not None, 'NumPy unavailable; rig matrix checks NOT RUN')
class PanoramaRigContractTests(unittest.TestCase):
    def test_groups_each_physical_panorama_without_world_positions(self):
        intrinsic, groups = RIG.validate_crops(fixture())
        self.assertEqual(len(groups), 3)
        self.assertEqual([len(crops) for _, crops in groups], [3]*3)
        self.assertEqual(intrinsic['fx'], 256)
        self.assertNotIn('transform_matrix', groups[0][1][0])

    def test_rejects_incomplete_or_duplicate_virtual_camera_set(self):
        invalid = fixture()
        invalid['crops'].pop()
        with self.assertRaisesRegex(ValueError, 'same complete'):
            RIG.validate_crops(invalid)
        invalid = fixture()
        invalid['crops'].append(copy.deepcopy(invalid['crops'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate crop file'):
            RIG.validate_crops(invalid)

    def test_rejects_nonrigid_or_mislabeled_crop_rotation(self):
        for mutation in ('scale', 'reflection', 'label'):
            invalid = fixture()
            crop = invalid['crops'][0]
            if mutation == 'scale':
                crop['relativeCameraToPanoramaRotation'][0][0] *= 2
            elif mutation == 'reflection':
                crop['relativeCameraToPanoramaRotation'] = (-np.asarray(crop['relativeCameraToPanoramaRotation'])).tolist()
            else:
                crop['yawDegrees'] += 10
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                RIG.validate_crops(invalid)

    def test_rejects_traversal_and_insufficient_physical_baselines(self):
        invalid = fixture()
        invalid['crops'][0]['file'] = '../outside.png'
        with self.assertRaises(ValueError):
            RIG.validate_crops(invalid)
        invalid = fixture()
        invalid['crops'] = invalid['crops'][:3]
        with self.assertRaisesRegex(ValueError, 'three physical panoramas'):
            RIG.validate_crops(invalid)


@unittest.skipUnless(pycolmap is not None, 'PyCOLMAP unavailable; native rig checks NOT RUN')
class NativePanoramaRigTests(unittest.TestCase):
    def test_native_database_groups_sensors_with_analytic_rotation_and_zero_baseline(self):
        rotations = [RIG.PREPARE.crop_rotation(yaw, 15) for yaw in (20,80,140)]
        config = RIG.rig_config(pycolmap, rotations)
        self.assertTrue(config.cameras[0].ref_sensor)
        np.testing.assert_allclose(config.cameras[1].cam_from_rig.rotation.matrix(), rotations[1].T @ rotations[0], atol=1e-12)
        np.testing.assert_array_equal(config.cameras[1].cam_from_rig.translation, [0,0,0])
        with tempfile.TemporaryDirectory() as directory:
            with pycolmap.Database.open(Path(directory) / 'database.db') as db:
                for view in range(3):
                    camera_id = db.write_camera(pycolmap.Camera(model='PINHOLE',width=512,height=512,params=[256]*4))
                    for pano in range(3):
                        db.write_image(pycolmap.Image(name=f'view_{view:02d}/pano_{pano:06d}.png',camera_id=camera_id))
                pycolmap.apply_rig_config([config], db)
                self.assertEqual(db.num_rigs(), 1)
                self.assertEqual(db.num_frames(), 3)
                self.assertTrue(all(frame.num_data_ids() == 3 for frame in db.read_all_frames()))

    def test_rig_check_detects_camera_center_drift(self):
        rotations = [RIG.PREPARE.crop_rotation(yaw, 0) for yaw in (0,60,120)]
        mapping = {f'view_{i}': {'sourceId': 'synthetic_fixture', 'relativeCameraToPanoramaRotation': r.tolist()}
                   for i,r in enumerate(rotations)}
        camera = pycolmap.Camera(model='PINHOLE',width=512,height=512,params=[256]*4)
        class Image:
            has_pose = True
            camera_id = 1
            def __init__(self, index, center):
                self.name = f'view_{index}'
                self.pose = pycolmap.Rigid3d(pycolmap.Rotation3d(rotations[index]),np.asarray(center,dtype=float)).inverse()
            def cam_from_world(self):
                return self.pose
        class Model:
            cameras = {1: camera}
            images = {i: Image(i,[2,3,4]) for i in range(3)}
        intrinsic = RIG.PREPARE.intrinsics(512,90)
        self.assertEqual(RIG.rig_checks(Model, mapping, intrinsic)['status'], 'PASS')
        Model.images[1] = Image(1,[2.1,3,4])
        result = RIG.rig_checks(Model,mapping,intrinsic)
        self.assertEqual(result['status'], 'FAIL')
        self.assertAlmostEqual(result['maxCenterDeviation'],0.1)


if __name__ == '__main__':
    unittest.main()
