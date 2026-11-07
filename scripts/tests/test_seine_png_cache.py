"""Synthetic storage protocol fixtures, never evidence of training or inference."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

SPEC = importlib.util.spec_from_file_location('seine_png', Path(__file__).resolve().parents[1] / 'seine_png_cache.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


class SeinePngCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        self.task = self.repo / 'data/jobs/seine-full-20261107'
        self.job = self.task / 'segment-1004-1027'
        self.keep = self.task / 'segment-1020-1043'
        for job in [self.job, self.keep]:
            for name in ['training/job.json', 'tangent-inputs/report.json', 'depth/report.json', 'sfm/report.json']:
                path = job / name;path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{"status":"PASS"}')
        self.source = self.task / 'acquisition-1004-1027/images/original.jpg'
        self.source.parent.mkdir(parents=True)
        y, x = np.mgrid[:32, :64]
        Image.fromarray(np.stack([x * 3, y * 6, (x + y) * 2], axis=-1).astype(np.uint8)).save(self.source)
        self.proof = self.job / 'png-cache'
        self.proof.mkdir()
        for name, source in [('prepare-panoramas.py', Path(P.__file__).with_name('prepare-panoramas.py')), ('restore-script.py', Path(P.__file__))]:
            shutil.copyfile(source, self.proof / name)
        self.manifest_path = self.proof / 'manifest.json'
        self.manifest = dict(schemaVersion=1, kind='seine-generated-png-cache-v1', status='PASS', state='PRESENT',
            job=str(self.job), versions=P.versions(), projectionSha256=P.file_sha(self.proof / 'prepare-panoramas.py'),
            rendererSha256=P.file_sha(self.proof / 'restore-script.py'),
            sources={'original.jpg':dict(path=str(self.source), sha256=P.file_sha(self.source), dimensions=[64,32], rank=1004)},
            recipes={}, files={})
        self.expected = {}
        patterns = {
            'rgb': ('tangent-rgb', ['tangent-inputs/images/p00-t00.png', 'dataset/images/p00-t00.png', 'depth/view-00-source.png']),
            'mask': ('tangent-mask', ['tangent-inputs/masks/p00-t00.png', 'dataset/masks/p00-t00.png']),
            'sfm': ('sfm-bgr', ['sfm-inputs/images/pano_000001_view_01.png', 'sfm/dataset/images/pano_000001_view_01.png', 'sfm/rig-images/view_00/pano_000000.png'])}
        for key, (kind, _) in patterns.items():
            self.manifest['recipes'][key] = dict(kind=kind, source='original.jpg', size=16, fov=80, yaw=310, pitch=-10, maskBoundary=.78)
        for key, raw in P.rendered(self.manifest, P.module(self.proof / 'prepare-panoramas.py')):
            for relative in patterns[key][1]:
                path = self.job / relative;path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(raw)
                self.expected[relative] = raw
                self.manifest['files'][relative] = dict(recipe=key, sha256=P.sha(raw), bytes=len(raw), mode=0o644, mtimeNs=path.stat().st_mtime_ns)
        self.manifest.update(verifiedAliases=len(self.expected), verifiedRecipes=len(patterns))
        P.save(self.manifest_path, self.manifest)
        for path in [self.job / 'depth/view-00-visual.png', self.job / 'depth/view-00-relative.npy',
                     self.job / 'sfm/database.db', self.job / 'training/execution.log', self.job / 'training/scene.ply']:
            path.write_bytes(b'KEEP ACTUAL EVIDENCE')

    def evict(self, apply=False, keep=None):
        return P.evict_verified_pngs(self.manifest_path, keep_jobs=keep if keep is not None else [self.keep], repo=self.repo, apply=apply)

    def assert_present(self):
        for relative, expected in self.expected.items():self.assertEqual((self.job / relative).read_bytes(), expected)

    def test_readonly_audit_then_exact_restore_of_all_stages_preserves_other_evidence(self):
        report = self.evict()
        self.assertEqual(report['removedAliases'], 0)
        self.assert_present()
        report = self.evict(True)
        self.assertEqual(report['removedAliases'], len(self.expected))
        self.assertTrue(all(not (self.job / p).exists() for p in self.expected))
        for path in [self.job / 'depth/view-00-visual.png', self.job / 'depth/view-00-relative.npy', self.job / 'sfm/database.db', self.job / 'training/execution.log', self.job / 'training/scene.ply']:
            self.assertEqual(path.read_bytes(), b'KEEP ACTUAL EVIDENCE')
        restored = P.restore_png_cache(self.manifest_path, repo=self.repo)
        self.assertEqual(restored['restoredAliases'], len(self.expected))
        self.assert_present()
        self.assertEqual((self.job / 'dataset/images/p00-t00.png').stat().st_ino, (self.job / 'depth/view-00-source.png').stat().st_ino)

    def test_reference_frontier_active_jobs_and_old_jobs_are_protected(self):
        for keep in [[], [self.job]]:
            with self.assertRaises(ValueError):self.evict(True, keep)
        (self.job / 'training/job.json').write_text('{"status":"RUNNING"}')
        with self.assertRaises(ValueError):self.evict(True)
        (self.job / 'training/job.json').write_text('{"status":"PASS"}')
        self.manifest['job'] = str(self.repo / 'data/jobs/paris-streaming-20261107')
        P.save(self.manifest_path, self.manifest)
        with self.assertRaises(ValueError):self.evict(True)
        self.assert_present()

    def test_changed_original_or_png_never_evicted(self):
        original = self.source.read_bytes();self.source.write_bytes(original + b'changed')
        with self.assertRaisesRegex(ValueError, 'ERP changed'):self.evict(True)
        self.assert_present();self.source.write_bytes(original)
        candidate = self.job / next(iter(self.expected));candidate.write_bytes(b'changed PNG')
        with self.assertRaisesRegex(ValueError, 'PNG changed'):self.evict(True)
        self.assertEqual(candidate.read_bytes(), b'changed PNG')

    def test_unproved_path_disappearance_dependency_or_saved_code_change_fails(self):
        for key, value in [('status', 'FAIL'), ('verifiedAliases', 0), ('versions', {})]:
            old = self.manifest[key];self.manifest[key] = value;P.save(self.manifest_path, self.manifest)
            with self.assertRaises(ValueError):self.evict(True)
            self.manifest[key] = old
        P.save(self.manifest_path, self.manifest)
        code = self.proof / 'prepare-panoramas.py';code.write_bytes(code.read_bytes() + b'\n# changed')
        with self.assertRaisesRegex(ValueError, 'recipe code changed'):self.evict(True)
        self.assert_present()

    def test_allowlist_and_symlink_cannot_remove_original_or_visual(self):
        row = next(iter(self.manifest['files'].values()))
        self.manifest['files']['depth/view-00-visual.png'] = row
        self.manifest['verifiedAliases'] += 1
        P.save(self.manifest_path, self.manifest)
        with self.assertRaisesRegex(ValueError, 'Unexpected PNG'):self.evict(True)
        self.manifest['files'].pop('depth/view-00-visual.png');self.manifest['verifiedAliases'] -= 1
        P.save(self.manifest_path, self.manifest)
        path = self.job / next(iter(self.expected));path.unlink();path.symlink_to(self.source)
        with self.assertRaises(ValueError):self.evict(True)
        self.assertTrue(self.source.exists())

    def test_extra_or_missing_generated_png_rejected_before_unlink(self):
        path = self.job / 'tangent-inputs/images/p00-t19.png';path.write_bytes(b'unproved')
        with self.assertRaisesRegex(ValueError, 'unproved'):self.evict(True)
        path.unlink()
        path = self.job / next(iter(self.expected));path.unlink()
        with self.assertRaisesRegex(ValueError, 'disappeared'):self.evict(True)

    def test_external_hardlink_is_preserved_and_not_reported_as_reclaimed(self):
        source = self.job / next(iter(self.expected));target = self.keep / 'retained-reference.png';os.link(source, target)
        report = self.evict(True)
        self.assertLess(report['uniqueBytesWithNoExternalLinks'], report['rawUniqueBytes'])
        self.assertEqual(target.read_bytes(), next(iter(self.expected.values())))

    def test_partial_eviction_is_restorable_and_retry_is_idempotent(self):
        original = Path.unlink;removed = []
        def interrupted(path, *args, **kwargs):
            if path.relative_to(self.job).as_posix() in self.expected:
                if removed:raise OSError('Injected interruption after first eviction')
                removed.append(path)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'unlink', interrupted), self.assertRaises(OSError):self.evict(True)
        self.assertEqual(P.read(self.manifest_path)['state'], 'EVICTING')
        self.assertFalse(removed[0].exists())
        P.restore_png_cache(self.manifest_path, repo=self.repo);self.assert_present()
        self.evict(True)
        self.assertEqual(self.evict(True)['removedAliases'], 0)
        P.restore_png_cache(self.manifest_path, repo=self.repo);self.assert_present()


if __name__ == '__main__':unittest.main()
