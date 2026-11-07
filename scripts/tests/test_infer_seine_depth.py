import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image

SPEC = importlib.util.spec_from_file_location('seine_depth', Path(__file__).resolve().parents[1] / 'infer-seine-depth.py')
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)


def image(path, seed):
    Image.fromarray(np.random.default_rng(seed).integers(0, 256, (8, 8, 3), dtype=np.uint8)).save(path)
    return path


def fake_result(folder, inputs):
    """Synthetic on-disk format fixture. This never exercises or proves MPS."""
    folder.mkdir()
    records = []
    for index, requested in enumerate(inputs):
        source = Path(requested['source'])
        with Image.open(source) as loaded:
            loaded.convert('RGB').save(folder / f'view-{index:02d}-source.png')
        values = np.linspace(-0.2, 4, 64, dtype=np.float32).reshape(8, 8)
        np.save(folder / f'view-{index:02d}-relative.npy', values)
        Image.fromarray(np.arange(64, dtype=np.uint8).reshape(8, 8)).save(folder / f'view-{index:02d}-visual.png')
        records.append(dict(**requested, actualModelTensorShape=[1, 3, 518, 518],
            inferenceSeconds=0.125, predictionMin=float(values.min()), predictionMax=float(values.max()),
            relativeNpySha256=D.sha(folder / f'view-{index:02d}-relative.npy'),
            visualSha256=D.sha(folder / f'view-{index:02d}-visual.png')))
    report = dict(schemaVersion=1, status='PASS', model=D.MODEL, revision=D.REVISION, device='mps',
        outputMeaning=D.MEANING, requestedInputSize=None, images=records,
        torchVersion='SYNTHETIC TEST FIXTURE', elapsedSeconds=3.0, modelLoadSeconds=1.0)
    (folder / 'report.json').write_text(json.dumps(report))
    return report


class SeineDepthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = image(self.root / 'source.png', 5)
        self.requested = D.image_input(self.source)
        self.cache = self.root / 'cache'
        fake_result(self.cache, [self.requested])
        self.inputs = self.root / 'inputs.json'
        self.inputs.write_text(json.dumps([str(self.source)]))

    def edit_report(self, edit):
        path = self.cache / 'report.json'
        report = json.loads(path.read_text())
        edit(report)
        path.write_text(json.dumps(report))

    def test_all_cached_does_not_invoke_backend_and_preserves_exact_bytes(self):
        output = self.root / 'output'
        old_report = (self.cache / 'report.json').read_bytes()
        with patch.object(D, 'invoke_backend', side_effect=AssertionError('No model may run')) as backend:
            report = D.run(output, self.inputs, [self.cache])
        backend.assert_not_called()
        self.assertEqual((report['newlyInferred'], report['reused']), (0, 1))
        self.assertEqual(report['execution']['backendStatus'], 'NOT RUN')
        self.assertIsNone(report['execution']['device'])
        self.assertIsNone(report['execution']['newInferenceElapsedSeconds'])
        self.assertIsNone(report['images'][0]['inferenceSeconds'])
        self.assertEqual(report['images'][0]['originEvidence']['inferenceSeconds'], 0.125)
        self.assertEqual((self.cache / 'report.json').read_bytes(), old_report)
        for suffix in ['relative.npy', 'visual.png', 'source.png']:
            old, new = self.cache / f'view-00-{suffix}', output / f'view-00-{suffix}'
            self.assertEqual(old.stat().st_ino, new.stat().st_ino)
            self.assertEqual(D.sha(old), D.sha(new))

    def test_only_cache_misses_reach_backend_and_computed_outputs_are_hardlinked(self):
        second = image(self.root / 'second.png', 9)
        self.inputs.write_text(json.dumps([str(second), str(self.source)]))
        output = self.root / 'mixed'
        with patch.object(D, 'invoke_backend', side_effect=fake_result) as backend:
            report = D.run(output, self.inputs, [self.cache])
        self.assertEqual(len(backend.call_args.args[1]), 1)
        self.assertEqual(backend.call_args.args[1][0]['source'], str(second.resolve()))
        self.assertEqual((report['newlyInferred'], report['reused']), (1, 1))
        self.assertEqual(report['execution']['newInferenceElapsedSeconds'], 3.0)
        self.assertEqual(report['images'][0]['inferenceSeconds'], 0.125)
        self.assertIsNone(report['images'][1]['inferenceSeconds'])
        self.assertEqual((output / 'view-00-relative.npy').stat().st_ino,
                         (output / 'computed/view-00-relative.npy').stat().st_ino)
        self.assertEqual((output / 'view-01-relative.npy').stat().st_ino,
                         (self.cache / 'view-00-relative.npy').stat().st_ino)

    def test_reused_output_can_be_reused_again_with_origin_chain_retained(self):
        first, second = self.root / 'first', self.root / 'second'
        with patch.object(D, 'invoke_backend', side_effect=AssertionError('No backend')):
            D.run(first, self.inputs, [self.cache])
            report = D.run(second, self.inputs, [first])
        origin = report['images'][0]['originEvidence']
        self.assertEqual(origin['previousOrigin']['report'], str((self.cache / 'report.json').resolve()))
        self.assertEqual((second / 'view-00-relative.npy').stat().st_ino,
                         (self.cache / 'view-00-relative.npy').stat().st_ino)

    def test_wrong_model_revision_size_or_semantics_rejected_without_fallback(self):
        original = (self.cache / 'report.json').read_bytes()
        changes = [lambda r: r.update(model='different'), lambda r: r.update(revision='different'),
                   lambda r: r.update(status='FAIL'), lambda r: r.update(outputMeaning='metric depth'),
                   lambda r: r.update(requestedInputSize=518),
                   lambda r: r['images'][0].update(actualModelTensorShape=[1, 3, 756, 756])]
        for i, edit in enumerate(changes):
            with self.subTest(i=i):
                (self.cache / 'report.json').write_bytes(original)
                self.edit_report(edit)
                output = self.root / f'bad{i}'
                with patch.object(D, 'invoke_backend') as backend, self.assertRaises(ValueError):
                    D.run(output, self.inputs, [self.cache])
                backend.assert_not_called()
                self.assertEqual(json.loads((output / 'report.json').read_text())['status'], 'FAIL')

    def test_modified_npy_and_finite_shape_violation_fail_even_with_updated_checksum(self):
        path = self.cache / 'view-00-relative.npy'
        for i, values in enumerate([np.full((8, 8), np.nan, dtype=np.float32),
                                    np.arange(64, dtype=np.float32).reshape(4, 16),
                                    np.arange(64, dtype=np.float64).reshape(8, 8)]):
            with self.subTest(i=i):
                np.save(path, values)
                self.edit_report(lambda r: r['images'][0].update(relativeNpySha256=D.sha(path)))
                with patch.object(D, 'invoke_backend') as backend, self.assertRaisesRegex(ValueError, 'prediction'):
                    D.run(self.root / f'invalid{i}', self.inputs, [self.cache])
                backend.assert_not_called()

    def test_corrupted_visual_or_source_preview_cannot_reuse_pass_label(self):
        visual = self.cache / 'view-00-visual.png'
        visual.write_bytes(visual.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            D.run(self.root / 'bad-visual', self.inputs, [self.cache])
        self.edit_report(lambda r: r['images'][0].update(visualSha256=D.sha(visual)))
        image(self.cache / 'view-00-source.png', 60)
        with self.assertRaisesRegex(ValueError, 'preview pixels'):
            D.run(self.root / 'bad-preview', self.inputs, [self.cache])

    def test_backend_failure_retains_failure_without_claiming_new_predictions(self):
        self.inputs.write_text(json.dumps([str(image(self.root / 'uncached.png', 77))]))
        output = self.root / 'failed'
        with patch.object(D, 'invoke_backend', side_effect=RuntimeError('actual failure fixture')), self.assertRaises(RuntimeError):
            D.run(output, self.inputs, [self.cache])
        report = json.loads((output / 'report.json').read_text())
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['execution']['backendStatus'], 'FAIL')
        self.assertEqual(report['newlyInferred'], 0)
        self.assertIsNone(report['execution']['newInferenceElapsedSeconds'])

    def test_existing_output_cannot_be_overwritten(self):
        output = self.root / 'output'
        output.mkdir()
        (output / 'report.json').write_text('untouched')
        with self.assertRaisesRegex(ValueError, 'exists'):
            D.run(output, self.inputs, [self.cache])
        self.assertEqual((output / 'report.json').read_text(), 'untouched')


if __name__ == '__main__':
    unittest.main()
