"""T8 — the headline scenario, as ONE explicit test (SPEC T8).

`sample.Match` (class) and `sample.match` (function) are simultaneously
documented AND independently linkable WITHOUT collision, and the exported
`objects.inv` distinguishes them. This single test folds together a little of
T1 (inventory) and T4 (myst producer) logic on purpose — it is the one
sentence the whole project pivots on, proven end-to-end and offline.

Three legs, all in one test:
  (1) INVENTORY — sphobjinv: distinct rows for the class/function/method.
  (2) PRODUCER — myst plugin + served self-inventory: a page that runs
      {apidoc} sample and references both, resolving to DISTINCT urls with no
      unresolved-reference warnings.
  (3) RENDERED — the exported AST exposes BOTH exact-case targets.
"""
from sphobjinv import Inventory

from harness import REPO, md_links, myst_build_all, serve_inventory, write_project, xml_hrefs

INV = REPO / "build" / "objects.inv"
PLUGIN = REPO / "dist" / "index.mjs"


def _row(inv, name):
    rows = [o for o in inv.objects if o.name == name]
    assert len(rows) == 1, f"expected exactly one {name!r}, got {len(rows)}"
    return rows[0]


def test_case_clash(tmp_path):
    # ---- (1) INVENTORY: Match (class) and match (function) are distinct rows.
    inv = Inventory(str(INV))
    cls = _row(inv, "sample.Match")
    func = _row(inv, "sample.match")
    method = _row(inv, "sample.Match.group")

    assert (cls.domain, cls.role) == ("py", "class"), (cls.domain, cls.role)
    assert (func.domain, func.role) == ("py", "function"), (func.domain, func.role)
    assert (method.domain, method.role) == ("py", "method"), (method.domain, method.role)
    # Case-sensitive identity: same spelling but for case, yet distinct targets.
    assert cls.name != func.name
    assert cls.name.lower() == func.name.lower()
    assert cls.uri_expanded != func.uri_expanded, (cls.uri_expanded, func.uri_expanded)

    # ---- (2) PRODUCER: {apidoc} sample + self-inventory; both xrefs resolve.
    with serve_inventory(INV) as base:
        write_project(
            tmp_path,
            "version: 1\n"
            "project:\n"
            "  plugins:\n"
            f"    - {PLUGIN}\n"
            "  references:\n"
            f"    self: {base}\n"
            "  exports:\n"
            "    - format: md\n"
            "      output: out.md\n"
            "    - format: xml\n"
            "      output: out.xml\n",
            {
                "index.md": (
                    "```{apidoc} sample\n```\n\n"
                    "[fnref](xref:self#sample.match)\n\n"
                    "[clsref](xref:self#sample.Match)\n"
                )
            },
        )
        result = myst_build_all(tmp_path)

    links = md_links(tmp_path)
    fn, cl = links["fnref"], links["clsref"]

    # Both resolved (not left as raw xref:), to DISTINCT, case-correct urls.
    assert fn.endswith("/api.html#sample.match"), fn
    assert cl.endswith("/api.html#sample.Match"), cl
    assert fn != cl, (fn, cl)
    assert "xref:self" not in fn and "xref:self" not in cl
    # No unresolved-reference warnings for the valid case-clash pair.
    assert "not resolve" not in result.stderr and "not found" not in result.stderr, result.stderr

    # ---- (3) RENDERED: the exported AST exposes BOTH exact-case targets.
    hrefs = xml_hrefs(tmp_path)
    assert any(h.endswith("#sample.Match") for h in hrefs), hrefs
    assert any(h.endswith("#sample.match") for h in hrefs), hrefs
    # And they are genuinely two different targets, not one folded onto the other.
    assert len({h for h in hrefs if h.rsplit("#", 1)[-1].lower() == "sample.match"}) == 2, hrefs
