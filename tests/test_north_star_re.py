"""T5 — north-star consumer test (offline).

Vendored trimmed CPython inventory (real library/re.html#... uris, explicit
anchors) is served locally and consumed by mystmd. `re.match` (function) and
`re.Match` (class) must resolve to DISTINCT CPython URLs — proving consumer-side
case-sensitivity end-to-end with no network.
"""
from harness import REPO, myst_build_all, md_links, serve_inventory, write_project

INV = REPO / "fixtures" / "inv" / "python.objects.inv"


def test_north_star_re(tmp_path):
    with serve_inventory(INV) as base:
        write_project(
            tmp_path,
            "version: 1\n"
            "project:\n"
            "  references:\n"
            f"    python: {base}\n"
            "  exports:\n"
            "    - format: md\n"
            "      output: out.md\n"
            "    - format: xml\n"
            "      output: out.xml\n",
            {
                "index.md": (
                    "[fnref](xref:python#re.match)\n\n"
                    "[clsref](xref:python#re.Match)\n"
                )
            },
        )
        result = myst_build_all(tmp_path)

    links = md_links(tmp_path)
    fn, cls = links["fnref"], links["clsref"]

    # both resolved (not left as raw xref:), to DISTINCT, case-correct CPython urls
    assert fn.endswith("/library/re.html#re.match"), fn
    assert cls.endswith("/library/re.html#re.Match"), cls
    assert fn != cls, (fn, cls)
    assert "xref:python" not in fn and "xref:python" not in cls
    # no unresolved-reference warnings for the valid pair
    assert "not resolve" not in result.stderr and "not found" not in result.stderr, result.stderr
