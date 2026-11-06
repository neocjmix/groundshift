import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('viewer_overlay', Path(__file__).resolve().parents[1] / 'package-viewer-overlay.py')
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)


class ViewerOverlayTests(unittest.TestCase):
    def inventory(self, folder, files):
        records=[]
        for name, value in files.items():
            target=folder/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(value)
            records.append(dict(path=name, bytes=len(value), sha256=overlay.digest(target)))
        path=folder.with_suffix('.inventory.json'); path.write_text(json.dumps(dict(output=str(folder), files=records)))
        return path

    def test_actual_assembly_replaces_overlay_without_mutating_base_and_retains_old_compiled_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            base=self.inventory(root/'base', {'www/index.html':b'old', 'www/experiments/old/summary.json':b'old report', 'www/assets/old.js':b'old bundle'})
            current=self.inventory(root/'current', {'www/index.html':b'new', 'www/experiments/old/summary.json':b'old report', 'www/experiments/new/summary.json':b'new report', 'www/assets/new.js':b'new bundle'})
            archive=root/'new.tar.gz'; overlay.main(SimpleNamespace(inventory=current,base=base,archive=archive))
            report=json.loads(archive.with_suffix('.json').read_text()); assembled=Path(report['assembledDirectory'])
            self.assertEqual(report['status'],'PASS'); self.assertEqual(report['overlayFiles'],3)
            self.assertEqual((root/'base/www/index.html').read_bytes(),b'old')
            self.assertEqual((assembled/'www/index.html').read_bytes(),b'new')
            self.assertEqual((assembled/'www/assets/old.js').read_bytes(),b'old bundle')
            self.assertEqual((assembled/'www/experiments/old/summary.json').read_bytes(),b'old report')

    def test_missing_historical_observation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); base=self.inventory(root/'base',{'www/experiments/old/summary.json':b'retain'})
            current=self.inventory(root/'current',{'www/index.html':b'new'})
            with self.assertRaisesRegex(ValueError,'Prior observation absent'):
                overlay.main(SimpleNamespace(inventory=current,base=base,archive=root/'new.tar.gz'))

    def test_unsafe_inventory_path_is_rejected(self):
        for name in ['../secret','/secret','www/../secret']:
            with self.assertRaises(ValueError):
                overlay.records({'files':[{'path':name}]})
