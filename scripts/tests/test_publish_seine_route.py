"""Publication-boundary fixtures only; no native inference/rendering claims."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('publisher', Path(__file__).parents[1] / 'publish-seine-route.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.coordinator = self.repo / 'data/jobs/seine'
        self.source = self.coordinator / 'route-world-001'
        self.child = self.source / 'route/segments/segment-988-989'
        self.child.mkdir(parents=True)
        self.write('coverage.json', dict(status='PASS', segments=1, sourceCount=2, firstRank=988, lastRank=989, targetSourceCount=876, sourceGpsCoverageMeters=2.5, exportedAt='2026-11-07T00:00:00Z'))
        world = dict(id='seine-full-route', route=dict(path='route/index.json'), coordinates=dict(unit='arbitrary'))
        self.write('world.json', world)
        self.write('cameras.json', dict(frames=[dict(image=f'panorama-rank-{rank}') for rank in [988, 989]]))
        self.write('route/index.json', dict(segments=[dict(id='segment-988-989', world='segments/segment-988-989/world.json')]))
        self.write('route/segments/segment-988-989/world.json', dict(assets=[dict(format='spz', path='scene.spz')], paging=dict(path='rad/index.json'), coordinates=dict(unit='arbitrary'), navigation=dict(camerasPath='cameras.json')))
        self.write('route/segments/segment-988-989/cameras.json', dict(frames=[]))
        for base in [self.source, self.child]:
            (base / 'SOURCE_LICENSE').write_text('Fixture attribution; not a rendered scene')
            (base / 'scene.spz').write_bytes(b'fixture, not actual splats')
        (self.child / 'rad').mkdir()
        self.rad = self.child / 'rad/scene.rad'
        self.rad.write_bytes(b'fixture RAD bytes')
        self.write('route/segments/segment-988-989/rad/index.json', dict(kind='spark-rad', root='scene.rad', files=[dict(path='scene.rad', bytes=self.rad.stat().st_size, sha256=publisher.digest(self.rad))]))
        publisher.atomic_json(self.coordinator / 'route-run.json', dict(exports=[dict(path=str(self.source), status='PASS', segments=1)]))
        for name, value in [('worlds/catalog.json', dict(scenes=[dict(id='historical', createdAt='earlier')])), ('experiments/lab/timeline.json', dict(entries=[dict(id='historical-failure')])), ('experiments/tourist-streaming/summary.json', dict(stages=[dict(title='retained failure', status='FAIL')], deviceFeedback=dict(status='USER_REPORTED_RESOLVED')))]:
            publisher.atomic_json(self.repo / 'public' / name, value)
        publisher.atomic_json(self.repo / 'scripts/observation-worlds.json', dict(worlds=[], files=[]))
        preview = self.repo / 'public/worlds/paris-58m-lod-compact/preview.jpg'
        preview.parent.mkdir(parents=True)
        preview.write_bytes(b'fixture, not an image')
        (self.repo / 'deploy').mkdir()
        (self.repo / 'deploy/Dockerfile.github').write_text('COPY --from=baseline /out /srv\n')

    def write(self, name, value):
        publisher.atomic_json(self.source / name, value)

    def test_selected_files_reject_partial_and_corrupted_paging(self):
        partial = self.source.with_name('route-world-001.partial')
        with self.assertRaises(ValueError):
            publisher.selected_files(partial)
        self.rad.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            publisher.selected_files(self.source)

    def test_unfinished_export_or_camera_gap_is_not_published(self):
        coverage = publisher.read(self.source / 'coverage.json')
        coverage['status'] = 'RUNNING'
        self.write('coverage.json', coverage)
        with self.assertRaises(ValueError):
            publisher.selected_files(self.source)
        coverage['status'] = 'PASS'
        self.write('coverage.json', coverage)
        self.write('cameras.json', dict(frames=[dict(image='panorama-rank-989')]))
        with self.assertRaisesRegex(ValueError, 'Camera path'):
            publisher.selected_files(self.source)

    def test_private_metadata_is_rejected_before_public_changes(self):
        self.write('world.json', {**publisher.read(self.source / 'world.json'), 'notes': '/Users/private/example'})
        with self.assertRaisesRegex(ValueError, 'Private reference'):
            publisher.prepare(self.repo, self.coordinator, self.source)
        self.assertFalse((self.repo / 'public/worlds/seine-full-route').exists())

    def test_prepare_preserves_history_source_and_pending_idempotence(self):
        report = publisher.prepare(self.repo, self.coordinator, self.source)
        self.assertEqual(report['status'], 'PREPARED')
        summary = publisher.read(self.repo / 'public/experiments/tourist-streaming/summary.json')
        self.assertIn(dict(title='retained failure', status='FAIL'), summary['stages'])
        self.assertEqual(summary['deviceFeedback']['status'], 'USER_REPORTED_RESOLVED')
        self.assertEqual(summary['expansion']['fullRouteBrowserAcceptance'], 'NOT RUN')
        self.assertEqual(publisher.prepare(self.repo, self.coordinator, self.source), report)
        self.assertEqual(publisher.digest(self.source / 'world.json'), publisher.digest(Path(report['sourceWorld']) / 'world.json'))

    def test_atomic_write_does_not_modify_a_hardlinked_source(self):
        source = self.source / 'scene.spz'
        target = self.repo / 'linked'
        target.hardlink_to(source)
        original = source.read_bytes()
        publisher.atomic_bytes(target, b'new bytes')
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(target.read_bytes(), b'new bytes')


if __name__ == '__main__':
    unittest.main()
