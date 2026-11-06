"""Source-sequence evidence only: GPS lengths are not reconstructed camera poses."""
import math
import statistics
from datetime import datetime


def distance(a, b):
    """WGS84 longitude/latitude pairs, spherical great-circle approximation (m)."""
    if len(a) < 2 or len(b) < 2 or not all(math.isfinite(v) for v in [*a[:2], *b[:2]]):
        raise ValueError('Finite longitude/latitude pairs required')
    for lon, lat in [a[:2], b[:2]]:
        if abs(lon) > 180 or abs(lat) > 90:
            raise ValueError('Invalid longitude/latitude')
    p, q = math.radians(a[1]), math.radians(b[1])
    value = math.sin((q-p)/2)**2 + math.cos(p)*math.cos(q)*math.sin(math.radians(b[0]-a[0])/2)**2
    return 12742017.6 * math.asin(min(1, math.sqrt(value)))


def select_route(features, collection, start, end):
    selected = [f for f in features if f['collection'] == collection
                and start <= f['properties']['geovisio:rank_in_collection'] <= end]
    selected.sort(key=lambda f: f['properties']['geovisio:rank_in_collection'])
    if [f['properties']['geovisio:rank_in_collection'] for f in selected] != list(range(start, end+1)):
        raise ValueError('Missing or duplicate capture ranks; do not connect gaps')
    if len(set(f['id'] for f in selected)) != len(selected):
        raise ValueError('Duplicate source IDs')
    for i, f in enumerate(selected):
        p = f['properties']
        interior = p.get('pers:interior_orientation', {})
        if p.get('license') != 'etalab-2.0' or interior.get('field_of_view') != 360:
            raise ValueError('Require verified Open Licence 2.0 and full sphere')
        dimensions = interior.get('sensor_array_dimensions', [])
        if len(dimensions) != 2 or dimensions[0] != 2*dimensions[1] or dimensions[1] <= 0:
            raise ValueError('Require an explicit2:1 ERP raster')
        # Provider adjacency, rather than a GPS-nearest-neighbor invention.
        if i and not any(l.get('rel') == 'prev' and l.get('id') == selected[i-1]['id'] for l in f['links']):
            raise ValueError('Source prev link does not confirm adjacency')
        if i and datetime.fromisoformat(p['datetime'].replace('Z', '+00:00')) < datetime.fromisoformat(selected[i-1]['properties']['datetime'].replace('Z', '+00:00')):
            raise ValueError('Capture time reversed')
    return selected


def route_summary(selected):
    if len(selected) < 2:
        raise ValueError('At least two observations required')
    steps = [distance(a['geometry']['coordinates'], b['geometry']['coordinates']) for a, b in zip(selected, selected[1:])]
    progress = [0]
    for step in steps:
        progress.append(progress[-1]+step)
    return dict(count=len(selected), lengthMeters=progress[-1], medianSpacingMeters=statistics.median(steps),
                maximumSpacingMeters=max(steps), minimumSpacingMeters=min(steps), progressMeters=progress,
                distanceMeaning='Approximate source GPS polyline length, not surveyed distance or SfM geometry')
