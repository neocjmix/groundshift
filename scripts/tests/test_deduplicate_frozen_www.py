import importlib.util
from pathlib import Path
import tempfile
import unittest
import os
import pwd
import subprocess

SPEC = importlib.util.spec_from_file_location('frozen_dedup', Path(__file__).resolve().parents[1] / 'deduplicate-frozen-www.py')
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)


class FrozenDedupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'data/deploy/viewer-100/www'
        self.target = self.root / 'data/jobs/old/publications/frozen/www'
        self.source.mkdir(parents=True)
        self.target.mkdir(parents=True)
        self.plan = dict(schemaVersion=1, kind='frozen-www-hardlinks', immutableAcknowledged=True,
            sources=[str(self.source.relative_to(self.root))], destinations=[str(self.target.relative_to(self.root))])
        self.a, self.b = self.source / 'scene.spz', self.target / 'scene.spz'
        self.a.write_bytes(b'A' * 1048576)
        self.b.write_bytes(self.a.read_bytes())

    def test_audit_never_mutates_and_apply_preserves_bytes_paths_and_anchor(self):
        before = self.a.stat().st_ino, self.b.stat().st_ino
        audit = D.deduplicate(self.root, self.plan)
        self.assertEqual(len(audit['replacements']), 1)
        self.assertEqual((self.a.stat().st_ino, self.b.stat().st_ino), before)
        result = D.deduplicate(self.root, self.plan, apply=True)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(self.a.stat().st_ino, before[0])
        self.assertEqual(self.a.stat().st_ino, self.b.stat().st_ino)
        self.assertEqual(self.b.read_bytes(), b'A' * 1048576)
        self.assertEqual(len(D.deduplicate(self.root, self.plan, apply=True)['replacements']), 0)

    def test_different_mode_or_bytes_are_retained(self):
        self.b.chmod(0o600)
        self.assertEqual(D.deduplicate(self.root, self.plan, apply=True)['replacements'], [])
        self.b.chmod(self.a.stat().st_mode & 0o777)
        self.b.write_bytes(b'B' * 1048576)
        self.assertEqual(D.deduplicate(self.root, self.plan, apply=True)['replacements'], [])
        self.assertEqual(self.b.read_bytes(), b'B' * 1048576)

    def test_extended_attributes_are_not_discarded(self):
        key = 'com.groundshift.dedup-test' if os.uname().sysname == 'Darwin' else 'user.groundshift-test'
        if hasattr(os, 'setxattr'):
            os.setxattr(self.b, key, b'unique metadata')
        else:
            subprocess.run(['/usr/bin/xattr', '-w', key, 'unique metadata', str(self.b)], check=True)
        self.assertEqual(D.deduplicate(self.root, self.plan, apply=True)['replacements'], [])
        self.assertEqual(dict(D._attrs(self.b))[key], b'unique metadata')

    @unittest.skipUnless(os.uname().sysname == 'Darwin', 'macOS extended ACL behavior')
    def test_extended_acl_is_not_discarded(self):
        subprocess.run(['/bin/chmod', '+a', f'user:{pwd.getpwuid(os.getuid()).pw_name} allow read', str(self.b)], check=True)
        self.assertNotEqual(D._attrs(self.a), D._attrs(self.b))
        self.assertEqual(D.deduplicate(self.root, self.plan, apply=True)['replacements'], [])

    def test_active_exclusions_and_nonpublication_paths_rejected_before_mutation(self):
        for patch in [dict(excluded=['data/jobs/old']), dict(destinations=['public']),
                      dict(destinations=['data/jobs/old/training/world']), dict(immutableAcknowledged=False)]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                D.deduplicate(self.root, {**self.plan, **patch}, apply=True)
        self.assertNotEqual(self.a.stat().st_ino, self.b.stat().st_ino)

    def test_symlink_root_or_file_rejected(self):
        link = self.target / 'linked'
        link.symlink_to(self.a)
        with self.assertRaises(ValueError):
            D.deduplicate(self.root, self.plan, apply=True)
        link.unlink()
        elsewhere = self.root / 'data/jobs/old/publications/alias'
        elsewhere.symlink_to(self.target.parent, target_is_directory=True)
        with self.assertRaises(ValueError):
            D.deduplicate(self.root, {**self.plan, 'destinations':[str((elsewhere / 'www').relative_to(self.root))]}, apply=True)

    def test_late_change_does_not_replace_destination(self):
        source_stamp, target_stamp = D._stamp(self.a.stat()), D._stamp(self.b.stat())
        digest = D._digest(self.a)
        self.b.write_bytes(b'changed after audit')
        with self.assertRaisesRegex(ValueError, 'changed since audit'):
            D.replace_verified(self.a, self.b, source_stamp, target_stamp, digest)
        self.assertEqual(self.b.read_bytes(), b'changed after audit')
        self.assertFalse(list(self.target.glob('*.gs-hardlink-*')))


if __name__ == '__main__':
    unittest.main()
