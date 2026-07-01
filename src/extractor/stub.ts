// SPEC §7/§11-M1 — stubbed extractor. Hardcodes the `sample` object model so the
// linking proof is not blocked on real extraction. Anchors == fullName (exact case).

import type { ApiIndex, ApiItem, Extractor } from "../ir.js";

export function buildStubIndex(): ApiIndex {
  const items: Record<string, ApiItem> = {
    sample: {
      fullName: "sample",
      name: "sample",
      kind: "module",
      docstring: null,
      children: ["sample.Match", "sample.match", "sample.subpkg"],
      anchor: "sample",
    },
    "sample.Match": {
      fullName: "sample.Match",
      name: "Match",
      kind: "class",
      docstring: null,
      bases: [],
      children: ["sample.Match.group"],
      anchor: "sample.Match",
    },
    "sample.match": {
      fullName: "sample.match",
      name: "match",
      kind: "function",
      docstring: null,
      signature: {
        params: [
          {
            name: "pattern",
            kind: "positional_or_keyword",
            annotation: null,
            default: null,
          },
          {
            name: "string",
            kind: "positional_or_keyword",
            annotation: null,
            default: null,
          },
        ],
        returnAnnotation: "Match | None",
      },
      anchor: "sample.match",
    },
    "sample.Match.group": {
      fullName: "sample.Match.group",
      name: "group",
      kind: "method",
      docstring: null,
      signature: {
        params: [
          {
            name: "index",
            kind: "positional_or_keyword",
            annotation: null,
            default: "0",
          },
        ],
        returnAnnotation: null,
      },
      anchor: "sample.Match.group",
    },
    "sample.subpkg": {
      fullName: "sample.subpkg",
      name: "subpkg",
      kind: "module",
      docstring: null,
      children: ["sample.subpkg.Widget", "sample.subpkg.build"],
      anchor: "sample.subpkg",
    },
    "sample.subpkg.Widget": {
      fullName: "sample.subpkg.Widget",
      name: "Widget",
      kind: "class",
      docstring: null,
      bases: [],
      children: [],
      anchor: "sample.subpkg.Widget",
    },
    "sample.subpkg.build": {
      fullName: "sample.subpkg.build",
      name: "build",
      kind: "function",
      docstring: null,
      anchor: "sample.subpkg.build",
    },
  };

  return { items, roots: ["sample"] };
}

export const stubExtractor: Extractor = {
  name: "stub",
  async analyze(): Promise<ApiIndex> {
    return buildStubIndex();
  },
};
