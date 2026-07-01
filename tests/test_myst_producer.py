"""T4 — producer test (offline).

The MyST project that actually runs `{apidoc} sample` must make intra-project
references to `sample.Match` (class) and `sample.match` (function) resolve
**case-sensitively** (to distinct targets), proving BOTH §6 mechanisms:

  (a) Option A — self-inventory: the served objects.inv is registered as
      `references: self`, and `xref:self#sample.Match` / `xref:self#sample.match`
      resolve via the case-sensitive inventory resolver to distinct urls.
  (b) Option B — plugin `{py}` role: emits a fully-resolved, case-preserved
      link (non-fragment) directly from the extractor's object table.
"""
from harness import (
    REPO,
    myst_build_all,
    md_links,
    serve_inventory,
    write_project,
    xml_hrefs,
)

PLUGIN = str(REPO / "dist" / "index.mjs")
INV = REPO / "build" / "objects.inv"


def test_myst_producer(tmp_path):
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
                    ":::{apidoc} sample\n"
                    ":::\n\n"
                    "[clsref](xref:self#sample.Match)\n\n"
                    "[fnref](xref:self#sample.match)\n\n"
                    "role class {py}`sample.Match`\n\n"
                    "role func {py}`sample.match`\n"
                )
            },
        )
        result = myst_build_all(tmp_path)

    # (a) INVENTORY path (Option A) — distinct, case-correct, fully resolved.
    links = md_links(tmp_path)
    cls, fn = links["clsref"], links["fnref"]
    assert cls.endswith("#sample.Match"), cls
    assert fn.endswith("#sample.match"), fn
    assert cls != fn, (cls, fn)
    assert "xref:" not in cls and "xref:" not in fn, (cls, fn)
    assert "not resolve" not in result.stderr and "not found" not in result.stderr, (
        result.stderr
    )

    # (b) ROLE path (Option B) — {py} emits case-preserved links to both.
    hrefs = xml_hrefs(tmp_path)
    assert "api.html#sample.Match" in hrefs, hrefs
    assert "api.html#sample.match" in hrefs, hrefs
