# Drafted mystmd issue

> Draft for filing against [jupyter-book/mystmd](https://github.com/jupyter-book/mystmd).
> Written from empirical work in this repo (mystmd **v1.10.1**). Repros are self-contained.

---

## Title

Case-sensitive, typed cross-references for API docs: `$`-anchor lowercasing, http-only `references:`, and no plugin inventory-write API

## Summary

MyST resolves cross-references through **two independent namespaces**:

1. **Local labels** — headings, `(target)=`, `mystTarget`. Identifiers are **normalized (lowercased/slugified)** and matched case-insensitively. Great for forgiving prose anchors.
2. **Inventory (intersphinx)** — external `objects.inv` registered under `references:`, referenced with `xref:<proj>#<name>`. Keys are stored and looked up **case-sensitively** (verified: `Inventory.getEntry` is exact).

For **Python API documentation** this distinction is load-bearing: `re.match` (a function) and `re.Match` (a class) are *different objects* and must be *different link targets*. The inventory namespace is the right home for them — and mostly works — **except for four issues** that make case-sensitive, typed API cross-references impractical today. Each is small and independently fixable.

I built a plugin that works around all four (explicit anchors + a custom role); this issue proposes fixing them upstream so plugins don't have to.

---

## Issue 1 (primary bug): the Sphinx `$` anchor shorthand is expanded **lowercased**

A Sphinx v2 inventory may abbreviate a uri whose fragment equals the object name using `$`:

```
re.Match py:class 1 library/re.html#$ -
re.match py:function 1 library/re.html#$ -
```

Sphinx and `sphobjinv` expand `$` **case-preserved** (`…/re.html#re.Match` vs `…/re.html#re.match`). MyST expands it with `.toLowerCase()` (in the intersphinx `Inventory.setEntry`), so **both rows resolve to the same URL** `…/re.html#re.match`. The class silently collapses onto the function.

**Impact:** consuming the *real* `https://docs.python.org/3` inventory (which uses `$` throughout) mis-links every case-distinct name pair. This is not hypothetical — it affects any project that `xref`s CPython.

### Minimal repro

```bash
# build two inventories from the same rows: one with `$`, one with explicit anchors
python - <<'PY'
import sphobjinv as soi
for kind in ("dollar","explicit"):
    inv = soi.Inventory(); inv.project="P"; inv.version="1"
    for name,role,frag in [("re.match","function","re.match"),("re.Match","class","re.Match")]:
        uri = "re.html#$" if kind=="dollar" else f"re.html#{frag}"
        inv.objects.append(soi.DataObjStr(name=name,domain="py",role=role,priority="1",uri=uri,dispname="-"))
    soi.writebytes(f"{kind}/objects.inv", soi.compress(inv.data_file()))
PY
# serve each and xref:proj#re.match / xref:proj#re.Match from a MyST page.
# EXPECTED: two distinct urls.  ACTUAL (v1.10.1): the `$` inventory collapses both to #re.match.
```

**Fix:** expand `$` using the entry name **verbatim** (Sphinx semantics), not lowercased.

---

## Issue 2: `references:` only accepts `http(s)` — no local file or `file://`

`references:` entries are validated as URLs and loaded by fetching `<url>/objects.inv`. A **bare relative path**, a **bare absolute path**, and a **`file://` URL** all fail:

- relative/absolute path → `'url' must be valid URL` at config validation.
- `file://…/objects.inv` → passes URL validation but `Inventory.load()` calls `fs.readFileSync` on the raw `file://` string → `ENOENT`.

**Impact:** to consume a *locally generated* inventory (e.g. a project's own API inventory, or a vendored offline fixture) you must stand up an HTTP server. This is painful for local builds, `myst start`, CI, and offline docs.

**Fix:** accept a filesystem path / `file://` URL for a `references:` entry (read it from disk), with an optional separate base-url for resolved links.

---

## Issue 3: no plugin API to register case-sensitive **typed** inventory entries

`MystPlugin` exposes only `directives`, `roles`, `transforms`. There is no hook to add entries to the intersphinx/reference registry (it lives on the session cache, fed solely from `myst.yml` `references:`). A project-stage transform receives only `(mdast, vfile)` + `{select, selectAll}`, and runs **after** `resolveReferences`/`SphinxTransformer`, so it cannot participate in resolution.

A role **can** emit a fully-resolved `link` node with a verbatim-case url (link urls aren't normalized), which is enough to *author* case-sensitive links — but it feeds no inventory and appears in no exported inventory.

**Impact:** an API-docs plugin cannot register `py:function`/`py:class`/`py:method` objects so that (a) intra-project `xref` resolves them case-sensitively and (b) they appear in the site's exported inventory. It must generate an `objects.inv` out of band and serve it (see Issues 1–2).

**Proposal:** a plugin hook to contribute typed, case-sensitive inventory entries, e.g.

```ts
interface MystPlugin {
  // …
  inventory?: (utils) => InventoryEntry[]; // { name, domain, role, uri, dispname }
}
```

that are merged into the resolution registry **and** the site's exported inventory, verbatim.

---

## Issue 4: MyST's own exported `objects.inv` is `std`-only and lowercased

`writeObjectsInv` emits only `std:doc` and `std:label` rows, drawn from `state.targets` whose identifiers have already passed through `normalizeLabel` (lowercased). So a MyST site cannot publish `py:*` (or any domain-typed) objects, and even its `std` labels lose case.

**Impact:** downstream Sphinx/MyST projects can't intersphinx-link a MyST site's API objects case-sensitively, because the objects never make it into the published inventory with their domain/role/case.

**Fix:** let domains other than `std` contribute rows, and preserve the authored case for inventory keys/uris.

---

## Appendix: the local-label case-folding repro (why the inventory path is required)

`mystTarget`/`(label)=`/heading identifiers are lowercased, so the local-label namespace *cannot* hold `re.Match` vs `re.match`:

```markdown
(sample.Match)=
class Match …

(sample.match)=
def match …
```
Building this warns **`Duplicate identifier in file "sample.match"`** — both targets normalize to `sample.match` and collide. (A plugin-emitted `div` with an explicit `html_id` is currently the *only* node form that preserves an exact-case anchor.) This is by design for prose, and is exactly why API objects belong in the case-sensitive inventory namespace — which brings us back to Issues 1–4.

---

## Why this matters together

Fixing **Issue 1** alone makes real-world CPython xrefs correct. Fixing **1 + 2** makes a locally generated API inventory usable without a server. Fixing **3 (+ 4)** lets an API-docs plugin be a first-class citizen: register typed, case-sensitive objects that resolve intra-project and publish in the site inventory for cross-project linking — the missing piece for a Sphinx-parity Python API domain in MyST.
