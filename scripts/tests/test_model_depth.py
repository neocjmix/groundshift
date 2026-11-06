import sys
import unittest
import subprocess
import tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model_depth import fit_depth,apply_depth,range_to_z,outside_camera_proximity


class ModelDepthTests(unittest.TestCase):
    def test_affine_radial_recovers_offset_and_resists_outliers(self):
        x=np.linspace(.02,.98,100);target=12*x+3;target[::10]+=100
        fit=fit_depth(x,target,'affine-radial')
        np.testing.assert_allclose([fit['scale'],fit['offset']],[12,3],atol=1e-4)

    def test_scale_only_does_not_introduce_offset(self):
        x=np.linspace(1,10,100)
        for kind in ['scale-radial','scale-camera-z']:
            fit=fit_depth(x,x*7,kind);np.testing.assert_allclose(apply_depth(x,fit,kind),x*7);self.assertEqual(fit['offset'],0)

    def test_z_and_radial_are_distinct(self):
        rays=np.array([[0,0,1],[.6,0,.8]])
        np.testing.assert_allclose(range_to_z(np.array([10,10]),rays),[10,8])

    def test_conventions_cannot_be_silently_substituted(self):
        fit=fit_depth(np.arange(1,40),np.arange(1,40)*2,'scale-radial')
        with self.assertRaises(ValueError):apply_depth(np.ones(3),fit,'scale-camera-z')
        with self.assertRaises(ValueError):fit_depth(np.arange(1,40),np.arange(1,40),'inverse-depth')

    def test_invalid_and_negative_distance_are_not_points(self):
        fit=dict(convention='affine-radial',scale=2,offset=-1,units='sfm-arbitrary',evidence='synthetic test')
        self.assertTrue(np.isnan(apply_depth(np.array([0,np.nan]),fit,'affine-radial')).all())
        with self.assertRaises(ValueError):range_to_z(np.array([1]),np.array([[0,0,2]]))

    def test_proximity_exclusion_is_invariant_under_shared_rigid_transform(self):
        points=np.array([[.001,0,0],[1,0,0],[3.1,0,0]]);centers=np.array([[0,0,0],[3,0,0]])
        expected=np.array([False,True,False]);rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]]);translation=np.array([10,20,30])
        np.testing.assert_array_equal(outside_camera_proximity(points,centers,.4),expected)
        np.testing.assert_array_equal(outside_camera_proximity(points@rotation.T+translation,centers@rotation.T+translation,.4),expected)
        self.assertTrue(outside_camera_proximity(points,centers,0).all())

    def test_blocked_candidate_never_imports_model_or_creates_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'attempt'
            result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'infer-street-model.py'),'depthmaster',str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2);self.assertIn('license chain',result.stderr);self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
