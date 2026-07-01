"""T7 (SPEC T7) — public-API enumeration via the griffe extractor.

Runs python/extract.py per fixture package and asserts the enumerated item
fullNames / roots.

Canonicalization policy (R7 / T7a)
----------------------------------
A name re-exported from a package ``__init__`` is recorded under its PUBLIC
path, not its private definition site. The extractor uses griffe's
``alias.path`` (the public path ``sample.Match``) rather than
``alias.canonical_path`` (the private ``sample._core.Match``); the anchor
equals the fullName, so both are the public path. Thus ``fixtures/sample``
yields ``sample.Match`` / ``sample.match`` and NEVER ``sample._core.Match``.

Public MEMBERSHIP honours ``__all__`` — resolved by runtime import so a
DYNAMICALLY built ``__all__`` (all_dynamic, R7) is handled identically to a
literal one (all_static).
"""
import json
import subprocess

from harness import REPO

VENV_PY = str(REPO / ".venv" / "bin" / "python")
EXTRACT = str(REPO / "python" / "extract.py")
FIXTURES = str(REPO / "fixtures")


def extract(package, roots=FIXTURES):
    """Run the griffe extractor for `package` and return the parsed ApiIndex."""
    result = subprocess.run(
        [VENV_PY, EXTRACT, "--roots", roots, "--package", package],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def public_names(index, root):
    """Direct public children of the root package, as bare names."""
    prefix = root + "."
    return {
        item["fullName"][len(prefix):]
        for item in index["items"].values()
        if item["fullName"].startswith(prefix)
        and "." not in item["fullName"][len(prefix):]
    }


# --------------------------------------------------------------------------
# (a) re-import canonicalization: public path wins
# --------------------------------------------------------------------------
def test_sample_reimports_use_public_path():
    idx = extract("sample")
    items = idx["items"]

    assert idx["roots"] == ["sample"]

    # canonical fullNames are the PUBLIC ones ...
    assert "sample.Match" in items
    assert "sample.match" in items
    # ... never the private definition site.
    assert "sample._core.Match" not in items
    assert "sample._core.match" not in items

    # both present and distinct (class vs function, case-sensitive).
    assert items["sample.Match"]["fullName"] == "sample.Match"
    assert items["sample.match"]["fullName"] == "sample.match"
    assert items["sample.Match"]["fullName"] != items["sample.match"]["fullName"]
    assert items["sample.Match"]["kind"] == "class"
    assert items["sample.match"]["kind"] == "function"


# --------------------------------------------------------------------------
# (b) nested subpackage with its own children
# --------------------------------------------------------------------------
def test_sample_nested_subpackage():
    items = extract("sample")["items"]

    assert "sample.subpkg" in items
    assert items["sample.subpkg"]["kind"] == "module"

    # subpkg owns its members.
    assert "sample.subpkg.Widget" in items
    assert "sample.subpkg.build" in items
    assert items["sample.subpkg.Widget"]["kind"] == "class"
    assert items["sample.subpkg.build"]["kind"] == "function"

    # they are recorded as children of the subpackage.
    assert "sample.subpkg.Widget" in items["sample.subpkg"]["children"]
    assert "sample.subpkg.build" in items["sample.subpkg"]["children"]


# --------------------------------------------------------------------------
# (c) literal __all__
# --------------------------------------------------------------------------
def test_all_static_public_names_exact():
    idx = extract("all_static")
    assert idx["roots"] == ["all_static"]
    assert public_names(idx, "all_static") == {"a", "B"}


# --------------------------------------------------------------------------
# (d) dynamically built __all__ (R7 robustness) — same result as literal
# --------------------------------------------------------------------------
def test_all_dynamic_public_names_exact():
    idx = extract("all_dynamic")
    assert idx["roots"] == ["all_dynamic"]
    assert public_names(idx, "all_dynamic") == {"a", "B"}
