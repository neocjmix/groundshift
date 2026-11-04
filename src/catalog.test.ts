import { describe, expect, it } from 'vitest';
import { parseSceneCatalog, type SceneCatalog } from './catalog';

function fixture(): SceneCatalog {
  return { version: 1, scenes: [{
    id: 'sample', title: 'Synthetic sample', description: 'Parser fixture only', category: 'sample',
    manifestPath: '/worlds/sample/world.json', thumbnailPath: '/worlds/sample/preview.jpg', detail: 'No rendering claim',
  }] };
}

describe('scene catalog', () => {
  it('preserves explicit scene order and metadata', () => {
    expect(parseSceneCatalog(fixture())).toEqual(fixture());
  });

  it.each([
    'https://example.com/world.json', '//example.com/world.json', '/worlds/../world.json',
    '/worlds/%2e%2e/world.json', '/worlds/sample/world.json?download=1',
    '/worlds/sample/world.json#fragment', '/worlds/sample/world.json\n',
    '/worlds/sample\\world.json', '/worlds/sample/source.mov',
  ])('rejects unsafe or unsupported manifest path %j', manifestPath => {
    const catalog = fixture();
    catalog.scenes[0]!.manifestPath = manifestPath;
    expect(() => parseSceneCatalog(catalog)).toThrow();
  });

  it('requires a preview from the same world folder', () => {
    const catalog = fixture();
    catalog.scenes[0]!.thumbnailPath = '/worlds/another/preview.jpg';
    expect(() => parseSceneCatalog(catalog)).toThrow('same world');
  });

  it.each(['id', 'manifestPath', 'thumbnailPath'] as const)('rejects duplicate %s', field => {
    const catalog = fixture();
    const original = catalog.scenes[0]!;
    catalog.scenes.push({ ...original, id: 'another', manifestPath: '/worlds/another/world.json', thumbnailPath: '/worlds/another/preview.jpg', [field]: original[field] });
    expect(() => parseSceneCatalog(catalog)).toThrow();
  });

  it('rejects unknown fields, unsupported versions, empty catalogs and blank labels', () => {
    expect(() => parseSceneCatalog({ ...fixture(), version: 2 })).toThrow();
    expect(() => parseSceneCatalog({ version: 1, scenes: [] })).toThrow();
    expect(() => parseSceneCatalog({ ...fixture(), privateSource: '/private/source.mov' })).toThrow();
    const catalog = fixture();
    catalog.scenes[0]!.title = '  ';
    expect(() => parseSceneCatalog(catalog)).toThrow();
  });
});
