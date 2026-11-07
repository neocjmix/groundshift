"""Synthetic planning/coordinate/reuse boundaries, not street accuracy proof."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

SCRIPTS=Path(__file__).parents[1];sys.path.insert(0,str(SCRIPTS))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,SCRIPTS/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
R=module('seine_route','seine-route.py');A=module('seine_acquire','acquire-tourist-route.py');P=module('seine_paris','paris-pipeline.py')


class SeineRouteTests(unittest.TestCase):
    def test_all_876_sources_covered_by_55_connected_fixed_windows(self):
        starts=R.windows();self.assertEqual(len(starts),55);self.assertEqual(starts[0],180)
        seen=set(range(180,204));previous=[180]
        for first in starts[1:]:
            self.assertGreaterEqual(max(len(set(range(first,first+24))&set(range(p,p+24))) for p in previous),6)
            seen.update(range(first,first+24));previous.append(first)
        self.assertEqual(seen,set(range(876)));self.assertEqual(len(starts),len(set(starts)))

    def test_no_insufficient_overlap_or_out_of_range_baseline(self):
        for args in ((876,180,24,20),(10,180,24,16)):
            with self.assertRaises(ValueError):R.windows(*args)

    def test_quaternion_roundtrip_including_half_turns(self):
        for q in ([0,0,0,1],[1,0,0,0],[0,1,0,0],[0,0,1,0],np.array([1,2,3,4])/np.sqrt(30)):
            matrix=R.quaternion_matrix(q)
            np.testing.assert_allclose(R.quaternion_matrix(R.matrix_quaternion(matrix)),matrix,atol=1e-14)
        with self.assertRaises(ValueError):R.matrix_quaternion(np.diag([1,1,-1]))
        with self.assertRaises(ValueError):R.quaternion_matrix([0,0,0,2])

    def test_viewer_alignment_applies_asset_transform_exactly_once(self):
        a=dict(position=[3,4,5],quaternion=[0,0,1,0],scale=2)
        b=dict(position=[-2,9,4],quaternion=[1,0,0,0],scale=3)
        raw=dict(scale=1.2,rotation=R.quaternion_matrix([0,1,0,0]).tolist(),translation=[4,6,8])
        combined=R.segment_to_route(a,b,raw);point=np.array([[7.,8.,9.]])
        from seine_alignment import transform_points
        first=transform_points(point,R.similarity(a));actual=transform_points(first,combined)
        expected=transform_points(transform_points(point,raw),R.similarity(b))
        np.testing.assert_allclose(actual,expected,atol=1e-12)

    def test_acquisition_rejects_gaps_and_failed_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder);path=source/'acquisition.json'
            for record in (dict(status='FAIL',frames=[]),dict(status='PASS',frames=[dict(rank=x) for x in [3,4,6]])):
                path.write_text(json.dumps(record))
                with self.assertRaises(ValueError):P.acquisition(source)
            path.write_text(json.dumps(dict(status='PASS',frames=[dict(rank=x) for x in [3,4,5]])))
            self.assertEqual(len(P.acquisition(source)['frames']),3)

    def test_actual_cached_jpeg_reused_without_network_and_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cache=root/'cache';(cache/'images').mkdir(parents=True)
            image=cache/'images/original.jpg';Image.new('RGB',(16,8),(30,80,120)).save(image)
            digest=hashlib.sha256(image.read_bytes()).hexdigest()
            (cache/'acquisition.json').write_text(json.dumps(dict(status='PASS',frames=[dict(id='abc',rank=4,file='images/original.jpg',sha256=digest)])))
            route=root/'route.json';route.write_text(json.dumps(dict(collection='test',images=[dict(id='abc',rank=4,hdUrl='https://example.invalid/image.jpg',license='etalab-2.0',dimensions=[16,8],hdSha256=digest)])))
            with patch.object(A.urllib.request,'urlopen',side_effect=AssertionError('No network for validated cache')):
                result=A.acquire(route,root/'output',0,1,[cache])
                self.assertEqual(result['status'],'PASS');self.assertTrue(result['frames'][0]['reusedVerifiedOriginal'])
                self.assertEqual(hashlib.sha256((root/'output'/result['frames'][0]['file']).read_bytes()).hexdigest(),digest)
                image.write_bytes(b'corrupted')
                failed=A.acquire(route,root/'failed',0,1,[cache]);self.assertEqual(failed['status'],'FAIL')
                self.assertIn('checksum',failed['error']);self.assertEqual(failed['frames'],[])

    def test_failed_export_preserved_and_retry_does_not_repeat_native_work(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);state=dict(records=[dict(firstRank=1,lastRank=24),dict(firstRank=17,lastRank=40)],exports=[])
            def fail(_root,_records,target):
                target.mkdir();(target/'diagnostic.txt').write_text('interrupted');raise RuntimeError('export interrupted')
            with patch.object(R,'export_route',side_effect=fail):
                with self.assertRaisesRegex(RuntimeError,'interrupted'):R.snapshot(root,state)
            self.assertFalse((root/'route-world-002').exists());self.assertEqual(len(list(root.glob('*.partial-*'))),1)
            report=dict(segments=2,sourceCount=40,firstRank=1,lastRank=40,sourceGpsCoverageMeters=99)
            def succeed(_root,_records,target):target.mkdir();R.write(target/'coverage.json',report);return report
            with patch.object(R,'export_route',side_effect=succeed) as call:
                R.snapshot(root,state);R.snapshot(root,state);self.assertEqual(call.call_count,1)
            self.assertEqual(len(state['exports']),1);self.assertEqual(len(list(root.glob('*.partial-*'))),1)

    def test_stage_spawn_failure_is_not_left_running_or_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            job=Path(folder)
            with patch.object(R.subprocess,'run',side_effect=FileNotFoundError('missing native binary')):
                with self.assertRaises(FileNotFoundError):R.run_stage(job,'native',['missing'])
            record=R.read(job/'runner.json');self.assertEqual(record['status'],'FAIL')
            self.assertEqual(record['stages'][0]['status'],'FAIL')
            with self.assertRaisesRegex(RuntimeError,'preserve'):R.run_stage(job,'native',['missing'])


if __name__=='__main__':unittest.main()
