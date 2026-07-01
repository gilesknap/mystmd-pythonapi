"""M2 — "swap behind the interface" (SPEC R5).

Prove the griffe extractor feeds the whole linking layer *identically* to the
stub. We drive the real Node CLI with MYST_PYAPI_EXTRACTOR=griffe to emit an
objects.inv sourced from griffe (not the stub), then show:

  (1) the griffe-sourced inventory carries the SAME key rows as the stub, with
      correct py domain roles and DISTINCT explicit anchors (case-correct); and
  (2) mystmd resolves xref:sample#sample.Match vs xref:sample#sample.match to
      DISTINCT urls end-to-end (same serve_inventory + myst_build_all + md_links
      oracle as test_north_star_re).

This is the extractor-swappability proof: nothing downstream of the Extractor
interface knows or cares that griffe produced the rows.
"""
import sphobjinv

from harness import (
    NODE,
    REPO,
    VENV_PY,
    md_links,
    myst_build_all,
    run,
    serve_inventory,
    write_project,
)


def _generate_griffe_inventory(work_dir):
    """Run the real Node CLI with the griffe extractor; return the .inv path.

    The dist CLI writes to <cwd>/build/objects.inv, so we point cwd at a temp
    dir. Everything else (extractor, roots, package, python) comes from env —
    exactly how a downstream consumer would swap extractors.
    """
    inv_out = work_dir / "objects.inv"
    result = run(
        [NODE, str(REPO / "dist" / "cli.mjs")],
        cwd=str(work_dir),
        env={
            "MYST_PYAPI_EXTRACTOR": "griffe",
            "MYST_PYAPI_ROOTS": str(REPO / "fixtures"),
            "MYST_PYAPI_PACKAGE": "sample",
            "MYST_PYAPI_INV": str(inv_out),
            "MYST_PYAPI_PYTHON": VENV_PY,
        },
    )
    assert result.returncode == 0, f"griffe CLI failed:\n{result.stdout}\n{result.stderr}"
    produced = work_dir / "build" / "objects.inv"
    assert produced.exists(), f"no inventory written:\n{result.stdout}\n{result.stderr}"
    return produced


# Key rows the stub canonicalizes; the griffe inventory MUST reproduce these
# exact (name, domain:role) pairs — case included.
EXPECTED_ROWS = {
    "sample.Match": "py:class",
    "sample.match": "py:function",
    "sample.Match.group": "py:method",
}


def test_griffe_inventory_has_stub_key_rows(tmp_path):
    inv_path = _generate_griffe_inventory(tmp_path)
    inv = sphobjinv.Inventory(str(inv_path))

    by_name = {o.name: o for o in inv.objects}
    for name, role in EXPECTED_ROWS.items():
        assert name in by_name, f"{name!r} missing from griffe inventory: {sorted(by_name)}"
        got = f"{by_name[name].domain}:{by_name[name].role}"
        assert got == role, f"{name}: expected {role}, got {got}"

    # Case-correctness: the mixed-case class row is distinct from the lowercase
    # function row (no case folding collapsed them).
    assert "sample.match" in by_name and "sample.Match" in by_name

    # Distinct EXPLICIT anchors — each key row targets its own fragment, and the
    # class/function anchors differ only by case.
    anchors = {name: by_name[name].uri for name in EXPECTED_ROWS}
    assert len(set(anchors.values())) == len(anchors), anchors
    assert anchors["sample.Match"].split("#")[-1] == "sample.Match"
    assert anchors["sample.match"].split("#")[-1] == "sample.match"
    assert anchors["sample.Match"] != anchors["sample.match"]


def test_griffe_inventory_resolves_distinct_xrefs(tmp_path):
    inv_path = _generate_griffe_inventory(tmp_path)

    proj = tmp_path / "proj"
    with serve_inventory(inv_path) as base:
        write_project(
            proj,
            "version: 1\n"
            "project:\n"
            "  references:\n"
            f"    sample: {base}\n"
            "  exports:\n"
            "    - format: md\n"
            "      output: out.md\n"
            "    - format: xml\n"
            "      output: out.xml\n",
            {
                "index.md": (
                    "[fnref](xref:sample#sample.match)\n\n"
                    "[clsref](xref:sample#sample.Match)\n"
                )
            },
        )
        result = myst_build_all(proj)

    links = md_links(proj)
    fn, cls = links["fnref"], links["clsref"]

    # Both resolved (not left as raw xref:) to DISTINCT, case-correct fragments.
    assert fn.endswith("#sample.match"), fn
    assert cls.endswith("#sample.Match"), cls
    assert fn != cls, (fn, cls)
    assert "xref:sample" not in fn and "xref:sample" not in cls
    assert "not resolve" not in result.stderr and "not found" not in result.stderr, result.stderr
