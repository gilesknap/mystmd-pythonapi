# Project state (continuity doc)

## ✅ COMPLETE — all milestones M0–M6 done. `./run_all.sh` → 18 passed.
Committed on branch `feat/case-sensitive-api-xrefs`, pushed, PR #1 opened:
https://github.com/gilesknap/mystmd-pythonapi/pull/1
Deliverables: FINDINGS.md, ISSUE.md, README.md, green run_all.sh, swappable stub+griffe extractor, warm sidecar + watch test.


Working notes so any agent can resume after a context clear. The authoritative
spec is `SPEC.md`; the oracle is `./run_all.sh` (not yet written).

## Toolchain (DONE — see memory `toolchain-bootstrap`)
- npm 10.9.2 on PATH via `/root/.local/bin/npm`; myst v1.10.1 at `./node_modules/.bin/myst`.
- Python 3.12 venv at `.venv` with griffe 2.1.0, sphinx 9.1.0, sphobjinv 2.4, numpydoc 1.10.0, pytest.
- Build the plugin with `npm run build` (tsup → `dist/index.js`).

## Milestones (SPEC §11)
- [x] M0 scaffold & env — toolchain up; `fixtures/inv/python.objects.inv` vendored; Q1–Q3 IN PROGRESS.
- [ ] M1 PROVE LINKING (extractor stubbed) — T1,T2,T3,T5,T8 green; T4 via §6 tree. **The point of the project.**
- [ ] M2 pluggable extractor (griffe).
- [ ] M3 docstring styles (T6).
- [ ] M4 structure (T7).
- [ ] M5 warm service + watch.
- [ ] M6 write-up (FINDINGS.md, ISSUE.md).

## Key files
- `fixtures/inv/python.objects.inv` — trimmed CPython inv (re.match, re.Match, re.compile, re.Match.group, re.Pattern) with real uris. Built by `scripts/make_python_inv.py`.
- `scripts/repro_case_sensitivity.py` — the `$`-anchor bug reproducer. (`experiments/` = gitignored scratch probes.)

## §6 RESOLVED — design locked (see FINDINGS.md)
- **The `$`-anchor bug:** myst lowercases the Sphinx `$` uri-shorthand on expansion, collapsing `re.Match`→`re.match`. FIX = always emit EXPLICIT exact-case anchors. Proven in `scripts/repro_case_sensitivity.py`.
- Q1: myst emits objects.inv but only std:doc/std:label, lowercased — useless for py:* objects.
- Q2: `references:` only accepts **http(s)** URLs (relative/absolute/file:// all fail). Local inv must be **served over localhost http** for myst to consume it.
- Q3: no plugin hook to write myst's inventory; a **role** CAN emit a verbatim-case link (Option B viable); transforms cannot (Option C dead).
- **Winning mechanism = D + B:** D = generate objects.inv (explicit anchors, py: roles) from the extractor, consumed cross-tool (Sphinx native; myst via served http). B = a plugin role resolves exact-case names against the module-scope ApiIndex → verbatim-case link for intra-project refs (T4).
- Test oracle: `_build/site/content/<page>.json` link nodes (url keyed by urlSource); or out.md/out.xml hrefs; unresolved refs warn on stderr.

## DONE so far
- T1 GREEN (objects.inv writer + stub, sphobjinv-validated). Writer + vendored CPython inv use explicit anchors.
- T5 GREEN (north-star: served CPython inv, re.match vs re.Match distinct in myst).
- Fixtures created + verified (sample case-clash, styles, all_static/all_dynamic).
- PLUGIN BUILT & PROVEN (dist/index.mjs): `{apidoc}` directive renders 7 objects each in a `div` with an EXACT-CASE `html_id` anchor (survives); `{py}` role emits case-preserved non-fragment links; a project-stage transform emits build/objects.inv during the build (R1). Extractor registry in place (stub only for M1).
- Anchor survival solved: `div html_id` survives exact-case (headings/mystTarget/paragraph do NOT). Role must emit NON-fragment url (bare `#frag` gets lowercased). See FINDINGS.md / memory myst-inventory-namespace.
- Test harness tests/harness.py (serve_inventory, myst_build_all, md_links, xml_hrefs, write_project) + conftest.py (conditional build). run_all.sh written (oracle).
- Key gotcha: myst plugins MUST be `.mjs` (tsup outExtension). Offline oracle = `myst build --all` md+xml exports (no site template).

## M0–M4 COMPLETE ✅  `./run_all.sh` → 16 passed (T1–T8 + extractor-swap).
- M2: griffe extractor (python/extract.py + src/extractor/griffe.ts), swappable via MYST_PYAPI_EXTRACTOR; stub is the default double.
- M3: T6 green — docstringSections normalize identically across numpy/google/sphinx.
- M4: T7 green — re-import canonicalization (public path), nested subpkg, static + dynamic __all__.
- Deliverables written: FINDINGS.md (+result section), ISSUE.md, README.md.
- Deviations documented: griffe emits sample.subpkg.Widget.render (8 items) vs stub's 7 — stub inventory (7 rows) is the restored default artifact so T1 count holds.
- M5 IN FLIGHT: warm Python sidecar (python/sidecar.py) + src/extractor/warm.ts + tests/test_watch.py (re-resolve after edit without cold restart). Additive; keep suite green.
- NOTE: nothing committed to git yet (all untracked) — commit only if the user asks.

## (history) M1 COMPLETE ✅  `./run_all.sh` → 9 passed (T1×4, T2, T3, T4, T5, T8).
- T2 sphinx consumer, T3 myst consumer, T4 producer (inventory + {py} role), T8 headline — all green.
- Known cosmetic quirk: `{apidoc}` div anchors emit `Unsupported node type: div` warnings from md/xml EXPORTERS (fine in HTML/site-JSON; resolution unaffected). Tests scope warning checks accordingly.
- ISSUE.md written (4 bugs + repros). FINDINGS.md written.

## Next action — M2 (griffe extractor)
Build python/extract.py (griffe → ApiIndex JSON incl. docstring sections + structure) + src/extractor/griffe.ts, wire into EXTRACTORS registry (select via MYST_PYAPI_EXTRACTOR=griffe; python via MYST_PYAPI_PYTHON). Keep stub as default double so T1-T8 stay green. Then M3 (T6 docstrings), M4 (T7 structure), M5 (warm sidecar+watch), README.md.
