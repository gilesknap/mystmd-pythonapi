"""SPEC T1 — validate the tool's generated build/objects.inv.

Run with: python -m pytest tests/test_objects_inv.py
"""

from pathlib import Path

import pytest
from sphobjinv import Inventory

REPO_ROOT = Path(__file__).resolve().parent.parent
INV_PATH = REPO_ROOT / "build" / "objects.inv"


@pytest.fixture(scope="module")
def inv() -> Inventory:
    assert INV_PATH.exists(), f"missing inventory: {INV_PATH}"
    return Inventory(str(INV_PATH))


def _find(inv: Inventory, name: str):
    matches = [o for o in inv.objects if o.name == name]
    assert len(matches) == 1, f"expected exactly one {name!r}, got {len(matches)}"
    return matches[0]


def test_valid_v2_inventory(inv: Inventory) -> None:
    # A successful zlib-compressed parse (SourceTypes.FnameZlib) is what makes
    # this a valid Sphinx inventory *format* v2. sphobjinv exposes the project's
    # own version string (not the format version) via `inv.version`.
    from sphobjinv import SourceTypes

    assert inv.source_type == SourceTypes.FnameZlib
    assert inv.project == "sample"
    assert inv.version == "0.1.0"


def test_match_function_and_class_distinct(inv: Inventory) -> None:
    func = _find(inv, "sample.match")
    cls = _find(inv, "sample.Match")

    assert func.domain == "py"
    assert func.role == "function"
    assert cls.domain == "py"
    assert cls.role == "class"

    # Distinct rows with distinct expanded uris (case-sensitive identity).
    assert func.uri_expanded != cls.uri_expanded


def test_method_exists(inv: Inventory) -> None:
    method = _find(inv, "sample.Match.group")
    assert method.domain == "py"
    assert method.role == "method"


def test_total_object_count(inv: Inventory) -> None:
    assert inv.count == 7
