// myst-pyapi — case-sensitive, intersphinx-compatible Python API cross-references.
//
// Linking design (see FINDINGS.md): API objects are addressed through a
// case-sensitive, explicit-anchor path, never myst's lowercased local labels.
//   * Producer inventory (Option D): a build-time transform writes objects.inv
//     from the extractor model with EXPLICIT exact-case anchors + py:* roles.
//   * Intra-project refs (Option B): the `{py}` role resolves an exact-case name
//     against the module-scope ApiIndex and emits a NON-fragment link whose url
//     myst leaves case-intact. Objects render inside a `div` whose html_id is the
//     exact-case anchor (the one node form that survives normalization).

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

import type { ApiIndex, ApiItem, Extractor } from "./ir.js";
import { stubExtractor, buildStubIndex } from "./extractor/stub.js";
import { griffeExtractor } from "./extractor/griffe.js";
import { warmGriffeExtractor } from "./extractor/warm.js";
import { renderIndex } from "./render/renderApi.js";
import { renderInventory } from "./inventory/objectsInv.js";

// ---- pluggable extractor (R5) --------------------------------------------
// Extractors register here; selected by MYST_PYAPI_EXTRACTOR (default "stub").
// M1 wires only the (synchronous) stub; M2 adds an async griffe extractor fed
// by a warm Python sidecar and getIndex() becomes an awaited call.
const EXTRACTORS: Record<string, Extractor> = {
  stub: stubExtractor,
  griffe: griffeExtractor,
  "griffe-warm": warmGriffeExtractor,
};

// ---- module-scope memoized analysis (R2: never paid per-directive) --------
let INDEX: ApiIndex | null = null;
function getIndex(): ApiIndex {
  if (!INDEX) INDEX = buildStubIndex();
  return INDEX;
}

// ---- page uri policy ------------------------------------------------------
// The page objects are documented on (matches the inventory's uris). Overridable
// so a project can point refs at wherever it runs {apidoc}.
const API_PAGE = process.env.MYST_PYAPI_PAGE ?? "api.html";
const pageUriFor = (_item: ApiItem): string => API_PAGE;

// ---- directive: {apidoc} --------------------------------------------------
const apidoc = {
  name: "apidoc",
  doc: "Render Python API documentation with case-sensitive anchors.",
  arg: { type: String, doc: "package (import) name" },
  run(_data: any, _vfile: any, ctx: any) {
    const index = getIndex();
    const parse = ctx?.parseMyst ? (s: string) => ctx.parseMyst(s) : undefined;
    return renderIndex(index, { parse, pageUriFor }, 2);
  },
};

// ---- role: {py}`dotted.Name` ---------------------------------------------
const pyRole = {
  name: "py",
  doc: "Case-sensitive cross-reference to a Python API object.",
  body: { type: String },
  run(data: any) {
    const index = getIndex();
    const name = String(data?.body ?? "").trim();
    const item = index.items[name];
    if (!item) {
      return [{ type: "inlineCode", value: name }];
    }
    // NON-fragment url ⇒ myst does not treat it as a local cross-reference and
    // therefore does not lowercase it (proven). Points at the div anchor.
    return [
      {
        type: "link",
        url: `${pageUriFor(item)}#${item.anchor}`,
        children: [{ type: "inlineCode", value: item.fullName }],
      },
    ];
  },
};

// ---- transform: emit objects.inv during the build (R1) --------------------
const emitInventory = {
  name: "myst-pyapi:emit-inventory",
  stage: "project",
  plugin: () => (_tree: any, _file: any) => {
    try {
      const index = getIndex();
      const buf = renderInventory(index, {
        project: process.env.MYST_PYAPI_PROJECT ?? "sample",
        version: process.env.MYST_PYAPI_VERSION ?? "0.1.0",
        pageUriFor,
      });
      const out = process.env.MYST_PYAPI_INV ?? "build/objects.inv";
      mkdirSync(dirname(out), { recursive: true });
      writeFileSync(out, buf);
    } catch {
      // best-effort; never fail the build over inventory emission
    }
  },
};

export * from "./ir.js";
export { getIndex, EXTRACTORS };

export default {
  name: "myst-pyapi",
  directives: [apidoc],
  roles: [pyRole],
  transforms: [emitInventory],
};
