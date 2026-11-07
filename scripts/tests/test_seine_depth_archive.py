import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('seine_archive', Path(__file__).resolve().parents[1] / 'seine_depth_archive.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def npy(values=(1.0, 2.5, 3.125, 4.0)):
    header = "{'descr': '<f4', 'fortran_order': False, 'shape': (2, 2), }"
    header = (header + ' ' * (-(10 + len(header) + 1) % 64) + '\n').encode()
    return b'\x93NUMPY\x01\x00' + struct.pack('<H', len(header)) + header + struct.pack('<4f', *values)


class SeineArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        self.job = self.repo / 'data/jobs/seine-full-20261107/segment-1004-1027'
        self.depth = self.job / 'depth'
        self.depth.mkdir(parents=True)
        (self.job / 'training').mkdir()
        (self.job / 'training/job.json').write_text(json.dumps({'status': 'PASS'}))
        self.raw = npy()
        self.path = self.depth / 'view-00-relative.npy'
        self.path.write_bytes(self.raw)
        self.report = {'status': 'PASS', 'images': [{'relativeNpySha256': A.digest(self.raw)}]}
        (self.depth / 'report.json').write_text(json.dumps(self.report))

    def run_archive(self, apply=True):
        return A.archive_completed_depth(self.job, repo=self.repo, apply=apply)

    def test_codec_exact_bytes_including_header_endianness_and_odd_tail(self):
        for raw in [self.raw, npy((-0.0, 0.125, 128.5, 0.00000001)), self.raw + b'xyz']:
            with self.subTest(size=len(raw)):
                encoded = A.encode_npy(raw)
                self.assertEqual(A.decode_npy(encoded, expected_sha256=A.digest(raw), expected_bytes=len(raw)), raw)

    def test_corruption_truncation_trailing_and_wrong_original_identity_rejected(self):
        encoded = A.encode_npy(self.raw)
        for invalid in [encoded[:9], encoded[:-1], encoded + b'extra', encoded[:-3] + b'bad']:
            with self.subTest(size=len(invalid)), self.assertRaises(ValueError):
                A.decode_npy(invalid)
        with self.assertRaises(ValueError):
            A.decode_npy(encoded, expected_sha256='0' * 64)
        with self.assertRaises(ValueError):
            A.decode_npy(encoded, expected_bytes=1)

    def test_audit_is_read_only_then_shared_aliases_archive_once_and_restore(self):
        computed = self.depth / 'computed'
        computed.mkdir()
        alias = computed / self.path.name
        os.link(self.path, alias)
        (computed / 'report.json').write_text(json.dumps(self.report))
        audit = self.run_archive(False)
        self.assertEqual((audit['rawAliases'], audit['uniqueInodes']), (2, 1))
        self.assertTrue(self.path.exists())
        self.assertFalse((self.depth / A.MANIFEST).exists())
        result = self.run_archive()
        self.assertEqual(result['removedAliases'], 2)
        self.assertEqual(len(list((self.job.parent / 'depth-archive').glob('*.sz'))), 1)
        for p in [self.path, alias]:
            self.assertFalse(p.exists())
            self.assertEqual(A.read_npy_bytes(p, repo=self.repo), self.raw)
        again = self.run_archive()
        self.assertEqual(again['removedAliases'], 0)
        self.assertEqual(A.restore_npy(alias, repo=self.repo).read_bytes(), self.raw)
        self.assertEqual(A.restore_npy(self.path, repo=self.repo).read_bytes(), self.raw)

    def test_external_hardlink_remains_and_storage_claim_is_explicit(self):
        outside = self.job.parent / 'unmodified-frontier.npy'
        os.link(self.path, outside)
        result = self.run_archive()
        self.assertEqual(result['groups'][0]['linksOutsideThisJob'], 1)
        self.assertEqual(outside.read_bytes(), self.raw)

    def test_old_jobs_active_training_failed_depth_and_symlinks_are_refused(self):
        for patch_report in [{'status': 'RUNNING'}, {'status': 'FAIL'}]:
            (self.job / 'training/job.json').write_text(json.dumps(patch_report))
            with self.assertRaises(ValueError):
                self.run_archive()
        (self.job / 'training/job.json').write_text(json.dumps({'status': 'PASS'}))
        old = self.repo / 'data/jobs/paris-streaming-20261107'
        old.mkdir()
        with self.assertRaises(ValueError):
            A.archive_completed_depth(old, repo=self.repo, apply=True)
        self.path.unlink()
        elsewhere = self.job / 'secret.npy'
        elsewhere.write_bytes(self.raw)
        self.path.symlink_to(elsewhere)
        with self.assertRaises(ValueError):
            self.run_archive()
        self.assertEqual(elsewhere.read_bytes(), self.raw)

    def test_inference_sha_mismatch_preserves_every_raw_byte(self):
        self.path.write_bytes(npy((4, 3, 2, 1)))
        changed = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'inference-report SHA'):
            self.run_archive()
        self.assertEqual(self.path.read_bytes(), changed)
        self.assertFalse((self.depth / A.MANIFEST).exists())

    def test_corrupt_existing_blob_never_removes_raw_input(self):
        folder = self.job.parent / 'depth-archive'
        folder.mkdir()
        (folder / (A.digest(self.raw) + '.npy.sz')).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            self.run_archive()
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertFalse((self.depth / A.MANIFEST).exists())

    def test_interrupted_unlink_keeps_durable_manifest_and_exact_restore(self):
        computed = self.depth / 'computed'
        computed.mkdir()
        alias = computed / self.path.name
        os.link(self.path, alias)
        (computed / 'report.json').write_text(json.dumps(self.report))
        original = Path.unlink
        def fail_raw(path, *args, **kwargs):
            if path == self.path:
                raise OSError('Injected unlink interruption')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail_raw), self.assertRaises(OSError):
            self.run_archive()
        self.assertEqual(json.loads((self.depth / A.MANIFEST).read_text())['state'], 'VERIFIED_ARCHIVES')
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertFalse(alias.exists())  # The earlier alias was already unlinked.
        self.assertEqual(A.read_npy_bytes(alias, repo=self.repo), self.raw)
        result = self.run_archive()
        self.assertEqual(result['removedAliases'], 1)
        self.assertEqual(A.read_npy_bytes(self.path, repo=self.repo), self.raw)

    def test_missing_reported_prediction_and_unreported_prediction_are_rejected(self):
        self.path.unlink()
        with self.assertRaises(ValueError):
            self.run_archive()
        self.path.write_bytes(self.raw)
        extra = self.depth / 'view-99-relative.npy'
        extra.write_bytes(self.raw)
        with self.assertRaisesRegex(ValueError, 'Unexpected raw prediction'):
            self.run_archive()
        self.assertEqual(extra.read_bytes(), self.raw)

    def test_manifest_path_escape_and_corrupt_restored_original_rejected(self):
        self.run_archive()
        manifest = json.loads((self.depth / A.MANIFEST).read_text())
        manifest['entries']['../../foreign.npy'] = next(iter(manifest['entries'].values()))
        (self.depth / A.MANIFEST).write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            self.run_archive()
        manifest['entries'].pop('../../foreign.npy')
        (self.depth / A.MANIFEST).write_text(json.dumps(manifest))
        self.path.write_bytes(npy((8, 8, 8, 8)))
        with self.assertRaisesRegex(ValueError, 'differs from archive'):
            A.restore_npy(self.path, repo=self.repo)


if __name__ == '__main__':
    unittest.main()
