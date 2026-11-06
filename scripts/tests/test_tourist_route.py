"""Synthetic boundary checks, separate from actual Panoramax acquisition/render evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
from tourist_route import distance, select_route, route_summary

spec = importlib.util.spec_from_file_location('acquire_tourist_route', Path(__file__).parents[1]/'acquire-tourist-route.py')
acquire_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acquire_module)


def feature(rank, longitude=2):
    return dict(id=str(rank), collection='seq', geometry=dict(coordinates=[longitude, 48]),
                links=[dict(rel='prev', id=str(rank-1))], properties={
                    'geovisio:rank_in_collection': rank, 'datetime': f'2026-01-01T00:00:0{rank}Z',
                    'license': 'etalab-2.0', 'pers:interior_orientation': dict(field_of_view=360, sensor_array_dimensions=[12288, 6144])})


class SourceRouteTests(unittest.TestCase):
    def test_reversed_network_order_restores_actual_rank_order(self):
        a, b = feature(1), feature(2, 2.00003)
        selected = select_route([b, a], 'seq', 1, 2)
        self.assertEqual([f['id'] for f in selected], ['1', '2'])
        self.assertGreater(route_summary(selected)['lengthMeters'], 2)

    def test_missing_and_duplicate_ranks_are_not_connected(self):
        with self.assertRaisesRegex(ValueError, 'ranks'):
            select_route([feature(1), feature(3)], 'seq', 1, 3)
        with self.assertRaisesRegex(ValueError, 'ranks'):
            select_route([feature(1), feature(2), feature(2)], 'seq', 1, 2)

    def test_provider_link_must_confirm_adjacent_frame(self):
        bad = feature(2); bad['links'][0]['id'] = 'other-photo'
        with self.assertRaisesRegex(ValueError, 'prev link'):
            select_route([feature(1), bad], 'seq', 1, 2)

    def test_no_silent_license_or_perspective_substitution(self):
        for key, value in [('license', 'proprietary'), ('pers:interior_orientation', dict(field_of_view=90))]:
            f = feature(1); f['properties'][key] = value
            with self.assertRaisesRegex(ValueError, 'Licence'):
                select_route([f], 'seq', 1, 1)
        f = feature(1); f['properties']['pers:interior_orientation']['sensor_array_dimensions'] = [4096, 4096]
        with self.assertRaisesRegex(ValueError, 'ERP'):
            select_route([f], 'seq', 1, 1)

    def test_utc_time_comparison_accounts_for_offset(self):
        a, b = feature(1), feature(2)
        a['properties']['datetime'] = '2026-01-01T01:00:00+01:00'
        b['properties']['datetime'] = '2026-01-01T00:00:01Z'
        self.assertEqual(len(select_route([a, b], 'seq', 1, 2)), 2)
        b['properties']['datetime'] = '2025-12-31T23:59:59Z'
        with self.assertRaisesRegex(ValueError, 'reversed'):
            select_route([a, b], 'seq', 1, 2)

    def test_duplicate_ids_are_not_extra_observations(self):
        a, b = feature(1), feature(2); b['id'] = a['id']
        with self.assertRaisesRegex(ValueError, 'IDs'):
            select_route([a, b], 'seq', 1, 2)

    def test_longitude_latitude_axis_high_latitudes_and_dateline(self):
        equator = distance([0, 0], [1, 0])
        self.assertAlmostEqual(equator, 111195.08, places=1)
        self.assertAlmostEqual(distance([0, 60], [1, 60])/equator, .5, places=4)
        self.assertLess(distance([179.999, 0], [-179.999, 0]), 223)
        self.assertEqual(distance([2, 48], [2, 48]), 0)

    def test_invalid_coordinates_and_stationary_capture(self):
        for pair in [[200, 1], [1, 91], [float('nan'), 1]]:
            with self.assertRaises(ValueError):
                distance(pair, [0, 0])
        self.assertEqual(route_summary([feature(1), feature(2)])['lengthMeters'], 0)
        with self.assertRaises(ValueError):
            route_summary([feature(1)])

    def test_failed_hd_download_keeps_failure_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = root/'route.json'
            manifest.write_text(json.dumps(dict(collection='seq', images=[dict(license='etalab-2.0', hdUrl='https://example.com/source.jpg')])) )
            with patch.object(acquire_module.urllib.request, 'urlopen', side_effect=OSError('offline')):
                result = acquire_module.acquire(manifest, root/'new-output', 0, 1)
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['frames'], [])
            stored = json.loads((root/'new-output/acquisition.json').read_text())
            self.assertEqual(stored['sourceManifestSha256'], hashlib.sha256(manifest.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
