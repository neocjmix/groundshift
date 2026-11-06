"""Photometry fixtures prove denominator/alpha semantics, not model quality."""
from pathlib import Path
import importlib.util
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('measure',Path(__file__).resolve().parents[1]/'measure-street.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


class StreetMeasurementTests(unittest.TestCase):
    def test_exact_rgb_is_explicit_infinite_psnr(self):
        rgb=np.full((2,2,3),100,np.uint8);rgba=np.full((2,2,4),100,np.uint8);rgba[:,:,3]=255
        r=M.metrics(rgb,rgba,np.ones((2,2),bool));self.assertEqual(r['mae'],0);self.assertTrue(r['exactMatch']);self.assertIsNone(r['psnrDb']);self.assertEqual(r['opacityCoverage95'],1)

    def test_holes_stay_in_error_denominator(self):
        rgb=np.full((2,2,3),100,np.uint8);rgba=np.zeros((2,2,4),np.uint8)
        r=M.metrics(rgb,rgba,np.ones((2,2),bool));self.assertEqual(r['pixelCount'],4);self.assertEqual(r['mae'],27);self.assertEqual(r['opacityCoverage95'],0)

    def test_selected_band_only_and_no_uint_wrap(self):
        rgb=np.zeros((2,2,3),np.uint8);rgba=np.full((2,2,4),255,np.uint8);mask=np.array([[True,False],[False,False]])
        r=M.metrics(rgb,rgba,mask);self.assertEqual(r['mae'],255);self.assertEqual(r['pixelCount'],1)

    def test_partial_alpha_is_composited_not_silently_discarded(self):
        rgb=np.full((1,1,3),100,np.uint8);rgba=np.array([[[100,100,100,128]]],np.uint8)
        r=M.metrics(rgb,rgba,np.ones((1,1),bool));self.assertEqual(r['mae'],13);self.assertEqual(r['opacityCoverage95'],0);self.assertAlmostEqual(r['meanOpacity'],128/255)

    def test_empty_or_mismatched_selection_fails(self):
        rgb=np.zeros((2,2,3),np.uint8);rgba=np.zeros((2,2,4),np.uint8)
        with self.assertRaises(ValueError):M.metrics(rgb,rgba,np.zeros((2,2),bool))
        with self.assertRaises(ValueError):M.metrics(rgb,rgba,np.ones((2,2),np.uint8))
        with self.assertRaises(ValueError):M.metrics(rgb,rgba[:1],np.ones((2,2),bool))


if __name__=='__main__':unittest.main()
