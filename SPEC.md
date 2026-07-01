# Spec: Case-sensitive, intersphinx-compatible API cross-references for `mystmd`

**Audience: an autonomous coding agent (Claude Code).** Build the repo described here, then run the acceptance oracle in a loop, fixing failures until it is green. Do not wait for human input. When a design fork appears, follow the decision tree in §6 and keep the first option that makes the oracle green. Record every empirical result in `FINDINGS.md` as you go.

---

## 0. Agent operating instructions (the loop)

1. Build the milestones in order (§10). Each milestone has machine-checkable acceptance tests.
2. After any change, run `./run_all.sh`. It runs every test and exits non-zero on any failure. This is the **only** oracle; there is no human reviewer.
3. On failure: read the failing test's output, form a hypothesis, change one thing, re-run. Repeat.
4. On a design fork (esp. §6): try options **in the given order**; keep the first that turns the relevant test green; write down in `FINDINGS.md` what worked and what didn't (with the exact error).
5. "Done" = all acceptance tests in §9 pass **and** `FINDINGS.md` documents which §6 mechanism won and why, **and** `ISSUE.md` (a drafted mystmd issue) exists per §11-M6.
6. Never delete a failing test to make the suite pass. If a test encodes a requirement MyST genuinely cannot meet, mark it `xfail` with a one-line reason and record the limitation in `FINDINGS.md`; do not silently drop it.

---

## 1. Goal

A single `mystmd` plugin that renders Python API documentation and — critically — produces **case-sensitive, intersphinx-compatible cross-reference targets**, emitted as a standard `objects.inv` that is consumable **from both mystmd and Sphinx**. The extractor (what reads Python and produces the object model) is a **pluggable** component and is explicitly *lower priority* than the linking layer for this phase.

**North-star proof:** a consumer must be able to link to **both `re.match` (a function) and `re.Match` (a class)** as distinct targets, in both mystmd and Sphinx, and our own generated inventory must round-trip the same distinction for a local fixture package.

---

## 2. Requirements (hard constraints)

R1. **One plugin, no separate pre-process build step**, and it must work under `myst start` (watch mode).
R2. **Amortized cost:** analysis must never be paid per-directive, and ideally not fully re-paid per build. A prepared Python venv is acceptable; nothing may be *imported/executed* per directive. (A warm sidecar or module-scope memoization is the intended mechanism — see §7.)
R3. **Case-sensitive object identity.** `re.match` ≠ `re.Match`. This is non-negotiable and is the reason the project exists.
R4. **Emit a valid `objects.inv`** (Sphinx inventory v2) with correct `py:` domain roles, consumable by both mystmd (`references:`) and Sphinx (`intersphinx_mapping`).
R5. **Pluggable extractor** behind a stable interface, so the extractor choice (griffe / numpydoc-runtime / tree-sitter / pyright / scip) can be swapped later without touching the linking/rendering layer.
R6. **Docstring styles:** numpy, google, and sphinx(reST field-list) must all be supported. Docstring *bodies* may be authored in MyST and should be passed through the MyST parser; only the section splitting is style-specific.
R7. **Package-structure robustness:** handle `__init__` re-imports (flat public API), nested namespaces, and `__all__` that is either a static literal or dynamically generated.

---

## 3. Key discovery — MyST's two reference namespaces (the conceptual core)

MyST resolves cross-references through **two independent systems**:

- **Local-label namespace.** Populated by headings, `(target)=`, and `mystTarget` nodes. MyST **normalizes (lowercases/slugifies)** these identifiers and matches references case-**insensitively**. This is by design (forgiving anchors).
- **Inventory namespace (intersphinx).** Populated by external `objects.inv` files registered under `references:` in `myst.yml`, referenced via `xref:<project>#<name>` (or Sphinx-side `inv:`). Matched **verbatim and case-sensitively**, because Sphinx inventory keys are case-sensitive (`re.match` and `re.Match` are separate rows).

