"""T6 — docstring-style equivalence (SPEC T6).

The SAME API documented in three different docstring conventions must parse to
an EQUIVALENT normalized section model. We run the griffe extractor
(python/extract.py) over fixtures/styles/{numpy_mod,google_mod,sphinx_mod}.py —
each defines ``combine(first, second)`` with Summary / Parameters(first,second)
/ Returns / Raises(ValueError) — pull the ``docstringSections`` for ``combine``
from each, and assert the three are equivalent after normalization:

* identical summary,
* same parameter names in the same order,
* a Returns section is present,
* Raises includes ``ValueError``.
"""
from __future__ import annotations

import json
import subprocess

from harness import REPO, VENV_PY

STYLES_DIR = REPO / "fixtures" / "styles"
MODULES = ["numpy_mod", "google_mod", "sphinx_mod"]


def _sections(module: str) -> dict:
    """Run the griffe extractor and return combine's docstringSections."""
    proc = subprocess.run(
        [
            VENV_PY,
            str(REPO / "python" / "extract.py"),
            "--roots",
            str(STYLES_DIR),
            "--package",
            module,
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    index = json.loads(proc.stdout)
    item = index["items"][f"{module}.combine"]
    sections = item.get("docstringSections")
    assert sections is not None, f"{module}: no docstringSections extracted"
    return sections


def _normalize(sections: dict) -> dict:
    """Reduce to the style-independent comparison model."""
    return {
        "summary": (sections.get("summary") or "").strip(),
        "param_names": [p["name"] for p in sections.get("parameters") or []],
        "returns_present": bool((sections.get("returns") or "").strip()),
        "raises_types": sorted(
            (r.get("type") or "").strip() for r in sections.get("raises") or []
        ),
    }


def test_docstring_styles_equivalent():
    normalized = {m: _normalize(_sections(m)) for m in MODULES}

    # Per-style sanity: each style must yield the expected shape.
    for module, norm in normalized.items():
        assert norm["summary"] == "Combine two values into a single result.", module
        assert norm["param_names"] == ["first", "second"], module
        assert norm["returns_present"], f"{module}: Returns section missing"
        assert "ValueError" in norm["raises_types"], f"{module}: ValueError missing"

    # Cross-style equivalence: all three normalize to the SAME model.
    numpy_norm = normalized["numpy_mod"]
    for module in ("google_mod", "sphinx_mod"):
        assert normalized[module] == numpy_norm, (
            f"{module} not equivalent to numpy_mod: "
            f"{normalized[module]} != {numpy_norm}"
        )
