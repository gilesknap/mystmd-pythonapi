// Node entrypoint: build an ApiIndex and write build/objects.inv.
//
// Extractor selection (keeps the stub as the DEFAULT so run_all.sh stays green):
//   MYST_PYAPI_EXTRACTOR   "stub" (default) | "griffe"
//   MYST_PYAPI_ROOTS       comma-separated search paths (griffe; default "fixtures")
//   MYST_PYAPI_PACKAGE     package import name    (griffe; default "sample")

import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import type { ApiIndex } from "./ir.js";
import { buildStubIndex } from "./extractor/stub.js";
import { analyzeSync } from "./extractor/griffe.js";
import { writeInventoryFile } from "./inventory/objectsInv.js";

function buildIndex(): ApiIndex {
  const which = process.env.MYST_PYAPI_EXTRACTOR ?? "stub";
  if (which === "griffe") {
    const roots = (process.env.MYST_PYAPI_ROOTS ?? "fixtures")
      .split(",")
      .filter(Boolean);
    const pkg = process.env.MYST_PYAPI_PACKAGE ?? "sample";
    return analyzeSync(roots, pkg);
  }
  return buildStubIndex();
}

function main(): void {
  const index = buildIndex();
  const outPath = resolve(process.cwd(), "build", "objects.inv");
  mkdirSync(dirname(outPath), { recursive: true });

  writeInventoryFile(outPath, index, {
    project: process.env.MYST_PYAPI_PROJECT ?? "sample",
    version: process.env.MYST_PYAPI_VERSION ?? "0.1.0",
    pageUriFor: () => process.env.MYST_PYAPI_PAGE ?? "api.html",
  });

  const rowCount = Object.keys(index.items).length;
  console.log(`Wrote ${rowCount} rows to ${outPath}`);
}

main();
