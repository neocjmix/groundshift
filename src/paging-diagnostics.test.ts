import { describe, expect, it } from 'vitest';
import type { PagedSplats, SparkRenderer } from '@sparkjsdev/spark';
import { snapshotPagingDiagnostics, type PagingDiagnostics } from './paging-diagnostics';

function fixture() {
  const spark = {
    lodSplatCount: 800000, lodSplatScale: 1, lodRenderScale: 1, maxPagedSplats: 917504,
    renderSize: { x: 603, y: 1311 }, activeSplats: 52000,
    current: { numSplats: 52000, mappingVersion: 4 }, display: { numSplats: 52000, mappingVersion: 4 },
    sorting: false, sortDirty: false, lastSortTime: 100, lodDirty: false, lodInitQueue: [],
    lastLod: { timestamp: 100, maxSplats: 800000, pixelScaleLimit: .00128 },
    currentLod: { timestamp: 100 }, lastLodRaycastTime: 100,
    lodWorker: null as { messages: Record<string, unknown> } | null,
    sortWorker: null as { messages: Record<string, unknown> } | null,
    pager: { fetchers: [] as unknown[], fetched: [] as unknown[], newUploads: [] as unknown[], readyUploads: [] as unknown[], lodTreeUpdates: [] as unknown[], pageToSplatsChunk: [{ chunk: 0 }, { chunk: 3 }] },
  };
  const network = { pending: 0, requested: 3, bytes: 3000000, errors: [] as string[] };
  const capture = (nowMs = 1000, previous?: PagingDiagnostics, lastFrameMs: number | null = nowMs) => snapshotPagingDiagnostics({
    spark: spark as unknown as SparkRenderer, paged: { numSplats: 53000 } as PagedSplats,
    network, nowMs, frameCount: nowMs / 10, lastFrameMs, visibility: 'visible', previous,
  });
  return { spark, network, capture };
}

describe('pinned Spark device diagnostics', () => {
  it('distinguishes network completion from a decoder or retry that stops making progress', () => {
    const { spark, network, capture } = fixture();
    spark.pager.fetchers.push({}); network.pending = 1;
    const downloading = capture();
    expect(downloading.phase).toBe('network'); expect(downloading.queues.decodeOrBackoff).toBe(0);
    network.pending = 0;
    const decoding = capture(2000, downloading);
    expect(decoding.phase).toBe('decode'); expect(decoding.stages.decode.state).toBe('busy');
    const waiting = capture(13000, decoding);
    expect(waiting.stages.decode.state).toBe('waiting'); expect(waiting.stages.decode.unchangedMs).toBe(11000);
    expect(waiting.heartbeat.state).toBe('rendering'); // Healthy RAF cannot hide stalled pipeline work.
    spark.pager.fetchers.length = 0; spark.activeSplats = 670000;
    expect(capture(14000, waiting).phase).toBe('settled');
  });

  it('does not call an idle low-count view stalled or fully detailed', () => {
    const { capture } = fixture(); const first = capture(); const later = capture(61000, first);
    expect(later.phase).toBe('settled'); expect(later.selection.active).toBe(52000);
    expect(Object.values(later.stages).every(stage => stage.state === 'idle')).toBe(true);
    expect(later.runtime.traversalBudget).toBe(800000);
  });

  it('separates decoded/tree work, uploads and GPU/sort display handoff', () => {
    const { spark, capture } = fixture();
    spark.pager.lodTreeUpdates.push({}); expect(capture().phase).toBe('lod');
    spark.pager.lodTreeUpdates.length = 0; spark.pager.readyUploads.push({}); expect(capture().phase).toBe('upload');
    spark.pager.readyUploads.length = 0; spark.current.mappingVersion = 5; spark.current.numSplats = 600000;
    spark.sorting = true; spark.sortWorker = { messages: { 8: {} } };
    const sorting = capture(); const waiting = capture(12000, sorting);
    expect(waiting.phase).toBe('display'); expect(waiting.stages.display.state).toBe('waiting');
    expect(waiting.selection.active).toBe(52000); expect(waiting.selection.current).toBe(600000);
    spark.lastSortTime = 12000;
    expect(capture(13000, waiting).stages.display.state).toBe('busy');
  });

  it('reports render pauses independently, without calling hidden-page throttling a failure', () => {
    const { capture } = fixture(); const paused = capture(5000, undefined, 1000);
    expect(paused.phase).toBe('settled'); expect(paused.heartbeat.state).toBe('paused');
    const hidden = snapshotPagingDiagnostics({ nowMs: 9000, frameCount: 0, lastFrameMs: null, visibility: 'hidden' });
    expect(hidden.heartbeat.state).toBe('hidden'); expect(hidden.phase).toBe('unknown');
  });

  it('tolerates missing, disposed, throwing and invalid fields without exposing raw data', () => {
    const hostile = new Proxy({}, { get() { throw new Error('private URL or log'); } }) as SparkRenderer;
    expect(() => snapshotPagingDiagnostics({ spark: hostile, nowMs: NaN, frameCount: Infinity, lastFrameMs: null })).not.toThrow();
    const unknown = snapshotPagingDiagnostics({ spark: hostile, nowMs: NaN, frameCount: Infinity, lastFrameMs: null });
    expect(unknown.phase).toBe('unknown'); expect(unknown.runtime.maxPagedSplats).toBeNull();
    expect(unknown.queues.fetchDecode).toBeNull(); expect(unknown.sampledAtMs).toBeNull();
    const { network, capture } = fixture(); network.errors.push('https://private.example/source-secret');
    const data = capture(); expect(data.network.errorCount).toBe(1);
    expect(JSON.stringify(data)).not.toContain('private');
  });
});
