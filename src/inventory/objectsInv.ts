// SPEC §8 — pure-JS Sphinx inventory v2 writer.
// No external deps; uses node's built-in zlib.

import { deflateSync } from "node:zlib";
import { writeFileSync } from "node:fs";
import type { ApiIndex, ApiItem, ItemKind } from "../ir.js";

const ROLE_BY_KIND: Record<ItemKind, string> = {
  module: "module",
  class: "class",
  exception: "exception",
  function: "function",
  method: "method",
  property: "property",
  attribute: "attribute",
  data: "data",
};

export interface RenderInventoryOpts {
  project: string;
  version: string;
  pageUriFor: (item: ApiItem) => string;
}

export function renderInventory(
  index: ApiIndex,
  opts: RenderInventoryOpts,
): Buffer {
  const header =
    `# Sphinx inventory version 2\n` +
    `# Project: ${opts.project}\n` +
    `# Version: ${opts.version}\n` +
    `# The remainder of this file is compressed using zlib.\n`;

  const items = Object.values(index.items).sort((a, b) =>
    a.fullName < b.fullName ? -1 : a.fullName > b.fullName ? 1 : 0,
  );

  let body = "";
  for (const item of items) {
    const role = ROLE_BY_KIND[item.kind];
    const priority = "1";
    const page = opts.pageUriFor(item);
    // ALWAYS emit an EXPLICIT, exact-case anchor — never the Sphinx `$`
    // shorthand. mystmd's intersphinx loader (Inventory.setEntry) expands `$`
    // with `.toLowerCase()`, which collapses case-distinct entries such as
    // `sample.Match` and `sample.match` onto the same URL. Explicit anchors are
    // preserved verbatim by both mystmd AND Sphinx, so a single generated
    // inventory is consumable case-sensitively by both. (See FINDINGS.md.)
    const uri = page + "#" + item.anchor;
    const dispname = item.name;
    body += `${item.fullName} py:${role} ${priority} ${uri} ${dispname}\n`;
  }

  const compressed = deflateSync(Buffer.from(body, "utf-8"));
  return Buffer.concat([Buffer.from(header, "utf-8"), compressed]);
}

export function writeInventoryFile(
  path: string,
  index: ApiIndex,
  opts: RenderInventoryOpts,
): void {
  writeFileSync(path, renderInventory(index, opts));
}
