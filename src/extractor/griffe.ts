// SPEC M2 — pluggable griffe extractor.
//
// This is the real extractor behind the §8 `Extractor` interface. It shells out
// to a Python sidecar (python/extract.py) that drives griffe for structure,
// signatures and docstrings, and prints an ApiIndex JSON to stdout.
//
// Why a subprocess: griffe is a Python library; the linking/rendering layer is
// Node. Analysis is amortized (module-scope memoized in cli/index), never paid
// per-directive (R2), so a synchronous execFileSync is fine here.

import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import type { ApiIndex, Extractor } from "../ir.js";

// Absolute path to python/extract.py, resolved relative to THIS module. The
// plugin/CLI is only ever executed from the bundled dist/*.mjs (never from src
// via tsx), where `../python/extract.py` resolves to the repo-root python/ dir.
// No src-relative fallback is needed. (Deploying python/ from PyPI — see issue
// #3 — would replace this path resolution with `python -m` invocation.)
function extractScriptPath(): string {
  return fileURLToPath(new URL("../python/extract.py", import.meta.url));
}

// Python interpreter: env override, else the repo venv. Resolved relative to
// python/extract.py's parent (repo root) when falling back to the venv.
function pythonPath(): string {
  const env = process.env.MYST_PYAPI_PYTHON;
  if (env) return env;
  return fileURLToPath(new URL("../.venv/bin/python", import.meta.url));
}

function defaultPackage(): string {
  return process.env.MYST_PYAPI_PACKAGE ?? "sample";
}

// Synchronous helper: run the sidecar for `roots`/`pkg`, parse ApiIndex JSON.
export function analyzeSync(roots: string[], pkg: string): ApiIndex {
  const script = extractScriptPath();
  const py = pythonPath();
  const stdout = execFileSync(
    py,
    [script, "--roots", roots.join(","), "--package", pkg],
    { encoding: "utf-8", maxBuffer: 64 * 1024 * 1024 },
  );
  const parsed = JSON.parse(stdout) as ApiIndex;
  return parsed;
}

export const griffeExtractor: Extractor = {
  name: "griffe",
  async analyze(packageRoots: string[]): Promise<ApiIndex> {
    return analyzeSync(packageRoots, defaultPackage());
  },
};
