import importlib.util
from pathlib import Path
import sys
import unittest
try:
    import numpy as np
    from PIL import Image
except ImportError:np=None
if np is not None:
    folder=Path(__file__).resolve().parents[1];sys.path.insert(0,str(folder))
    spec=importlib.util.spec_from_file_location('perspective',folder/'compare-perspective-depth.py');P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
@unittest.skipUnless(np is not None,'NumPy/Pillow required; perspective diagnostic NOT RUN')
class PerspectiveControlTests(unittest.TestCase):
    def test_perspective_sample_uses_corner_origin_and_never_wraps(self):
        a=np.arange(4,dtype=float).reshape(2,2)
        self.assertEqual(P.plane_sample(a,[.5,.5]),0);self.assertEqual(P.plane_sample(a,[1.5,1.5]),3);self.assertEqual(P.plane_sample(a,[1,1]),1.5)
        self.assertTrue(np.isnan(P.plane_sample(a,[-.01,.5])));self.assertTrue(np.isnan(P.plane_sample(a,[2,.5])))
    def test_inverse_camera_z_is_not_radial(self):
        fit={'convention':'inverse-camera-z','scale':1.,'offset':0.};ray=np.array([.6,0,.8])
        self.assertAlmostEqual(P.perspective_radial(.5,fit,ray),2.5)
        with self.assertRaises(ValueError):P.perspective_radial(.5,{**fit,'convention':'inverse-ray-range'},ray)
        with self.assertRaises(ValueError):P.perspective_radial(.5,fit,np.array([0,0,-1.]))
        self.assertTrue(np.isnan(P.perspective_radial(-1,fit,ray)))
    def test_camera_z_fit_records_actual_target_convention(self):
        values=np.linspace(.1,2,50);z=1/(.5*values+.2);fit=P.camera_z_fit(values,z)
        self.assertEqual(fit['convention'],'inverse-camera-z');self.assertAlmostEqual(fit['scale'],.5);self.assertAlmostEqual(fit['offset'],.2)
if __name__=='__main__':unittest.main()
