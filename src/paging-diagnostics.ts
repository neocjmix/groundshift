import type { PagedSplats, SparkRenderer } from '@sparkjsdev/spark';
import type { RadTransfer } from './rad-fetcher';

type NullableNumber = number | null;
export type PagingStage = 'network' | 'decode' | 'lod' | 'upload' | 'display';
export interface PagingStageDiagnostic {
  state: 'idle' | 'busy' | 'waiting' | 'unknown';
  unchangedMs: NullableNumber;
  sinceMs: NullableNumber;
  /** Numeric-only observations used to detect progress, never URLs or logs. */
  progress: string;
}
export interface PagingDiagnostics {
  schemaVersion: 1;
  sparkVersion: '2.4.0';
  sampledAtMs: NullableNumber;
  available: boolean;
  /** Settled means no observed pending work, not full detail or visual quality. */
  phase: PagingStage | 'settled' | 'initializing' | 'unknown';
  heartbeat: {
    state: 'rendering' | 'paused' | 'hidden' | 'not-observed';
    frames: NullableNumber;
    lastFrameMs: NullableNumber;
    ageMs: NullableNumber;
  };
  runtime: {
    lodSplatCount: NullableNumber;
    lodSplatScale: NullableNumber;
    lodRenderScale: NullableNumber;
    maxPagedSplats: NullableNumber;
    traversalBudget: NullableNumber;
    renderWidth: NullableNumber;
    renderHeight: NullableNumber;
    pixelScaleLimit: NullableNumber;
  };
  network: { pending: NullableNumber; requested: NullableNumber; bytes: NullableNumber; errorCount: NullableNumber };
  queues: {
    fetchDecode: NullableNumber;
    /** Fetchers also include retry backoff; this is not an exact decoder count. */
    decodeOrBackoff: NullableNumber;
    fetched: NullableNumber;
    newUploads: NullableNumber;
    readyUploads: NullableNumber;
    treeUpdates: NullableNumber;
    lodRpc: NullableNumber;
    sortRpc: NullableNumber;
  };
  selection: {
    traversed: NullableNumber;
    current: NullableNumber;
    displayed: NullableNumber;
    active: NullableNumber;
    residentPages: NullableNumber;
    residentChunks: number[] | null;
    currentMapping: NullableNumber;
    displayMapping: NullableNumber;
    sorting: boolean | null;
  };
  stages: Record<PagingStage, PagingStageDiagnostic>;
}

export interface PagingDiagnosticsInput {
  spark?: SparkRenderer | null;
  paged?: PagedSplats | null;
  network?: Readonly<RadTransfer>;
  nowMs: number;
  frameCount: number;
  lastFrameMs: number | null;
  visibility?: DocumentVisibilityState;
  previous?: PagingDiagnostics | null;
}

// Pinned Spark 2.4.0 exposes some queues as TypeScript-private ordinary fields.
// Read only their lengths. Missing fields/getter failures stay unknown, not zero.
function read(object: unknown, key: PropertyKey): unknown {
  try {
    return object !== null && (typeof object === 'object' || typeof object === 'function')
      ? Reflect.get(object, key) : undefined;
  } catch { return undefined; }
}
function number(value: unknown): NullableNumber {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
}
function count(value: unknown): NullableNumber {
  try { return Array.isArray(value) ? number(value.length) : null; } catch { return null; }
}
function rpcCount(worker: unknown): NullableNumber {
  if (worker === null) return 0; // Spark initializes an unused worker to null.
  const messages = read(worker, 'messages');
  try { return messages && typeof messages === 'object' ? Object.keys(messages).length : null; }
  catch { return null; }
}
function boolean(value: unknown): boolean | null { return typeof value === 'boolean' ? value : null; }
function positive(...values: NullableNumber[]): boolean | null {
  return values.some(value => value !== null && value > 0) ? true : values.includes(null) ? null : false;
}
function any(...values: (boolean | null)[]): boolean | null {
  return values.includes(true) ? true : values.includes(null) ? null : false;
}
function chunks(value: unknown): number[] | null {
  const length = count(value);
  if (length === null || length > 4096) return null;
  const result: number[] = [];
  for (let i = 0; i < length; i++) {
    const entry = read(value, i);
    if (entry === undefined || entry === null) continue;
    const chunk = number(read(entry, 'chunk'));
    if (chunk === null) return null;
    result.push(chunk);
  }
  return result.sort((a, b) => a - b);
}

function stage(
  pending: boolean | null, observations: unknown[], now: NullableNumber,
  previous: PagingStageDiagnostic | undefined,
): PagingStageDiagnostic {
  // All observations originate from the sanitized numbers/booleans below.
  const progress = JSON.stringify(observations);
  const priorSince = number(read(previous, 'sinceMs'));
  const sinceMs = pending === true && read(previous, 'progress') === progress
    && priorSince !== null && now !== null && priorSince <= now ? priorSince : now;
  const unchangedMs = now !== null && sinceMs !== null ? now - sinceMs : null;
  return {
    state: pending === null ? 'unknown' : !pending ? 'idle'
      : unchangedMs !== null && unchangedMs >= 10_000 ? 'waiting' : 'busy',
    unchangedMs: pending === true ? unchangedMs : null,
    sinceMs: pending === true ? sinceMs : null,
    progress,
  };
}

