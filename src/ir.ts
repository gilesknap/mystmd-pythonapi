// SPEC §8 — The IR / extractor interface.
// These types are consumed by the linking layer verbatim.

export type ItemKind =
  | "module"
  | "class"
  | "exception"
  | "function"
  | "method"
  | "property"
  | "attribute"
  | "data";

// maps 1:1 to Sphinx py-domain roles for objects.inv:
//   module->py:module class->py:class exception->py:exception
//   function->py:function method->py:method property->py:property
//   attribute->py:attribute data->py:data

export interface ApiItem {
  fullName: string; // EXACT CASE, dotted, canonical: "re.Match", "re.match", "re.Match.group"
  name: string; // "Match"
  kind: ItemKind;
  docstring: string | null; // raw; body is MyST
  docstringStyle?: "numpy" | "google" | "sphinx";
  // Normalized docstring sections (griffe M3). Equivalent numpy/google/sphinx
  // docstrings yield equivalent (whitespace-trimmed) sections.
  docstringSections?: {
    summary: string | null;
    parameters: { name: string; annotation: string | null; description: string }[];
    returns: string | null;
    raises: { type: string | null; description: string }[];
  };
  signature?: {
    params: {
      name: string;
      kind: string;
      annotation: string | null;
      default: string | null;
    }[];
    returnAnnotation: string | null;
  };
  bases?: string[];
  annotation?: string | null;
  value?: string | null;
  modifiers?: string[];
  children?: string[]; // fullNames of direct children
  anchor: string; // exact-case anchor used in the built page + objects.inv uri fragment
}

export interface ApiIndex {
  items: Record<string, ApiItem>;
  roots: string[];
}

export interface Extractor {
  name: string; // "stub" | "griffe" | "numpydoc" | "tree-sitter" ...
  analyze(packageRoots: string[]): Promise<ApiIndex>;
  // optional incremental hook for watch mode:
  invalidate?(changedFile: string): void;
}
