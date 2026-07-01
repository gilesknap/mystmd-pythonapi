# FINDINGS

Empirical results and the design decision for case-sensitive, intersphinx-compatible
API cross-references in `mystmd`. Verified against **mystmd v1.10.1**, sphinx 9.1.0,
sphobjinv 2.4, griffe 2.1.0 (see `STATE.md` / memory `toolchain-bootstrap` for the env).

Every claim below was produced by running the real tools; the reproducers live under
`scripts/` (notably `scripts/repro_case_sensitivity.py`).

---

## 0. Headline

**You CAN link to both `re.match` and `re.Match` distinctly from mystmd and from
Sphinx — provided the `objects.inv` uses EXPLICIT, exact-case anchors rather than the
Sphinx `$` shorthand.** The SPEC's premise (§3/F5) that the inventory namespace is
case-sensitive is correct for the *keys*, but mystmd silently **lowercases the `$`
anchor expansion**, which collapses `re.Match` onto `re.match`. That single gotcha is
the crux of the whole project.

---

## 1. The central discovery — the `$`-anchor lowercasing bug (SPEC §6, decisive)

A Sphinx inventory row may store its uri with a `$` shorthand meaning "substitute the
object's name here", e.g. `re.Match py:class 1 library/re.html#$ -`. Real CPy uses this.

- **sphobjinv / Sphinx** expand `$` to the name **case-preserved** → `.../re.html#re.Match`.
- **mystmd v1.10.1** expands `$` with `entry.name.toLowerCase()` (in `Inventory.setEntry`,
  intersphinx pkg) → `.../re.html#re.match`. So `re.match` and `re.Match` **collapse to
  the same URL**, even though both keys are stored and matched case-sensitively.

Reproduced directly (`scripts/repro_case_sensitivity.py`): two inventories built from the
same trimmed CPython data, served over http, consumed by myst:

| inventory form | `xref:python#re.match` resolves to | `xref:python#re.Match` resolves to | distinct? |
|---|---|---|---|
| `#$` shorthand (real CPython form) | `…/re.html#re.match` | `…/re.html#re.match` | **NO** |
| **explicit anchors** | `…/re.html#re.match` | `…/re.html#re.Match` | **YES** |

**Consequence for real-world use:** consuming the *actual* `https://docs.python.org/3`
inventory (which uses `$`) in mystmd will silently mis-link every case-distinct name
(functions vs same-named classes). This is the primary issue to file (see `ISSUE.md`).

**Our fix (load-bearing):** the inventory writer (`src/inventory/objectsInv.ts`) and the
vendored fixture (`scripts/make_python_inv.py`) **always emit explicit exact-case
anchors**, never `#$`. Explicit anchors are preserved verbatim by BOTH mystmd and
Sphinx, so one generated `objects.inv` is consumed case-sensitively by both tools.

---

## 2. Platform facts (SPEC §6 Q1–Q3)

### Q1 — Does mystmd emit its own `objects.inv`?
**Yes, but it is useless for API objects.** myst's `writeObjectsInv` only emits the
`std:doc` and `std:label` domains from `state.targets`, and those identifiers have
already been passed through `normalizeLabel` (lowercased). It can never carry
`py:function`/`py:class`/`py:method` rows, and it loses case. So we must generate our
own inventory from the extractor model, not post-process myst's.
(Evidence: `node_modules/mystmd/dist/myst.cjs` `writeObjectsInv` ~L307987–308014.)

### Q2 — Does `references:` accept a local inventory? (full matrix)
`references:` entries are validated as URLs and loaded by the intersphinx loader. Results:

| form | loads? | notes |
|---|---|---|
| bare relative path `../../x.inv` | **NO** | `'url' must be valid URL` — rejected at config validation |
| bare absolute path `/abs/x.inv` | **NO** | same rejection |
| `file:///abs/x.inv` | **NO** | passes URL validation but `Inventory.load()` does `fs.readFileSync` on the raw `file://` string → ENOENT |
| **`http://host/dir`** (dir served) | **YES** | fetches `<url>/objects.inv`; base url for resolved links = the http url |
| object form `{url, kind: intersphinx}` | **YES** | `url` required + must parse; there is **no separate base-url key** — the one `url` is both locator and link prefix |

**Consequence:** to have mystmd consume a *local* inventory it must be **served over
http** (localhost is fine, fully offline). Tests use a localhost static server. There is
no file-path or file:// route in v1.10.1.

### Q3 — Can a plugin register case-sensitive typed inventory entries?
**No.** The plugin surface (`myst-common` `MystPlugin`) exposes only `directives`,
`roles`, `transforms` — no inventory/reference hook. A project-stage transform receives
only `(mdast, vfile)` + `{select, selectAll}`, runs **after** the built-in
`resolveReferences`/`SphinxTransformer`, and cannot reach the intersphinx registry
(which lives on the session cache, fed solely from `myst.yml` `references:`).
- **Option B is viable:** a **role**'s `run()` returns `GenericNode[]` and may emit a
  `link` node with a verbatim-case `url`; link urls are not passed through
  `normalizeLabel`, so case is preserved.
