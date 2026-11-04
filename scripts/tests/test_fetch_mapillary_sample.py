import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "fetch_mapillary_sample", Path(__file__).parents[1] / "fetch-mapillary-sample.py")
FETCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FETCH)


class SourceIntegrityTests(unittest.TestCase):
    def test_changed_source_is_rejected_even_at_same_length(self):
        original = b"original"
        entry = {"image_id": "fixture", "size": len(original),
                 "sha1": hashlib.sha1(original).hexdigest()}
        with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
            FETCH.verify_source(b"modified", entry)

    def test_failed_download_retains_failure_report_without_completed_image(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch.object(FETCH.urllib.request, "urlopen", side_effect=OSError("offline")):
                with self.assertRaisesRegex(OSError, "offline"):
                    FETCH.acquire(output)
            report = FETCH.json.loads((output / "acquisition.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["frames"], [])
            self.assertEqual(list((output / "images").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
