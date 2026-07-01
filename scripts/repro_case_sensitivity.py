"""Reproducer: mystmd's `$`-anchor lowercasing (FINDINGS.md §1).

Builds two inventories from the vendored trimmed CPython rows — one keeping the
Sphinx `$` shorthand, one with explicit anchors — serves each over localhost
http, points a MyST project at each, and prints the resolved URLs for
`xref:python#re.match` vs `xref:python#re.Match`.

Expected output (mystmd v1.10.1):
  [dollar]   both resolve to .../re.html#re.match          -> COLLAPSED
  [explicit] re.match -> #re.match, re.Match -> #re.Match  -> DISTINCT

Run:  .venv/bin/python scripts/repro_case_sensitivity.py
"""
import functools
import http.server
import pathlib
import re
import shutil
import socketserver
import subprocess
import tempfile
import textwrap
import threading

import sphobjinv as soi

REPO = pathlib.Path(__file__).resolve().parent.parent
MYST = str(REPO / "node_modules" / ".bin" / "myst")
SRC_INV = REPO / "fixtures" / "inv" / "python.objects.inv"

WORK = pathlib.Path(tempfile.mkdtemp(prefix="repro-case-"))
srv = WORK / "srv"
for sub in ("dollar", "explicit"):
    (srv / sub).mkdir(parents=True, exist_ok=True)

src = soi.Inventory(str(SRC_INV))


def build_inv(explicit):
    out = soi.Inventory()
    out.project, out.version = "Python", "3"
    for o in src.objects:
        # our vendored inv already stores explicit anchors; re-introduce the `$`
        # shorthand for the "dollar" case to demonstrate the collapse.
        uri = o.uri_expanded if explicit else re.sub(re.escape(o.name) + r"$", "$", o.uri_expanded)
        out.objects.append(soi.DataObjStr(
            name=o.name, domain=o.domain, role=o.role,
            priority=o.priority, uri=uri, dispname=o.dispname))
    return out


for sub, ex in (("dollar", False), ("explicit", True)):
    inv = build_inv(ex)
    soi.writebytes(str(srv / sub / "objects.inv"), soi.compress(inv.data_file()))
    peek = {o.name: o.uri for o in inv.objects if o.name in ("re.match", "re.Match")}
    print(f"[{sub}] stored uris: {peek}")

PORT = 8123
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(srv))
httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def run_case(key):
    d = WORK / ("proj_" + key)
    d.mkdir(exist_ok=True)
    (d / "myst.yml").write_text(textwrap.dedent(f"""\
        version: 1
        project:
          title: t
          references:
            python: http://127.0.0.1:{PORT}/{key}
          exports:
            - format: md
              output: out.md
        """))
    (d / "index.md").write_text(
        "[fnref](xref:python#re.match)\n\n[clsref](xref:python#re.Match)\n")
    subprocess.run([MYST, "build", "--all"], cwd=str(d), capture_output=True, text=True)
    md = (d / "out.md").read_text()
    links = {m.group(1): m.group(2) for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", md)}
    fn, cls = links.get("fnref"), links.get("clsref")
    print(f"\n=== CASE {key} ===")
    print(f"  re.match -> {fn}")
    print(f"  re.Match -> {cls}")
    print(f"  DISTINCT: {fn != cls}")


run_case("dollar")
run_case("explicit")
httpd.shutdown()
shutil.rmtree(WORK, ignore_errors=True)
