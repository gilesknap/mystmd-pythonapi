#!/usr/bin/env python
"""SPEC M5 §7 — PERSISTENT griffe sidecar (keeps griffe WARM).

A long-lived process: read newline-delimited JSON requests on stdin, write
newline-delimited JSON responses on stdout. griffe (the library) is imported
ONCE at startup and a single ``Analyzer`` (one GriffeLoader + import cache) is
reused across requests — no per-request re-import, no cold restart.

Protocol (responses are correlated to requests by ``id``):

    {"id":N,"cmd":"ping"}
        -> {"id":N,"ok":true,"pid":<os.getpid()>}

    {"id":N,"cmd":"analyze","roots":[...],"package":"p"}
        -> {"id":N,"ok":true,"index":{...ApiIndex...}}

    {"id":N,"cmd":"invalidate","package":"p"}
        -> {"id":N,"ok":true}       # drop cached module(s); next analyze re-reads

On any error:
        -> {"id":N,"ok":false,"error":"<message>"}

stdout is flushed after every response; the process exits cleanly on EOF.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyapi_extract import Analyzer  # noqa: E402


def _handle(analyzer: Analyzer, req: dict) -> dict:
    rid = req.get("id")
    cmd = req.get("cmd")
    if cmd == "ping":
        return {"id": rid, "ok": True, "pid": os.getpid()}
    if cmd == "analyze":
        roots = list(req.get("roots") or [])
        package = req["package"]
        index = analyzer.analyze(roots, package)
        return {"id": rid, "ok": True, "index": index}
    if cmd == "invalidate":
        analyzer.invalidate(req["package"])
        return {"id": rid, "ok": True}
    raise ValueError(f"unknown cmd: {cmd!r}")


def main() -> None:
    analyzer = Analyzer()
    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            resp = _handle(analyzer, req)
        except Exception as exc:  # noqa: BLE001 — protocol: report, keep serving
            resp = {"id": rid, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
        out.write(json.dumps(resp, ensure_ascii=False, separators=(",", ":")))
        out.write("\n")
        out.flush()


if __name__ == "__main__":
    main()
