// SPEC M5 — JS-side proof that warm.ts drives the persistent sidecar.
//
// Usage: node scripts/warm_harness.mjs <root> <package>
//
// Imports the BUILT plugin (dist/index.mjs), grabs the registered "griffe-warm"
// extractor, and proves warm REUSE: ping the sidecar, run analyze(), ping again,
// and check the pid is unchanged (a per-request cold restart would change it).
// Prints a small JSON summary { names, samePid } to stdout.

import { fileURLToPath } from "node:url";

const REPO = new URL("..", import.meta.url);
const dist = new URL("dist/index.mjs", REPO);

const root = process.argv[2];
const pkg = process.argv[3] ?? "sample";
process.env.MYST_PYAPI_PACKAGE = pkg;

const mod = await import(fileURLToPath(dist));
const { EXTRACTORS } = mod;
const warm = EXTRACTORS["griffe-warm"];

// ping -> analyze -> ping: a stable pid across the analyze proves the SAME warm
// sidecar served it (the module-scope SIDECAR singleton was reused, not respawned).
const pidBefore = warm.ping();
const index = await warm.analyze([root]);
const pidAfter = warm.ping();
const names = Object.keys(index.items).sort();
const samePid = pidBefore === pidAfter;

process.stdout.write(JSON.stringify({ names, samePid }) + "\n");

// One-shot script: exit deterministically (the warm sidecar is unref'd and the
// process 'exit' hook in warm.ts kills it).
process.exit(0);
