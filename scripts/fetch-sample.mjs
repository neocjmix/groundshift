#!/usr/bin/env node
import { createHash, randomUUID } from 'node:crypto';
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

// Pin both the upstream revision and content: a changed remote file must not
// silently change the scene used for browser validation.
const revision = 'c3e5ec0a8ddb3ab26f28a067a29d272fe1a23411';
const url = `https://raw.githubusercontent.com/marcelpadilla/splats/${revision}/data/plant/plant.splat`;
const expectedSha256 = 'ce9d490b18f16d6730d832227bf541431b8b1a5d167c5a3fe89af4f324c0d8fd';
const expectedBytes = 3_636_736;
const destination = fileURLToPath(new URL('../public/worlds/sample/plant.splat', import.meta.url));

function verify(bytes) {
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  if (bytes.length !== expectedBytes || sha256 !== expectedSha256) {
    throw new Error(`Sample integrity mismatch: ${bytes.length} bytes, SHA-256 ${sha256}. Expected ${expectedBytes} bytes, SHA-256 ${expectedSha256}.`);
  }
}

async function main() {
  if (process.argv.length > 2) {
    throw new Error('Usage: node scripts/fetch-sample.mjs (downloads the pinned, licensed Houseplant sample)');
  }

  try {
    const existing = await readFile(destination);
    verify(existing);
    console.log(`Verified existing Houseplant sample: ${destination} (${expectedBytes} bytes).`);
    return;
  } catch (error) {
    if (error.code !== 'ENOENT') {
      throw new Error(`Existing sample was not replaced. ${error.message}`, { cause: error });
    }
  }

  console.log('Downloading Houseplant by Marcel Padilla (CC-BY-4.0), 3.64 MB…');
  const response = await fetch(url, { signal: AbortSignal.timeout(60_000) });
  if (!response.ok) throw new Error(`Sample download failed: HTTP ${response.status} ${response.statusText}`);
  const bytes = Buffer.from(await response.arrayBuffer());
  verify(bytes);
  await mkdir(path.dirname(destination), { recursive: true });
  const temporary = `${destination}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporary, bytes, { flag: 'wx' });
    await rename(temporary, destination);
  } finally {
    await rm(temporary, { force: true });
  }
  console.log(`Verified and saved ${expectedBytes} bytes to ${destination}.`);
  console.log('Attribution and upstream license: public/worlds/sample/ATTRIBUTION.md');
}

main().catch((error) => {
  console.error(`Sample acquisition failed: ${error.message}`);
  process.exitCode = 1;
});
