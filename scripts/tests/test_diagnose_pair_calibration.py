import importlib.util
from pathlib import Path
import sys
import unittest

try:
    import numpy as np
    from PIL import Image
except ImportError:
    np=None

if np is not None:
    folder=Path(__file__).resolve().parents[1];sys.path.insert(0,str(folder))
    spec=importlib.util.spec_from_file_location('diagnose',folder/'diagnose-pair-calibration.py')
    D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)


@unittest.skipUnless(np is not None,'NumPy and Pillow required; calibration reprojection NOT RUN')
class CalibrationDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.camera={'params':[256,256,256,256],'width':512,'height':512,'camFromWorld':[[1,0,0,-1],[0,1,0,0],[0,0,1,0]]}
        self.ray=np.array([0.,0.,1.]);self.center=np.zeros(3);self.observed=[204.8,256]

    def test_pinhole_pixels_keep_colmap_corner_origin(self):
        np.testing.assert_allclose(D.unit_bearing([256,256],[256,256,256,256]),[0,0,1])
        r=np.array([-255.5/256,-255.5/256,1]);r/=np.linalg.norm(r)
        np.testing.assert_allclose(D.unit_bearing([.5,.5],[256,256,256,256]),r)
        with self.assertRaises(ValueError):D.unit_bearing([1,2],[0,256,256,256])

    def test_measured_translation_and_radial_range_project_to_observed_target(self):
        result=D.evaluate_range(5,self.ray,self.center,self.camera,self.observed)
        self.assertTrue(result['valid']);self.assertTrue(result['insideImage']);self.assertAlmostEqual(result['pixelError'],0)
        self.assertLess(result['angularErrorDegrees'],1e-5)
        np.testing.assert_allclose(result['xy'],self.observed)

    def test_wrong_depth_moves_along_real_pinhole_epipolar_direction(self):
        result=D.evaluate_range(10,self.ray,self.center,self.camera,self.observed)
        self.assertAlmostEqual(result['pixelError'],25.6)
        self.assertAlmostEqual(result['xy'][1],self.observed[1])

    def test_invalid_ranges_and_behind_camera_are_counted(self):
        for radial in [np.nan,np.inf,0,-2]:self.assertFalse(D.evaluate_range(radial,self.ray,self.center,self.camera,self.observed)['valid'])
        self.assertFalse(D.project_world([0,0,-5],self.camera,self.observed)['valid'])

    def test_outside_target_image_is_valid_error_not_silently_rejected(self):
        result=D.evaluate_range(.1,self.ray,self.center,self.camera,self.observed)
        self.assertTrue(result['valid']);self.assertFalse(result['insideImage'])
        summary=D.statistics([{'methods':{'common':result}}],'common')
        self.assertEqual(summary['validSamples'],1);self.assertEqual(summary['outOfImageSamples'],1)
        self.assertGreater(summary['medianPixels'],2000)

    def test_observed_ray_sfm_control_matches_point_control_for_exact_observations(self):
        a=D.evaluate_range(5,self.ray,self.center,self.camera,self.observed)
        b=D.project_world([0,0,5],self.camera,self.observed)
        self.assertEqual(a,b)

    def test_selection_uses_central_normalized_bearing_and_stable_name_tie(self):
        cameras={name:{'params':[256,256,256,256]} for name in ['a','b','edge']}
        observations=[{'image':'edge','xyCornerOrigin':[500,500]},{'image':'b','xyCornerOrigin':[256,256]},{'image':'a','xyCornerOrigin':[256,256]}]
        self.assertEqual(D.select_observation(observations,cameras)['image'],'a')
        with self.assertRaises(ValueError):D.select_observation([],cameras)

    def test_common_fit_excludes_same_holdouts_and_nonshared_points(self):
        ids=[np.arange(1,151),np.arange(1,121)];prediction=[np.linspace(.1,2,len(x)) for x in ids];radial=[2*prediction[0],3*prediction[1]]
        common,held,fits=D.common_fits(ids,prediction,radial,'da2')
        np.testing.assert_array_equal(common,np.arange(1,121));self.assertTrue(held.any())
        changed_pred=[x.copy() for x in prediction];changed_radial=[x.copy() for x in radial]
        for i,group in enumerate(ids):
            excluded=np.isin(group,common[held])|~np.isin(group,common)
            changed_pred[i][excluded]*=1000;changed_radial[i][excluded]*=.001
        _,other_held,other=D.common_fits(ids,changed_pred,changed_radial,'da2')
        np.testing.assert_array_equal(held,other_held)
        for original,after in zip(fits,other):self.assertEqual(original,after)
        self.assertAlmostEqual(fits[0]['scale'],2);self.assertAlmostEqual(fits[1]['scale'],3)

    def test_duplicate_track_ids_rejected(self):
        with self.assertRaises(ValueError):D.common_fits([[1,1],[1]],[np.ones(2),np.ones(1)],[np.ones(2),np.ones(1)],'da2')

    def test_paired_statistics_disclose_invalid_exclusions(self):
        valid=lambda error:dict(valid=True,insideImage=True,pixelError=error,angularErrorDegrees=0)
        invalid=dict(valid=False,insideImage=False,pixelError=None,angularErrorDegrees=None)
        rows=[{'methods':{'original':valid(3),'common':valid(1)}},{'methods':{'original':valid(2),'common':invalid}}]
        summary=D.statistics(rows,'common');paired=D.paired_statistics(rows)
        self.assertEqual(summary['samples'],2);self.assertEqual(summary['invalidSamples'],1)
        self.assertEqual(paired['pairedValidSamples'],1);self.assertEqual(paired['excludedPairs'],1)
        self.assertEqual(paired['improved'],1);self.assertEqual(paired['medianDeltaPixels'],-2)

if __name__=='__main__':unittest.main()
