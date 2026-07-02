"""Shared test harness for the mystmd-pythonapi acceptance oracle.

Key facts baked in (see FINDINGS.md / memory `myst-inventory-namespace`):
- mystmd `references:` only accepts http(s) URLs, so a local objects.inv is served
  over an ephemeral localhost port (fully offline).
- The offline resolution oracle is `myst build --all` with md+xml exports and NO
  `site:` config (so no book-theme template fetch). Resolved xref urls appear as
  out.md link targets and out.xml `xlink:href`.
"""
from __future__ import annotations

import contextlib
import functools
import http.server
import os
import pathlib
import re
import shutil
import socketserver
import subprocess
import tempfile
import threading

REPO = pathlib.Path(__file__).resolve().parent.parent
# Honour an active venv ($VIRTUAL_ENV, e.g. a relocated cache venv); fall back to
# the in-repo .venv. Matches run_all.sh's VENV_PY resolution.
VENV = pathlib.Path(os.environ.get("VIRTUAL_ENV") or (REPO / ".venv"))
VENV_PY = str(VENV / "bin" / "python")
MYST = str(REPO / "node_modules" / ".bin" / "myst")
NODE = shutil.which("node") or "/usr/bin/node"
NPM = shutil.which("npm") or "/root/.local/bin/npm"


def run(cmd, cwd=None, env=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True)


@contextlib.contextmanager
def serve_inventory(inv_path):
    """Serve a dir containing objects.inv over localhost http; yield the base url.

    myst fetches `<base>/objects.inv`; the base is also the prefix of every
    resolved link, so resolved urls look like `<base>/library/re.html#re.Match`.
    """
    d = tempfile.mkdtemp(prefix="pyapi-inv-")
    shutil.copyfile(str(inv_path), os.path.join(d, "objects.inv"))
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=d)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        shutil.rmtree(d, ignore_errors=True)


def write_project(project_dir, myst_yml, pages):
    d = pathlib.Path(project_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / "myst.yml").write_text(myst_yml)
    for name, content in pages.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return d


EXPORTS_YAML = (
    "  exports:\n"
    "    - format: md\n"
    "      output: out.md\n"
    "    - format: xml\n"
    "      output: out.xml\n"
)


def myst_build_all(project_dir):
    """Run `myst build --all` from a clean state (offline; exports only)."""
    d = pathlib.Path(project_dir)
    for p in ("_build", "out.md", "out.xml"):
        pp = d / p
        if pp.is_dir():
            shutil.rmtree(pp, ignore_errors=True)
        elif pp.exists():
            pp.unlink()
    proc = run([MYST, "build", "--all"], cwd=str(d))
    assert proc.returncode == 0, (
        f"`myst build --all` failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )
    return proc


_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def md_links(project_dir):
    """Parse out.md → {link_text: resolved_url}."""
    md = (pathlib.Path(project_dir) / "out.md").read_text()
    return {m.group(1): m.group(2) for m in _LINK_RE.finditer(md)}


def xml_hrefs(project_dir):
    """All xlink:href values in the JATS export, in document order."""
    xml = (pathlib.Path(project_dir) / "out.xml").read_text()
    return re.findall(r'xlink:href="([^"]+)"', xml)


def build_plugin_and_inventory():
    """Build the plugin (.mjs) and generate build/objects.inv from the stub. Idempotent."""
    build = run([NPM, "run", "build"], cwd=str(REPO))
    assert build.returncode == 0, (
        f"`npm run build` failed\nSTDOUT:\n{build.stdout}\nSTDERR:\n{build.stderr}"
    )
    inv = run([NODE, str(REPO / "dist" / "cli.mjs")], cwd=str(REPO))
    assert inv.returncode == 0, (
        f"`cli.mjs` (inventory gen) failed\nSTDOUT:\n{inv.stdout}\nSTDERR:\n{inv.stderr}"
    )