- **Option C is not viable:** no transform path writes the inventory.
(Evidence: `myst-common/dist/types.d.ts` RoleSpec L94–102, TransformSpec L110–118;
`myst.cjs` plugin pipe L307601/307716, resolution order L307701–307721.)

---

## 3. The §6 decision tree — what won

- **Option A (self-inventory via `references: self`)** — *rejected as the primary
  mechanism.* Would require serving our generated inventory over http during the build
  (Q2), i.e. a separate running server, breaking R1 ("one plugin, works under
  `myst start`"). Usable in tests, not as the product ergonomics.
- **Option B (custom role → resolved link)** — **chosen for intra-project API refs
  (T4).** A role looks the exact-case name up in the module-scope `ApiIndex` and emits a
  verbatim-case `link` node; no inventory, no server, works under `myst start`, satisfies
  R1/R2. (See §4 for the anchor caveat.)
- **Option C (transform injects inventory)** — *rejected*, no API (Q3).
- **Option D (post-build inventory, inventory-only refs)** — **chosen for the exported
  `objects.inv`** consumed cross-tool (Sphinx T2, myst T3/T5). Emitted from the extractor
  model with explicit anchors; written once per build (not per directive) so R1/R2 hold.

**Winning design = D (cross-tool inventory) + B (intra-project role).** The invariant
holds: API objects are addressed through a case-sensitive, explicit-anchor path, never
through myst's lowercased local labels or the `$` shorthand.

---

## 4. Test oracle (how we assert resolved URLs)

JATS `out.xml` ext-link `xlink:href` and the `md` export link target BOTH carry the
resolved absolute URL for a resolved `xref:` (and keep the raw `xref:...` string when
unresolved). The richest oracle is the built site AST
`_build/site/content/<page>.json`: walk for `type == 'link'` nodes and read
`node.url` keyed by `node.urlSource` (the original `xref:...`). Unresolved refs also emit
a stderr warning `"xref:… not found in intersphinx …"`. Tests assert distinctness by
comparing the two resolved urls and asserting no warning for the valid pair.

---

## 5. Limitations to record (→ ISSUE.md)

1. `$`-anchor expansion is lowercased → case-distinct inventory rows collapse (the big one).
2. `references:` cannot point at a local file or `file://` — only http(s); forces serving.
3. No plugin API to register case-sensitive typed (`py:*`) inventory entries.
4. myst's own exported `objects.inv` is `std:doc`/`std:label` only and lowercased.
5. (Known, F2) `mystTarget`/`(label)=` identifiers are lowercased, so the local-label
   path cannot hold `re.Match` vs `re.match` either.

---

## 6. Prior art (stefanv/myst-apidoc renderer — reused)

`apiDirective.ts` is a `DirectiveSpec` `apidoc` that maps a JSON model → mdast: per object
a `mystTarget` + `heading`, then `Parameters`/`Returns`/`Raises` as a `heading` +
`definitionList` (term = name ` : ` emphasis(type), description = `parseMyst(desc).children`),
`Examples` as a python `code` node, docstring bodies spliced via `ctx.parseMyst(...).children`.
No signature rendering, no intersphinx, empty `transforms:[]`. We reuse the renderer
shapes and the `parseMyst` passthrough; we replace the linking layer entirely (§3).

---

---

## 7. Result (what is demonstrably true)

With the design above, the acceptance oracle `./run_all.sh` is green:

- **T1** — the generated `objects.inv` is a valid v2 inventory with distinct
  `sample.match` (py:function) and `sample.Match` (py:class) rows at distinct uris,
  plus `sample.Match.group` (py:method).
- **T2** — a Sphinx project consumes that inventory under `-n` and `-W` (warnings as
  errors) and resolves ``:py:class:`sample.Match``` and ``:py:func:`sample.match```
  to **different** URLs. Sphinx-side case-sensitivity proven.
- **T3 / T5** — mystmd consumes our inventory (T3) and the vendored CPython
  inventory (T5, north-star) and resolves the case-variant names to **distinct**
  URLs. myst-side case-sensitivity proven (explicit anchors).
- **T4** — the producer project that runs `{apidoc} sample` resolves
  `xref:self#sample.Match` vs `xref:self#sample.match` distinctly (served
  self-inventory), and the `{py}` role emits distinct case-preserved links.
- **T8** — the headline: `sample.Match` (class) and `sample.match` (function) are
  simultaneously documented and independently linkable without collision, in the
  producer, the exported inventory, and both consumers.

**Which §6 mechanism won:** **D (build-time explicit-anchor `objects.inv`) for
cross-tool consumption + B (`{py}` role → non-fragment link, `div html_id`
anchors) for intra-project refs.** A was rejected (http-only `references:` breaks
R1's server-less requirement) and C was rejected (no plugin inventory-write API).
The one non-obvious enabler is emitting **explicit exact-case anchors** instead of
the Sphinx `$` shorthand — without it, myst collapses every case-distinct pair.

_Status: M0 + M1 complete (oracle green: T1–T5, T8). M2 (griffe extractor) adds
the real extraction behind the same interface; M3/M4 add T6/T7; M5 the warm
sidecar + watch. FINDINGS updated as each lands._
