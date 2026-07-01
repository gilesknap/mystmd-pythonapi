# myst-pyapi

Case-sensitive, intersphinx-compatible **Python API cross-references** for
[`mystmd`](https://mystmd.org).

The single sentence this project demonstrates:

> **You can link to both `re.match` and `re.Match`, distinctly, from mystmd and
> from Sphinx, against an `objects.inv` this tool produced.**

That is harder than it sounds: mystmd's local-label namespace lowercases
identifiers (so `re.Match` and `re.match` collide), and even its intersphinx
path silently lowercases the Sphinx `$`-anchor shorthand. See
[`FINDINGS.md`](./FINDINGS.md) for the full investigation and
[`ISSUE.md`](./ISSUE.md) for the upstream issues this uncovered.

## How it works (the design)

API objects are addressed through a **case-sensitive, explicit-anchor path**,
never mystmd's lowercased local labels:

- **Producer inventory (Option D).** The plugin emits a standard Sphinx v2
  `objects.inv` from the extractor model, using **explicit exact-case anchors**
  and correct `py:*` domain roles. It is written *during the build* by a
  transform (no separate manual step). This inventory is consumed
  case-sensitively by **both** Sphinx (natively) and mystmd (via `references:`).
- **Intra-project refs (Option B).** A `{py}` role resolves an exact-case dotted
  name against the in-memory object model and emits a link whose URL mystmd
  leaves case-intact. Each object is rendered inside a `div` whose `html_id` is
  the exact-case anchor — the one node form that survives mystmd's normalization.

The **extractor** (what reads Python and produces the object model) is a
pluggable component behind a stable interface (`src/ir.ts` `Extractor`), so the
extractor choice can change without touching the linking/rendering layer.

## Layout

```
src/
  ir.ts                 # the IR: ApiItem / ApiIndex / Extractor (SPEC §8)
  extractor/stub.ts     # hardcoded 'sample' model (test double / M1 proof)
  extractor/griffe.ts   # real extractor: spawns python/extract.py (griffe)
  render/renderApi.ts   # ApiIndex -> MyST AST (div-anchored objects)
  inventory/objectsInv.ts  # pure-JS Sphinx v2 objects.inv writer (explicit anchors)
  cli.ts                # generate build/objects.inv from an extractor
  index.ts              # the mystmd plugin: {apidoc} directive, {py} role, inventory transform
python/extract.py       # griffe-based extractor CLI (structure + signatures + docstrings)
fixtures/               # sample package (case clash), styles, __all__ variants, vendored inv
tests/                  # the acceptance oracle (T1–T8) + harness
run_all.sh              # runs the whole oracle; exit code is truth
```

## Setup

The toolchain (Node ≥18 + mystmd, and a Python venv with griffe/sphinx/sphobjinv)
is bootstrapped as described in the project notes. Once present:

```bash
npm install          # mystmd + build tooling
npm run build        # compile the plugin to dist/*.mjs  (mystmd requires .mjs)
```

## Use the plugin against a package

In your MyST project's `myst.yml`:

```yaml
version: 1
project:
  plugins:
    - /path/to/myst-pyapi/dist/index.mjs
```

Then in a page:

````markdown
:::{apidoc} yourpackage
:::

See {py}`yourpackage.SomeClass` and {py}`yourpackage.some_func`.
````

- `{apidoc} <package>` renders the API and (via a build transform) writes
  **`build/objects.inv`** — a valid Sphinx inventory with case-sensitive `py:*`
  entries, ready to publish for cross-project linking.
- `{py}`` `dotted.Name` `` `` inserts a case-sensitive cross-reference.

### Selecting the extractor

The extractor is chosen with environment variables (default is the `stub`):

| Variable | Meaning | Default |
|---|---|---|
| `MYST_PYAPI_EXTRACTOR` | `stub` \| `griffe` | `stub` |
| `MYST_PYAPI_ROOTS` | search paths (griffe) | `fixtures` |
| `MYST_PYAPI_PACKAGE` | package to analyze | `sample` |
| `MYST_PYAPI_PYTHON` | python interpreter for griffe | `./.venv/bin/python` |
| `MYST_PYAPI_INV` | output path for the inventory | `build/objects.inv` |

Generate an inventory directly (without a full site build):

```bash
# stub model:
node dist/cli.mjs
# real griffe extraction of fixtures/sample:
MYST_PYAPI_EXTRACTOR=griffe MYST_PYAPI_ROOTS=fixtures MYST_PYAPI_PACKAGE=sample node dist/cli.mjs
```

The inventory lands at **`build/objects.inv`**.

### Consuming the inventory

- **From Sphinx:** `intersphinx_mapping = {'yourpkg': ('https://your.site', '/path/to/objects.inv')}`.
- **From mystmd:** register it under `references:` (mystmd requires an `http(s)`
  URL — serve the file, e.g. a static host) and link with
  `xref:yourpkg#yourpackage.SomeClass`.

## Run the acceptance oracle

```bash
./run_all.sh        # build + generate inventory + run tests T1–T8
./run_all.sh -x     # stop at first failure
```

The exit code is the only measure of success.

## References

- [`SPEC.md`](./SPEC.md) — the full specification and milestones.
- [`FINDINGS.md`](./FINDINGS.md) — empirical platform facts and the design decision.
- [`ISSUE.md`](./ISSUE.md) — drafted upstream mystmd issue (with repros).
