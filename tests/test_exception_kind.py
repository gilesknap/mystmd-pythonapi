"""Transitive exception classification (`_is_exception`).

`class NetworkIssue(Retryable)` where `Retryable(Exception)` must be emitted as
`kind == "exception"`, not `class` — even though `NetworkIssue`'s only DIRECT
base is `Retryable` (whose short name is neither `Exception` nor `*Error`). The
direct-base-only heuristic misclassified it; the fix walks the resolved MRO.
"""
import json
import subprocess

from harness import REPO, VENV_PY

EXTRACT = str(REPO / "python" / "extract.py")
FIXTURES = str(REPO / "fixtures")


def _extract(package):
    proc = subprocess.run(
        [VENV_PY, EXTRACT, "--roots", FIXTURES, "--package", package],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["items"]


def test_transitive_exception_classification():
    items = _extract("exc")

    # direct subclass of Exception
    assert items["exc.Retryable"]["kind"] == "exception"
    # INDIRECT subclass (Exception reached only via Retryable) — the fix
    assert items["exc.NetworkIssue"]["kind"] == "exception"
    # a class not in any exception chain stays a plain class
    assert items["exc.PlainThing"]["kind"] == "class"
