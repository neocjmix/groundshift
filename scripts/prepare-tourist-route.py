#!/usr/bin/env python3
"""Audit a real Panoramax response and prepare the selected Paris source manifest."""
import argparse
import hashlib
import json
from pathlib import Path
from tourist_route import select_route, route_summary


def prepare(snapshot, output):
    raw = snapshot.read_bytes()
    features = json.loads(raw)['features']
    collection = '9fe7f3ab-14e3-4174-8731-b06e31d9577b'
    selected = select_route(features, collection, 808, 1683)
    statistics = route_summary(selected)
    progress = statistics.pop('progressMeters')
    images = []
    for item, meters in zip(selected, progress):
        p = item['properties']
        images.append(dict(id=item['id'], rank=p['geovisio:rank_in_collection'], gps=item['geometry']['coordinates'],
                           distanceMeters=meters, capturedAt=p['datetime'], sourceUpdatedAt=p['updated'],
                           azimuthDegrees=p.get('view:azimuth'), horizontalAccuracyMeters=p.get('quality:horizontal_accuracy'),
                           dimensions=p['pers:interior_orientation']['sensor_array_dimensions'],
                           hdUrl=item['assets']['hd']['href'], sdUrl=item['assets']['sd']['href'], license=p['license'],
                           metadataUrl=next(link['href'] for link in item['links'] if link['rel'] == 'self')))
    route = dict(schemaVersion=1, id='paris-seine-20250508', collection=collection,
                 author='Immergis pour la Ville de Paris', license='etalab-2.0',
                 licenseUrl='https://github.com/etalab/licence-ouverte/blob/master/open-licence.md',
                 source='https://api.panoramax.xyz/api/collections/'+collection,
                 sourceSnapshotSha256=hashlib.sha256(raw).hexdigest(), capturedAtStart=images[0]['capturedAt'],
                 capturedAtEnd=images[-1]['capturedAt'], statistics=statistics, images=images)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        stream.write(json.dumps(route, indent=2)+'\n')
    print(json.dumps(dict(status='PASS', **statistics)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('output', type=Path)
    a = parser.parse_args()
    prepare(a.snapshot, a.output)
