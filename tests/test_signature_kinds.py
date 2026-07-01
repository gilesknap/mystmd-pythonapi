"""Rendered signatures must preserve Python parameter kinds.

signatureString() dropped `param.kind`, so `*args`/`**kwargs` and the
positional-only `/` and keyword-only `*` markers were lost. This reads the real
griffe ApiIndex for fixtures/sigs (via the built plugin's getIndex) and renders
each function's signature through the built plugin's signatureString, asserting
every marker survives. (The {apidoc} body renders into `div` anchors that md/xml
export can't serialize, so we exercise the render function directly.)
"""
import json
import subprocess

from harness import NODE, REPO

DIST = str(REPO / "dist" / "index.mjs")
FIXTURES = str(REPO / "fixtures")
VENV_PY = str(REPO / ".venv" / "bin" / "python")


def _rendered_signatures():
    probe = (
        f"process.env.MYST_PYAPI_EXTRACTOR='griffe';"
        f"process.env.MYST_PYAPI_ROOTS={json.dumps(FIXTURES)};"
        f"process.env.MYST_PYAPI_PACKAGE='sigs';"
        f"process.env.MYST_PYAPI_PYTHON={json.dumps(VENV_PY)};"
        f"const m=await import({json.dumps(DIST)});"
        f"const idx=m.getIndex();const out={{}};"
        f"for(const[k,v]of Object.entries(idx.items))out[k]=m.signatureString(v);"
        f"process.stdout.write(JSON.stringify(out));"
    )
    proc = subprocess.run(
        [NODE, "--input-type=module", "-e", probe],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_signature_param_kinds_rendered():
    sigs = _rendered_signatures()
    # *args, **kwargs, and the *args-introduced keyword-only group
    assert sigs["sigs.mix"] == "mix(pos, /, both, *args, kw, **extra)", sigs["sigs.mix"]
    # keyword-only via a bare `*` separator
    assert sigs["sigs.kwonly"] == "kwonly(a, *, b, c)", sigs["sigs.kwonly"]
    # positional-only via `/`
    assert sigs["sigs.posonly"] == "posonly(a, b, /, c)", sigs["sigs.posonly"]