**Consequence (the whole design pivots on this):** Python API objects must live in the **inventory namespace**, not the local-label namespace. Do **not** try to represent `re.Match` as a `mystTarget`/heading label — it will be folded to `re.match` and collide. Instead, the tool must (a) generate an `objects.inv` containing exact-case typed entries, and (b) make both intra-project and cross-project references resolve through that inventory.

---

## 4. Prior art (what stefanv's `myst-apidoc` does, and where it stops)

Pipeline: `fleece` (a Python script that **imports** the target package at runtime and runs `numpydoc` over **functions and submodules only** — no classes) → JSON → a JS `{apidoc}` directive that renders JSON to MyST AST.

Cross-referencing in that plugin is **only**: `mystTarget` nodes labeled with the dotted name + plain internal `{type:'link', url:'#'+label}` links. There is **no** intersphinx, **no** `objects.inv`, **no** case handling, and `transforms: []` is empty. It works for scikit-image solely because skimage's public API (functions only, via `fleece`) is all-lowercase snake_case, so MyST's label-lowercasing never collides. It does **not** solve case-sensitive or cross-project linking. Its renderer (definition lists for params, section layout) is a fine base to reuse; its linking layer is not sufficient.

Repo to read for the renderer: `https://github.com/stefanv/myst-apidoc` (`myst-apidoc-plugin/src/apiDirective.ts`).

---

## 5. Empirical findings from this session (trust these; do not re-derive)

Verified against **mystmd v1.10.1** (installed via `npm install mystmd`):

