"""Warm analyzer must not leak runtime imports across root changes.

The persistent sidecar keeps one `Analyzer` alive. If it analyzes package `pkg`
at root A and later at root B (same package name, different sources) WITHOUT an
intervening `invalidate`, the process-global `sys.modules` cache would otherwise
make `_runtime_all` return A's `__all__` for the B request. This drives both
analyses in ONE process (as the sidecar does) and asserts B wins.
"""
import json
import subprocess
import textwrap

from harness import REPO, VENV_PY


def _make_pkg(root, marker):
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        f'__all__ = ["{marker}"]\n\n\ndef {marker}():\n    """f."""\n'
    )
    return root


def test_warm_analyze_across_roots_no_stale_imports(tmp_path):
    root_a = _make_pkg(tmp_path / "a", "a_only")
    root_b = _make_pkg(tmp_path / "b", "b_only")

    probe = textwrap.dedent(
        """
        import json, sys
        sys.path.insert(0, sys.argv[1])           # repo/python
        from pyapi_extract import Analyzer
        az = Analyzer()
        a = az.analyze([sys.argv[2]], "pkg")      # root A
        b = az.analyze([sys.argv[3]], "pkg")      # root B, NO invalidate
        print(json.dumps({"a": sorted(a["items"]), "b": sorted(b["items"])}))
        """
    )
    proc = subprocess.run(
        [VENV_PY, "-c", probe, str(REPO / "python"), str(root_a), str(root_b)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)

    assert out["a"] == ["pkg", "pkg.a_only"]
    # Without the fix, B reuses sys.modules["pkg"] from A → "pkg.a_only".
    assert out["b"] == ["pkg", "pkg.b_only"], out["b"]
