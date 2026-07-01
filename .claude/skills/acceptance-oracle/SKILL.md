---
name: acceptance-oracle
description: How to run and extend this repo's acceptance test suite. Use when adding or modifying tests, verifying a change end-to-end, or when ./run_all.sh fails. Covers the oracle contract, the offline test harness (serve a local inventory + the myst build --all export oracle), and how to add a new acceptance test.
---

# Acceptance oracle

`./run_all.sh` is the single source of truth (SPEC §9). Its exit code decides
pass/fail; there is no other reviewer.

```bash
./run_all.sh        # build plugin (dist/*.mjs) + generate build/objects.inv + pytest tests/
./run_all.sh -x     # stop at the first failing test
```

It runs T1–T8 plus an extractor-swap test and a watch smoke test. Keep it green.

## The tests (SPEC §9)

| Test file | Proves |
|---|---|
| `test_objects_inv.py` (T1) | valid v2 inventory, distinct `sample.match`/`sample.Match` rows |
| `test_sphinx_consumer.py` (T2) | Sphinx consumes it case-sensitively under `-n -W` |
| `test_myst_consumer.py` (T3) | mystmd consumes our inventory case-sensitively |
| `test_myst_producer.py` (T4) | producer resolves intra-project refs distinctly (inventory + `{py}` role) |
| `test_north_star_re.py` (T5) | vendored CPython inv: `re.match` ≠ `re.Match` in mystmd |
| `test_docstring_styles.py` (T6) | numpy/google/sphinx → equivalent section model |
| `test_structure.py` (T7) | re-import canonicalization, nested pkg, static + dynamic `__all__` |
| `test_case_clash.py` (T8) | the headline case-clash scenario, end to end |
| `test_watch.py` | warm sidecar re-resolves after an edit without a cold restart |

## The offline harness (`tests/harness.py`)

mystmd `references:` needs http, and site builds fetch a template — so tests use
an **export oracle** with no template and a **localhost-served** inventory:

- `serve_inventory(inv_path)` — context manager; serves `objects.inv` on an
  ephemeral localhost port, yields the base url. **Keep the myst build inside the
  `with` block.**
- `write_project(dir, myst_yml, {file: content})` — scaffold a myst project.
- `myst_build_all(dir)` — runs `myst build --all` (exports only, offline; clears
  `_build`/`out.*` first).
- `md_links(dir)` → `{link_text: resolved_url}` (from `out.md`);
  `xml_hrefs(dir)` → `[href, …]` (from `out.xml`).

A RESOLVED `xref` shows its resolved url in `out.md`/`out.xml`; an UNRESOLVED one
keeps the literal `xref:…` string AND warns on stderr (`not resolve`/`not found`).

## Adding a test

Model it on `tests/test_north_star_re.py`. Assert the two case-variant refs
resolve to **distinct** urls and that the valid pair produces no
`not resolve`/`not found` warning. Run just yours while iterating:

```bash
.venv/bin/python -m pytest -q tests/test_yourthing.py
```

`tests/conftest.py` has an autouse fixture that builds the plugin + inventory
only if missing (so concurrent runs don't race `tsup --clean`); `run_all.sh`
does the authoritative clean rebuild.
