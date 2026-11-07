"""Filesystem/process workflow fixtures, not reconstruction or Railway evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('watcher', Path(__file__).parents[1] / 'watch-seine-publication.py')
watcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watcher)


class WatcherTests(unittest.TestCase):
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
        with self.assertRaisesRegex(ValueError, 'consolidation'):
            watcher.add_pointer(base + 'COPY --from=x\n' * 90, 'seine_snapshot_003', 'r', 'a.tar.gz', 'a' * 64)

    def test_missing_observations_fail_instead_of_silently_disappearing(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            current, base = root / 'current.json', root / 'base.json'
            current.write_text(json.dumps(dict(output=name, files=[])))
            base.write_text(json.dumps(dict(output=name, files=[dict(path='www/worlds/retained/world.json', bytes=1, sha256='a')])))
            with self.assertRaisesRegex(ValueError, 'Prior observation absent'):
                watcher.retain_inert(current, base)
