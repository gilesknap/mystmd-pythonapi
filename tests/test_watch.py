"""SPEC M5 §7 — WARM service + watch-mode smoke test (offline).

Proves the persistent griffe sidecar (python/sidecar.py):

  * serves MULTIPLE analyses from ONE process (griffe stays warm), and
  * reflects on-disk EDITS after an ``invalidate`` WITHOUT a cold restart —
    the PID is identical before and after the edit + re-analyze.

Also drives the BUILT warm extractor (dist/index.mjs -> src/extractor/warm.ts)
via a tiny Node harness to prove warm.ts speaks the sidecar protocol from JS.
If that JS sync-stdio sub-check ever proves flaky it is xfailed with a reason;
the Python-level assertions above are the load-bearing proof and never xfail.
"""
import json
import os
import shutil
import subprocess

from harness import NODE, REPO, VENV_PY

SIDECAR = str(REPO / "python" / "sidecar.py")
WARM_HARNESS = str(REPO / "scripts" / "warm_harness.mjs")
SAMPLE_SRC = REPO / "fixtures" / "sample"


class Sidecar:
    """Thin newline-JSON client for a persistent sidecar subprocess."""

    def __init__(self):
        self.proc = subprocess.Popen(
            [VENV_PY, SIDECAR],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._id = 0

    def request(self, **cmd):
        self._id += 1
        cmd["id"] = self._id
        self.proc.stdin.write(json.dumps(cmd) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        assert line, "sidecar produced no response (died?)"
        resp = json.loads(line)
        assert resp["id"] == cmd["id"], (resp, cmd)
        assert resp["ok"], resp
        return resp

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        self.proc.wait(timeout=10)


def _copy_sample(dest_pkgroot):
    """Copy fixtures/sample into dest_pkgroot/sample (no stale __pycache__)."""
    dest = dest_pkgroot / "sample"
    shutil.copytree(SAMPLE_SRC, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def test_warm_sidecar_reflects_edits_without_restart(tmp_path):
    pkgroot = tmp_path / "pkgroot"
    pkgroot.mkdir()
    sample = _copy_sample(pkgroot)
    roots = [str(pkgroot)]

    sc = Sidecar()
    try:
        pid_before = sc.request(cmd="ping")["pid"]

        idx = sc.request(cmd="analyze", roots=roots, package="sample")["index"]
        items = idx["items"]
        assert "sample.match" in items
        assert "sample.brandnew" not in items  # not added yet

        # EDIT the temp copy on disk: add a brand-new public function.
        core = sample / "_core.py"
        core.write_text(core.read_text() + "\n\ndef brandnew():\n    ...\n")
        init = sample / "__init__.py"
        init.write_text(
            '"""Sample package mirroring :py:mod:`re`, with a case clash."""\n'
            "from ._core import Match, match, brandnew\n"
            "from . import subpkg\n\n"
            '__all__ = ["Match", "match", "brandnew", "subpkg"]\n'
        )

        # Without invalidation the warm caches would still hide the edit; after
        # invalidate + re-analyze the new name appears.
        sc.request(cmd="invalidate", package="sample")
        idx2 = sc.request(cmd="analyze", roots=roots, package="sample")["index"]
        items2 = idx2["items"]
        assert "sample.brandnew" in items2, sorted(items2)
        assert items2["sample.brandnew"]["kind"] == "function"

        # SAME process served both analyses (warm; no cold restart).
        pid_after = sc.request(cmd="ping")["pid"]
        assert pid_after == pid_before
    finally:
        sc.close()


def test_warm_extractor_drives_sidecar_from_js(tmp_path):
    """The built warm.ts extractor produces sample.match via the sidecar, and
    the harness proves the sidecar is REUSED (stable pid across an analyze)."""
    pkgroot = tmp_path / "pkgroot"
    pkgroot.mkdir()
    _copy_sample(pkgroot)

    result = subprocess.run(
        [NODE, WARM_HARNESS, str(pkgroot), "sample"],
        capture_output=True,
        text=True,
        env={**os.environ, "MYST_PYAPI_PYTHON": VENV_PY, "MYST_PYAPI_PACKAGE": "sample"},
        timeout=60,
    )
    assert result.returncode == 0, f"harness failed:\n{result.stdout}\n{result.stderr}"
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    names = set(payload["names"])
    assert "sample.match" in names, names
    assert "sample.Match" in names, names
    # the sidecar pid was unchanged across the analyze -> warm reuse, not restart
    assert payload["samePid"] is True, payload
