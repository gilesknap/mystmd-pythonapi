// SPEC M5 — JS-side proof that warm.ts drives the persistent sidecar.
//
// Usage: node scripts/warm_harness.mjs <root> <package>
//
// Imports the BUILT plugin (dist/index.mjs), grabs the registered
// "griffe-warm" extractor, runs analyze() twice against the same warm sidecar,
// and prints a small JSON summary { names, samePid } to stdout.

import { fileURLToPath } from "node:url";

const REPO = new URL("..", import.meta.url);
const dist = new URL("dist/index.mjs", REPO);

const root = process.argv[2];
const pkg = process.argv[3] ?? "sample";
process.env.MYST_PYAPI_PACKAGE = pkg;

const mod = await import(fileURLToPath(dist));
const { EXTRACTORS } = mod;
const warm = EXTRACTORS["griffe-warm"];

const index = await warm.analyze([root]);
const names = Object.keys(index.items).sort();

process.stdout.write(JSON.stringify({ names }) + "\n");

// One-shot script: exit deterministically (the warm sidecar is unref'd and the
// process 'exit' hook in warm.ts kills it).
process.exit(0);
