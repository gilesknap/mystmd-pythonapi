#!/usr/bin/env python
"""SPEC M2/M3/M4 — griffe-backed Python API extractor (one-shot CLI).

CLI:
    python extract.py --roots <dir>[,<dir>] --package <name>

Prints an ApiIndex JSON `{ "items": { fullName: ApiItem }, "roots": [...] }`
to stdout, matching the §8 IR in src/ir.ts (plus the docstringSections
extension).

The extraction logic lives in ``pyapi_extract`` (shared with the persistent
``sidecar.py``); this file is a thin CLI wrapper so run_all's griffe/swap
tests keep calling ``extract.py`` unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyapi_extract import build_index  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="griffe ApiIndex extractor")
    ap.add_argument("--roots", required=True, help="comma-separated search paths")
    ap.add_argument("--package", required=True, help="package/module import name")
    args = ap.parse_args(argv)

    roots = [r for r in args.roots.split(",") if r]
    index = build_index(roots, args.package)
    json.dump(index, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