/**
 * Read-only device evidence, sampled independently of requestAnimationFrame.
 * "waiting" means ten seconds without an observed stage change, not a proven
 * hang. Hidden-page throttling and ordinary slow downloads are not failures.
 * No GPU readbacks, worker calls, network calls, error text or asset URLs.
 */
export function snapshotPagingDiagnostics(input: PagingDiagnosticsInput): PagingDiagnostics {
  const spark = read(input, 'spark'), paged = read(input, 'paged');
  const transfer = read(input, 'network'), pager = read(spark, 'pager');
  const current = read(spark, 'current'), display = read(spark, 'display');
  const lastLod = read(spark, 'lastLod'), currentLod = read(spark, 'currentLod');
  const now = number(read(input, 'nowMs')), lastFrame = number(read(input, 'lastFrameMs'));
  const ageMs = now !== null && lastFrame !== null && lastFrame <= now ? now - lastFrame : null;
  const residentChunks = chunks(read(pager, 'pageToSplatsChunk'));
  const network = {
    pending: number(read(transfer, 'pending')), requested: number(read(transfer, 'requested')),
    bytes: number(read(transfer, 'bytes')), errorCount: count(read(transfer, 'errors')),
  };
  const fetchDecode = count(read(pager, 'fetchers'));
  const queues = {
    fetchDecode,
    decodeOrBackoff: fetchDecode !== null && network.pending !== null ? Math.max(0, fetchDecode - network.pending) : null,
    fetched: count(read(pager, 'fetched')), newUploads: count(read(pager, 'newUploads')),
    readyUploads: count(read(pager, 'readyUploads')), treeUpdates: count(read(pager, 'lodTreeUpdates')),
    lodRpc: rpcCount(read(spark, 'lodWorker')), sortRpc: rpcCount(read(spark, 'sortWorker')),
  };
  const selection = {
    traversed: number(read(paged, 'numSplats')), current: number(read(current, 'numSplats')),
    displayed: number(read(display, 'numSplats')), active: number(read(spark, 'activeSplats')),
    residentPages: residentChunks?.length ?? null, residentChunks,
    currentMapping: number(read(current, 'mappingVersion')), displayMapping: number(read(display, 'mappingVersion')),
    sorting: boolean(read(spark, 'sorting')),
  };
  const previousStages = read(read(input, 'previous'), 'stages');
  const previous = (key: PagingStage) => read(previousStages, key) as PagingStageDiagnostic | undefined;
  const stages = {
    network: stage(positive(network.pending), [network.pending, network.requested, network.bytes, network.errorCount], now, previous('network')),
    decode: stage(positive(queues.decodeOrBackoff), [queues.decodeOrBackoff, queues.fetched, residentChunks, network.requested, network.bytes], now, previous('decode')),
    lod: stage(any(boolean(read(spark, 'lodDirty')), positive(queues.lodRpc, queues.treeUpdates, queues.fetched, queues.newUploads, count(read(spark, 'lodInitQueue')))),
      [queues.lodRpc, queues.treeUpdates, queues.fetched, queues.newUploads, selection.traversed,
        number(read(lastLod, 'timestamp')), number(read(currentLod, 'timestamp')), number(read(spark, 'lastLodRaycastTime'))], now, previous('lod')),
    upload: stage(positive(queues.readyUploads), [queues.readyUploads, residentChunks, selection.currentMapping], now, previous('upload')),
    display: stage(any(selection.sorting, boolean(read(spark, 'sortDirty')), positive(queues.sortRpc),
      selection.currentMapping !== null && selection.displayMapping !== null ? selection.currentMapping !== selection.displayMapping : null),
      [selection.sorting, queues.sortRpc, selection.current, selection.displayed, selection.active,
        selection.currentMapping, selection.displayMapping, number(read(spark, 'lastSortTime'))], now, previous('display')),
  };
  const keys = Object.keys(stages) as PagingStage[];
  const pendingStage = keys.find(key => stages[key].state === 'waiting')
    ?? keys.find(key => stages[key].state === 'busy');
  const phase = pendingStage ?? (keys.some(key => stages[key].state === 'unknown') ? 'unknown'
    : selection.active !== null && selection.active > 0 ? 'settled' : 'initializing');
  return {
    schemaVersion: 1, sparkVersion: '2.4.0', sampledAtMs: now,
    available: spark !== undefined && spark !== null, phase,
    heartbeat: {
      state: read(input, 'visibility') === 'hidden' ? 'hidden' : ageMs === null ? 'not-observed' : ageMs >= 2000 ? 'paused' : 'rendering',
      frames: number(read(input, 'frameCount')), lastFrameMs: lastFrame, ageMs,
    },
    runtime: {
      lodSplatCount: number(read(spark, 'lodSplatCount')), lodSplatScale: number(read(spark, 'lodSplatScale')),
      lodRenderScale: number(read(spark, 'lodRenderScale')), maxPagedSplats: number(read(spark, 'maxPagedSplats')),
      traversalBudget: number(read(lastLod, 'maxSplats')), pixelScaleLimit: number(read(lastLod, 'pixelScaleLimit')),
      renderWidth: number(read(read(spark, 'renderSize'), 'x')), renderHeight: number(read(read(spark, 'renderSize'), 'y')),
    },
    network, queues, selection, stages,
  };
}
