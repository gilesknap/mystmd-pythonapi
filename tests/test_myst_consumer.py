"""T3 — myst consumes OUR inventory case-sensitively (offline).

Serve build/objects.inv locally and consume it with mystmd. The class
`sample.Match` and the function `sample.match` must resolve to DISTINCT,
case-correct urls, while a bogus target `sample.Nope` stays unresolved and
warns — proving consumer-side case-sensitivity against our own inventory.
"""
from harness import REPO, md_links, myst_build_all, serve_inventory, write_project

INV = REPO / "build" / "objects.inv"


def test_myst_consumer(tmp_path):
    with serve_inventory(INV) as base:
        write_project(
            tmp_path,
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
                    "[clsref](xref:sample#sample.Match)\n\n"
                    "[fnref](xref:sample#sample.match)\n\n"
                    "[bogus](xref:sample#sample.Nope)\n"
                )
            },
        )
        result = myst_build_all(tmp_path)

    links = md_links(tmp_path)
    cls, fn = links["clsref"], links["fnref"]

    # valid pair resolved to distinct, case-correct urls (not raw xref:)
    assert cls.endswith("#sample.Match"), cls
    assert fn.endswith("#sample.match"), fn
    assert cls != fn, (cls, fn)
    assert "xref:" not in cls and "xref:" not in fn
    # no unresolved-reference warnings for the valid pair (bogus is expected below)
    warn_lines = [
        ln for ln in result.stderr.splitlines()
        if ("not resolve" in ln or "not found" in ln)
    ]
    assert not any(
        ("sample.Match" in ln or "sample.match" in ln) for ln in warn_lines
    ), result.stderr

    # negative control: bogus stays unresolved and warns
    assert "xref:" in links["bogus"], links["bogus"]
    assert "sample.Nope" in result.stderr, result.stderr
