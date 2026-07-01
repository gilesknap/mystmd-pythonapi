"""T2 — Sphinx consumer test (offline).

Prove that SPHINX (via sphinx.ext.intersphinx, nitpicky + warnings-as-errors)
consumes our generated `build/objects.inv` case-sensitively: `sample.Match`
(py:class) and `sample.match` (py:function) must resolve to DISTINCT,
case-correct URLs against the inventory, with the build succeeding under `-n -W`.
"""
import re
import subprocess

from harness import REPO

INV = REPO / "build" / "objects.inv"

CONF_PY = (
    "extensions = ['sphinx.ext.intersphinx']\n"
    "intersphinx_mapping = {\n"
    f"    'sample': ('http://example.test/sample', r'{INV}'),\n"
    "}\n"
    "nitpicky = True\n"
    "project = 't'\n"
    "author = 't'\n"
    "html_theme = 'basic'\n"
)

INDEX_RST = (
    "T2\n"
    "==\n"
    "\n"
    "Class ref: :py:class:`sample.Match`\n"
    "\n"
    "Func ref: :py:func:`sample.match`\n"
)


def test_sphinx_consumer(tmp_path):
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(CONF_PY)
    (srcdir / "index.rst").write_text(INDEX_RST)

    proc = subprocess.run(
        [
            str(REPO / ".venv" / "bin" / "sphinx-build"),
            "-n",
            "-W",
            "-b",
            "html",
            str(srcdir),
            str(outdir),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"sphinx-build failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )

    html = (outdir / "index.html").read_text()
    hrefs = re.findall(r'href="([^"]*api\.html#sample\.[^"]*)"', html)

    cls_hrefs = [h for h in hrefs if h.endswith("api.html#sample.Match")]
    fn_hrefs = [h for h in hrefs if h.endswith("api.html#sample.match")]

    assert cls_hrefs, f"class ref href not found in {hrefs}"
    assert fn_hrefs, f"func ref href not found in {hrefs}"

    cls, fn = cls_hrefs[0], fn_hrefs[0]
    assert "api.html#sample.Match" in cls, cls
    assert "api.html#sample.match" in fn, fn
    assert cls != fn, (cls, fn)
    # base http://example.test/sample + inventory uri => full href
    assert cls.startswith("http://example.test/sample"), cls
    assert fn.startswith("http://example.test/sample"), fn