- F1. A plugin-emitted `heading` with an explicit `identifier` has that identifier **discarded**; MyST reassigns an auto id (`sec-N`). Do not use headings to carry object identifiers.
- F2. `mystTarget` is the correct local-target primitive, but its `label` is **lowercased**. Proven: a `mystTarget` labeled `asyncio.Task` resolves from **both** `[](#asyncio.Task)` and `[](#asyncio.task)` — they collide onto one lowercased target. Same holds for native `(asyncio.Task)=`, which stored `id="asyncio.task"`.
- F3. Therefore the local-label path **cannot** distinguish `re.Match` from `re.match`. (This is the reason for §3's pivot.)
- F4. `myst build --html` fetches a **site template from `api.mystmd.org`**, which is **blocked/403 in restricted networks**. Use `myst build --all` with an `xml` (JATS) or `md` export to get the fully-resolved AST **without** a template. Prefer inspecting that exported AST in tests. (`format: xml` → JATS with `<xref rid=...>` showing resolution; unresolved refs emit `Cross reference target was not found` warnings on stderr.)
- F5. Consumer-side intersphinx in mystmd is configured via `references:` in `myst.yml` (e.g. `references: {python: https://docs.python.org/3}`) and referenced with `xref:python#<name>`; this path is case-sensitive (it matches inventory keys verbatim).
- F6. `git clone` works; unauthenticated GitHub **API** is rate-limited — avoid it.

---

## 6. The central investigation — getting objects into the inventory namespace (decision tree)

The producer side (making *our* objects case-sensitively referenceable, both intra-project and via exported `objects.inv`) is the unsolved part. Try these mechanisms **in order**; keep the first that passes `test_myst_producer` and `test_cross_tool` (§9). Document each attempt in `FINDINGS.md`.

**First, verify the platform facts (write results to `FINDINGS.md`):**
- Q1. Does `mystmd` itself emit an `objects.inv` for a built site (in addition to `myst.xref.json`)? Search the built `_build` output and mystmd docs/source. If yes, note where and whether entries preserve case + carry a domain/type.
- Q2. Does `references:` in `myst.yml` accept a **local file path** to an `objects.inv` (not just a URL)? Test both a bare path and a `file://` URL and a locally-served `http://` URL.
- Q3. Can a plugin **`transform`** mutate the project reference/inventory state before resolution? Inspect `myst-common` / `myst-transforms` types for a reference-registration hook.

**Option A — Self-inventory (preferred if viable).** The tool writes `objects.inv` early (it knows every object at extraction time, before rendering), and the project registers **its own** inventory under `references:` (e.g. key `self`). API cross-references are then authored/emitted as `xref:self#re.Match`, which uses the **case-sensitive inventory resolver** instead of the local-label resolver. Verify ordering works under a single `myst build` and under `myst start`.

**Option B — Custom role + tool-owned resolution.** Provide a `{py}`/`{py:obj}` role (and optionally a `py:` link scheme) whose `run` looks the exact-case name up in the extractor's in-memory object table (module-scope) and emits a fully-resolved `link` node with the correct URL. MyST never resolves it, so never folds it. Requires that the rendered object's HTML anchor is the exact-case name — test whether a plugin-set `html_id` on a **non-heading** container (e.g. a `div`/`span`) survives (F1 only disproved it for headings).

**Option C — Transform injects inventory entries.** A `transform` (empty in stefanv's plugin) registers case-sensitive typed entries into MyST's reference state after directives run, so both resolution and any `objects.inv`/`myst.xref.json` export include them verbatim. Depends on Q3.

**Option D — Post-build inventory + inventory-only references (robust fallback).** If MyST fundamentally will not hold case-sensitive local targets, then: (i) the tool emits `objects.inv` at build completion directly from the extractor model (independent of MyST's label graph), and (ii) **all** API references — intra and inter — go through the inventory path (`xref:`/role), and bare `[](#Object)` is simply never used for API objects. Treat this as the likely answer; A/B/C are attempts to make the ergonomics nicer. Even under D, the `objects.inv` must be produced without a separate manual step (emit it from a transform or a build hook so R1 holds).

**Whichever wins, the invariant is:** API objects are addressed through a case-sensitive inventory, never through MyST's lowercased local labels.

---

## 7. Architecture (decided)

- In-process **JS/TS mystmd plugin** (ESM), directives + roles + (probably) one transform. Not an executable plugin (those spawn per-directive).
- **Pluggable extractor behind an interface** (§8). The plugin talks to the extractor via a **warm service**: either (a) module-scope memoization if the extractor is JS, or (b) a **persistent Python subprocess** spawned once at module scope, held for the process lifetime, addressed over newline-delimited JSON-RPC on stdio, invalidated per-file on change. This satisfies R1/R2 and works under `myst start`.
- The plugin's **linking/rendering layer is independent of the extractor** and is where all the §6 work lives.
- **For Milestone 1, stub the extractor** (hardcode the object model) so the linking proof is not blocked on extraction. Plug a real extractor in at M2.

---

## 8. The IR / extractor interface

The extractor returns an `ApiIndex`. The linking layer consumes only this.

```ts
type ItemKind = "module" | "class" | "exception" | "function"
              | "method" | "property" | "attribute" | "data";

// maps 1:1 to Sphinx py-domain roles for objects.inv:
//   module->py:module class->py:class exception->py:exception
//   function->py:function method->py:method property->py:property
//   attribute->py:attribute data->py:data

interface ApiItem {
  fullName: string;          // EXACT CASE, dotted, canonical: "re.Match", "re.match", "re.Match.group"
  name: string;              // "Match"
  kind: ItemKind;
  docstring: string | null;  // raw; body is MyST
  docstringStyle?: "numpy" | "google" | "sphinx";
  signature?: { params: { name:string; kind:string; annotation:string|null; default:string|null }[];
                returnAnnotation: string | null };
  bases?: string[];
  annotation?: string | null;
  value?: string | null;
  modifiers?: string[];
  children?: string[];       // fullNames of direct children
  anchor: string;            // exact-case anchor used in the built page + objects.inv uri fragment
}
interface ApiIndex { items: Record<string, ApiItem>; roots: string[]; }

interface Extractor {
  name: string;                                   // "stub" | "griffe" | "numpydoc" | "tree-sitter" ...
  analyze(packageRoots: string[]): Promise<ApiIndex>;
  // optional incremental hook for watch mode:
  invalidate?(changedFile: string): void;
}
```

`objects.inv` row per item: `{fullName} py:{role} 1 {pageUri}#{anchor} {name}` (or `#$` shorthand when anchor == fullName; `$` expands to the name at read time).

---

## 9. Acceptance tests (the oracle — must all pass)

Create these; `run_all.sh` runs them all. Use `sphobjinv` (pip) for inventory generation/validation, `sphinx` (pip) for the Sphinx consumer, and mystmd (npm) for the MyST side. **Keep tests hermetic/offline** by vendoring inventories (see T5).

- **T1 `test_objects_inv`** (python + sphobjinv): the tool's generated `build/objects.inv` is a valid v2 inventory and contains **distinct** rows `sample.match py:function` and `sample.Match py:class` with **distinct uris**; likewise `sample.Match.group py:method`. Assert `inv.objects` count and that `Match`/`match` differ in role and uri.
- **T2 `test_sphinx_consumer`**: a tiny Sphinx project with `intersphinx_mapping = {'sample': ('http://example.test/sample', ABS_PATH_TO_build/objects.inv)}`, `nitpicky = True`, a page containing `` :py:class:`sample.Match` `` and `` :py:func:`sample.match` ``. Build with `sphinx-build -n -W -b html …`. **Must succeed** (warnings-as-errors) and the two refs must resolve to **different** URLs. This proves Sphinx can consume our inventory case-sensitively.
- **T3 `test_myst_consumer`**: a MyST project with `references: {sample: <our objects.inv, per §6-Q2>}`, a page with `[](xref:sample#sample.Match)` and `[](xref:sample#sample.match)`. Build via `myst build --all` (xml export, no template — F4). Assert **no `target was not found` warnings** and the two `<xref>` nodes resolve to **distinct** rids/urls. Proves MyST consumes our inventory case-sensitively.
- **T4 `test_myst_producer`**: the MyST project that actually runs `{apidoc} sample` (or `{apidoc} fixtures/sample`) must make `re.Match`-style intra-project references resolve **case-sensitively** — i.e. references to `sample.Match` and `sample.match` land on different objects. Implement via the §6 mechanism that works. Assert distinct resolution in the exported AST.
- **T5 `test_north_star_re`** (offline): vendor `fixtures/inv/python.objects.inv` — a trimmed real CPython inventory containing at least `re.match py:function`, `re.Match py:class`, `re.compile py:function` with their real `library/re.html#…` uris (generate with sphobjinv). Register it as `python` in a MyST project and reference `[](xref:python#re.match)` and `[](xref:python#re.Match)`; assert both resolve to **distinct** CPython URLs. (Consumer-side case-sensitivity, end-to-end, no network.)
- **T6 `test_docstring_styles`**: `fixtures/styles/{numpy_mod,google_mod,sphinx_mod}.py` define the **same** API with numpy/google/sphinx docstrings. Extract all three (via the current extractor; at M1 the stub can assert the parser layer directly) and assert the parsed section model (Summary/Parameters/Returns/Raises) is **equivalent** across styles.
- **T7 `test_structure`**: assert correct public-API enumeration for: (a) `fixtures/sample/__init__.py` that re-imports `Match, match` from a submodule (canonical fullName must be `sample.Match`, not `sample._core.Match`, or both mapped per policy — pick and document); (b) a nested subpackage `sample.subpkg`; (c) `fixtures/all_static/` with a literal `__all__`; (d) `fixtures/all_dynamic/` whose `__all__` is built by a function / `+=`.
- **T8 `test_case_clash`**: the headline. In one build, `sample.Match` (class) and `sample.match` (function) must be simultaneously documented and independently linkable **without collision**, in the MyST producer project, the exported `objects.inv`, and both consumers (folded into T1–T4 assertions but assert it explicitly here as a single scenario).

`run_all.sh` exit code is the loop's truth. Add a `-x` fast-fail mode for iteration.

---

## 10. Fixtures the agent must create

```
fixtures/
  sample/                      # mirrors `re`: has a case clash + re-import + nested pkg + static __all__
    __init__.py                # from ._core import Match, match ; from . import subpkg ; __all__=["Match","match","subpkg"]
    _core.py                   # class Match: (with .group method) ; def match(pattern, string): ...
    subpkg/__init__.py         # nested namespace with its own class/function
  all_static/__init__.py       # __all__ = ["a","B"] literal
  all_dynamic/__init__.py      # __all__ built via a loop/function or += across submodules
  styles/
    numpy_mod.py               # same API, numpy docstrings
    google_mod.py              # same API, google docstrings
    sphinx_mod.py              # same API, reST field-list docstrings
  inv/
    python.objects.inv         # vendored trimmed CPython inv (re.match, re.Match, re.compile)
```

`sample._core` must contain BOTH `class Match` and `def match(...)` so the case clash is real. Give `Match` a method `group` so a `py:method` row exists. Docstrings in `sample` should be authored in **MyST** (to exercise passthrough) while `styles/*` exercise the three source styles.

---

## 11. Milestones

- **M0 — scaffold & env.** Repo layout, `run_all.sh`, `package.json` (mystmd, tsup, myst-common), a Python venv with `pip install --break-system-packages griffe sphinx sphobjinv numpydoc`. Vendor `fixtures/inv/python.objects.inv`. Answer §6 Q1–Q3 into `FINDINGS.md`.
- **M1 — PROVE LINKING (extractor stubbed).** Hardcode the `sample` `ApiIndex`. Generate `objects.inv`. Get **T1, T2, T3, T5, T8** green, and **T4** via the §6 decision tree. This milestone is the point of the project; do it before any real extraction.
- **M2 — pluggable extractor.** Implement the §8 interface; write one real extractor (agent's choice — griffe is the strongest candidate; numpydoc-runtime is the known-working fallback) that reproduces `sample`'s `ApiIndex` from actual fixture source. Swap it behind the interface; T1–T8 stay green. Keep the stub extractor as a test double.
- **M3 — docstring styles.** Make **T6** pass across numpy/google/sphinx.
- **M4 — structure.** Make **T7** pass (re-import canonicalization, nested ns, static + dynamic `__all__`).
- **M5 — warm service + watch.** Implement the warm extractor (module-scope memo or persistent Python subprocess per §7). Add a watch-mode smoke test: edit a fixture `.py`, confirm the plugin re-resolves without a full cold restart.
- **M6 — write up.** `FINDINGS.md` (which §6 mechanism won; every platform fact learned) and `ISSUE.md` (a drafted mystmd issue: the two-namespace problem, the `mystTarget` case-folding repro, and a proposal for a first-class case-sensitive typed object domain / inventory-write API for plugins — with the minimal repro attached).

---

## 12. Environment notes & gotchas

- Node ≥18 (tested on 22). `npm install mystmd` → CLI `npx myst` (tested v1.10.1).
- **Do not** use `myst build --html` in a sandbox (fetches a blocked template, 403). Use `myst build --all` with an `exports: [{format: xml, output: ./out.xml}]` (JATS) or `md` to get resolved AST for assertions.
- Python: `pip install --break-system-packages …`. `sphobjinv` reads/writes/validates `objects.inv` (use it for T1 generation and assertions; it also does inv↔json).
- Sphinx consumer: build with `-n -W` so a missing/case-wrong ref fails the build (that's the signal for T2).
- Keep everything offline: vendor inventories; never depend on `docs.python.org` at test time.
- If a step needs a network host that's blocked, record it in `FINDINGS.md` and vendor a fixture instead; do not stall.

---

## 13. What to hand back

On completion, the repo root must contain: a green `./run_all.sh`, `FINDINGS.md` (platform facts + which §6 mechanism won, with evidence), `ISSUE.md` (the drafted mystmd issue), and a short `README.md` explaining how to run the plugin against a package and where the `objects.inv` lands. The extractor must be swappable (prove it by having both `stub` and one real extractor selectable via config/env). The single sentence that must be demonstrably true at the end: **"You can link to both `re.match` and `re.Match`, distinctly, from mystmd and from Sphinx, against an `objects.inv` this tool produced."**
