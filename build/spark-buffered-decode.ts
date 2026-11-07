/**
 * Narrow workaround for buffered RAD decoding in pinned Spark 2.4.0.
 * Upstream: https://github.com/sparkjsdev/spark/issues/481
 * Already-buffered bytes do not need a synthetic ReadableStream. Keep actual
 * URL/chunked streaming unchanged. This transforms the published ESM module at
 * build/dev time; node_modules and Spark's WASM implementation stay untouched.
 */
export const bufferedBranch = `if (fileBytes) {
\t\t\treadStream = new ReadableStream({ start(controller) {
\t\t\t\tcontroller.enqueue(fileBytes);
\t\t\t\tcontroller.close();
\t\t\t} });
\t\t\tstreamLength = fileBytes.length;
\t\t} else if (url) {`;

export const directBranch = `if (fileBytes) {
\t\t\tsendStatus({ loaded: fileBytes.length, total: fileBytes.length });
\t\t\tdecoder.push(fileBytes);
\t\t\treturn decoder.finish();
\t\t} else if (url) {`;

// Spark's ESM distribution embeds worker source in a quoted string:
// newlines are escaped, tabs remain literal. Fail closed if it changes.
const embedded = (source: string) => source.replaceAll('\n', '\\n');

export const isSparkWorkerModule=(id:string)=>id.replaceAll('\\','/').split(/[?#]/,1)[0].endsWith('/@sparkjsdev/spark/dist/spark.module.js');

export function patchBufferedSparkWorker(source: string): string {
  const before=embedded(bufferedBranch), after=embedded(directBranch);
  if(source.split(before).length!==2)throw new Error('Spark 2.4.0 buffered decoder patch: expected exactly one known worker branch. Revalidate the upstream package.');
  return source.replace(before,after);
}
