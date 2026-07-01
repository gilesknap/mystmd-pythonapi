// Renders an ApiIndex to MyST AST (mdast). Reuses the shape ideas from
// stefanv/myst-apidoc's renderer (heading + definition lists, docstring bodies
// spliced via parseMyst) but wraps every object in a `div` carrying an
// EXACT-CASE `html_id` anchor — the one node form proven to survive myst's
// identifier normalization (headings/mystTarget lowercase; div html_id does not).
// See FINDINGS.md §3/§4.

import type { ApiIndex, ApiItem } from "../ir.js";

// Loose node type — we emit plain mdast objects; myst validates them.
type Node = Record<string, any>;
type Parse = (s: string) => any;

const KIND_LABEL: Record<string, string> = {
  module: "module",
  class: "class",
  exception: "exception",
  function: "function",
  method: "method",
  property: "property",
  attribute: "attribute",
  data: "data",
};

export interface RenderOpts {
  parse?: Parse; // ctx.parseMyst — turns a MyST docstring body into nodes
  pageUriFor: (item: ApiItem) => string;
}

const text = (value: string): Node => ({ type: "text", value });
const inlineCode = (value: string): Node => ({ type: "inlineCode", value });

// The IR `kind` strings come from griffe's ParameterKind.value with spaces ->
// underscores (python/pyapi_extract.py), i.e. hyphens are preserved:
//   positional-only | positional_or_keyword | variadic_positional |
//   keyword-only | variadic_keyword
type Param = NonNullable<ApiItem["signature"]>["params"][number];

// Display name with the varargs sigil (`*args` / `**kwargs`); plain otherwise.
function paramDisplayName(p: Param): string {
  if (p.kind === "variadic_positional") return `*${p.name}`;
  if (p.kind === "variadic_keyword") return `**${p.name}`;
  return p.name;
}

export function signatureString(item: ApiItem): string {
  if (!item.signature) return item.fullName;
  const ps = item.signature.params;
  // Index of the last positional-only param → a `/` marker goes after it.
  let lastPosOnly = -1;
  ps.forEach((p, i) => {
    if (p.kind === "positional-only") lastPosOnly = i;
  });

  const parts: string[] = [];
  let starEmitted = false; // a `*args` or a bare `*` already opened the kw-only group
  ps.forEach((p, i) => {
    // keyword-only group opener: a bare `*`, unless `*args` already opened it.
    if (p.kind === "keyword-only" && !starEmitted) {
      parts.push("*");
      starEmitted = true;
    }
    const isVariadic =
      p.kind === "variadic_positional" || p.kind === "variadic_keyword";
    if (p.kind === "variadic_positional") starEmitted = true;
    let s = paramDisplayName(p);
    if (p.annotation) s += `: ${p.annotation}`;
    // *args/**kwargs never carry a default in Python syntax (griffe reports
    // ()/{} as their "default"); only real params render `=default`.
    if (p.default != null && !isVariadic) s += `=${p.default}`;
    parts.push(s);
    if (i === lastPosOnly) parts.push("/"); // positional-only separator
  });

  let sig = `${item.name}(${parts.join(", ")})`;
  if (item.signature.returnAnnotation) sig += ` -> ${item.signature.returnAnnotation}`;
  return sig;
}

function parseBody(parse: Parse | undefined, doc: string | null): Node[] {
  if (!doc || !parse) return [];
  try {
    const r = parse(doc);
    const children = Array.isArray(r) ? r : r?.children;
    return Array.isArray(children) ? children : [];
  } catch {
    return [];
  }
}

function paramsList(item: ApiItem): Node[] {
  if (!item.signature || item.signature.params.length === 0) return [];
  const dl: Node = {
    type: "definitionList",
    children: item.signature.params.flatMap((p) => {
      const term: Node[] = [inlineCode(paramDisplayName(p))];
      if (p.annotation) {
        term.push(text(" : "), { type: "emphasis", children: [text(p.annotation)] });
      }
      const descChildren: Node[] = [];
      const isVariadic =
        p.kind === "variadic_positional" || p.kind === "variadic_keyword";
      if (p.default != null && !isVariadic) {
        descChildren.push(text(`default: ${p.default}`));
      }
      return [
        { type: "definitionTerm", children: term },
        {
          type: "definitionDescription",
          children: descChildren.length ? [{ type: "paragraph", children: descChildren }] : [],
        },
      ];
    }),
  };
  return [{ type: "heading", depth: 6, children: [text("Parameters")] }, dl];
}

// Render one object as a div with an exact-case html_id anchor.
export function renderItem(item: ApiItem, opts: RenderOpts, depth: number): Node {
  const inner: Node[] = [];
  inner.push({
    type: "heading",
    depth,
    children: [inlineCode(item.name), text(`  — ${KIND_LABEL[item.kind] ?? item.kind}`)],
  });
  inner.push({ type: "paragraph", children: [inlineCode(signatureString(item))] });
  if (item.bases && item.bases.length) {
    inner.push({ type: "paragraph", children: [text("Bases: "), inlineCode(item.bases.join(", "))] });
  }
  inner.push(...parseBody(opts.parse, item.docstring));
  inner.push(...paramsList(item));
  return { type: "div", html_id: item.anchor, children: inner };
}

// Depth-first over roots and children; each object rendered once.
export function renderIndex(index: ApiIndex, opts: RenderOpts, startDepth = 2): Node[] {
  const nodes: Node[] = [];
  const seen = new Set<string>();
  const emit = (fullName: string, depth: number) => {
    const item = index.items[fullName];
    if (!item || seen.has(fullName)) return;
    seen.add(fullName);
    nodes.push(renderItem(item, opts, Math.min(depth, 6)));
    for (const child of item.children ?? []) emit(child, depth + 1);
  };
  for (const root of index.roots) emit(root, startDepth);
  return nodes;
}
