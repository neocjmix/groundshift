"""Filesystem/process workflow fixtures, not reconstruction or Railway evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('watcher', Path(__file__).parents[1] / 'watch-seine-publication.py')
watcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watcher)


class WatcherTests(unittest.TestCase):
    def test_generated_docs_keep_queued_pointer_distinct_from_dispatch(self):
        note = watcher.dispatch_description('CONNECTOR QUEUE')
        self.assertIn('DISPATCH_PENDING', note)
        self.assertIn('Git push alone is not Railway dispatch', note)
        self.assertNotIn('verified branch-follow', note)
        self.assertIn('still requires independent verification', watcher.dispatch_description('VERIFIED GIT AUTODEPLOY'))

    def test_git_push_queues_connector_work_without_claiming_delivery(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            active = dict(segments=2, phase='COMMITTED', attempt=name, commit='a' * 40,
                          overlay=dict(assembledInventory='next.inventory.json', changedFiles=[dict(path='www/worlds/seine-full-route/coverage.json', bytes=1, sha256='b' * 64)]))
            state = dict(active=active, submissions={}, deliveryMode='CONNECTOR QUEUE', baseInventory='before')
            with patch.object(watcher, 'run', return_value=''):
                watcher.advance(root, state, root / 'state.json')
            queued = json.loads((root / 'publication-dispatch/002.json').read_text())
            self.assertEqual(queued['status'], 'DISPATCH_PENDING')
            self.assertEqual(queued['commit'], 'a' * 40)
            self.assertNotIn('dispatchedAt', queued)
            self.assertFalse((root / 'publication-receipts/002.json').exists())
            with patch.object(watcher, 'public_hash', side_effect=ValueError('not live')):
                watcher.check_submissions(root, state, root / 'state.json')
            self.assertFalse((root / 'publication-receipts/002.json').exists())
            with patch.object(watcher, 'public_hash', side_effect=lambda value: value):
                watcher.check_submissions(root, state, root / 'state.json')
            receipt = json.loads((root / 'publication-receipts/002.json').read_text())
            self.assertEqual(receipt['status'], 'DELIVERED PUBLIC HASHES')
            self.assertEqual(receipt['railwayProviderStatus'], 'NOT RUN by background worker')

    def test_only_completed_atomic_exports_are_selected_in_order(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self.assertIsNone(watcher.next_export(root, {}))
            (root / 'route-run.json').write_text(json.dumps(dict(exports=[
                dict(segments=3, status='PASS'), dict(segments=2, status='PASS'),
                dict(segments=1, status='RUNNING')])))
            self.assertEqual(watcher.next_export(root, {})['segments'], 2)
            self.assertEqual(watcher.next_export(root, {'2': dict(phase='PUSHED')})['segments'], 3)
            (root / 'publication-receipts').mkdir()
            (root / 'publication-receipts/003.json').write_text('{}')
            self.assertIsNone(watcher.next_export(root, {'2': {}}))

    def test_pointer_is_idempotent_and_rejects_replacement_or_layer_overflow(self):
        base = f'FROM {watcher.IMAGE}\nCOPY deploy/Caddyfile /etc/caddy/Caddyfile\nCOPY --from=old /out/www /srv\nEXPOSE 8080\n'
        result = watcher.add_pointer(base, 'seine_snapshot_002', 'release-002', 'scene.tar.gz', 'a' * 64)
        self.assertEqual(result.count('COPY --from=seine_snapshot_002'), 1)
        self.assertLess(result.index('AS seine_snapshot_002'), result.index('COPY deploy/Caddyfile'))
        self.assertEqual(watcher.add_pointer(result, 'seine_snapshot_002', 'release-002', 'scene.tar.gz', 'a' * 64), result)
        with self.assertRaisesRegex(ValueError, 'differs'):
            watcher.add_pointer(result, 'seine_snapshot_002', 'release-002', 'scene.tar.gz', 'b' * 64)
        self.assertIn('AS seine_snapshot_052', watcher.add_pointer(base + 'COPY --from=x\n' * 89, 'seine_snapshot_052', 'r', 'a.tar.gz', 'a' * 64))
        with self.assertRaisesRegex(ValueError, 'consolidation'):
            watcher.add_pointer(base + 'COPY --from=x\n' * 110, 'seine_snapshot_003', 'r', 'a.tar.gz', 'a' * 64)

    def test_missing_observations_fail_instead_of_silently_disappearing(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            current, base = root / 'current.json', root / 'base.json'
            current.write_text(json.dumps(dict(output=name, files=[])))
            base.write_text(json.dumps(dict(output=name, files=[dict(path='www/worlds/retained/world.json', bytes=1, sha256='a')])))
            with self.assertRaisesRegex(ValueError, 'Prior observation absent'):
                watcher.retain_inert(current, base)
