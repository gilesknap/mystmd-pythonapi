"""SPEC M2-M5 — griffe-backed extraction CORE (importable, no CLI).

This module holds the entire extraction implementation: kind mapping,
signatures, docstring style detection + normalized sections, __all__ /
re-import canonicalization, and the tree walk. It is used two ways:

* python/extract.py  — a one-shot CLI (cold: a fresh interpreter per run).
* python/sidecar.py  — a PERSISTENT process that keeps griffe WARM across
  many requests via the ``Analyzer`` class (reuse one GriffeLoader + import
  cache; ``invalidate`` drops the cached module(s) so the next ``analyze``
  re-reads from disk).

The public entry points are:

    analyze(roots, package) -> dict          # cold, stateless
    Analyzer().analyze(roots, package)       # warm, reuses a GriffeLoader
    Analyzer().invalidate(package)           # drop caches for `package`

See extract.py's original module docstring for the canonicalization rules
(R7 / T7a): re-exports are recorded under their PUBLIC path via ``alias.path``.
"""

from __future__ import annotations

import importlib
import logging
import sys
from typing import Any, Optional

import griffe
from griffe import Docstring, Parser


# griffe emits parser warnings to logging; keep stdout clean (JSON only).
logging.getLogger("griffe").setLevel(logging.CRITICAL)


# --------------------------------------------------------------------------
# kind mapping: griffe Kind -> §8 ItemKind
# --------------------------------------------------------------------------
def _is_exception(obj: Any) -> bool:
    """True if a class (transitively, by name) derives from Exception."""
    try:
        for base in obj.bases:
            name = str(getattr(base, "canonical_path", base) or base)
            short = name.rsplit(".", 1)[-1]
            if short in {"Exception", "BaseException"} or short.endswith("Error"):
                return True
    except Exception:
        pass
    return False


def _map_kind(obj: Any, parent_is_class: bool) -> str:
    kind = obj.kind.value  # 'module' | 'class' | 'function' | 'attribute'
    if kind == "module":
        return "module"
    if kind == "class":
        return "exception" if _is_exception(obj) else "class"
    if kind == "function":
        return "method" if parent_is_class else "function"
    if kind == "attribute":
        labels = getattr(obj, "labels", set()) or set()
        if "property" in labels:
            return "property"
        return "attribute" if parent_is_class else "data"
    # receive/parameter/etc. never reached for our public API
    return "data"


# --------------------------------------------------------------------------
# signature
# --------------------------------------------------------------------------
def _signature(obj: Any, is_method: bool) -> Optional[dict]:
    if obj.kind.value != "function":
        return None
    params = []
    for i, p in enumerate(obj.parameters):
        # methods: drop the implicit leading self/cls receiver.
        if is_method and i == 0 and p.name in ("self", "cls"):
            continue
        params.append(
            {
                "name": p.name,
                # normalize griffe's "positional or keyword" -> IR "positional_or_keyword"
                "kind": (p.kind.value.replace(" ", "_") if p.kind is not None else "positional_or_keyword"),
                "annotation": str(p.annotation) if p.annotation is not None else None,
                "default": str(p.default) if p.default is not None else None,
            }
        )
    ret = str(obj.returns) if getattr(obj, "returns", None) is not None else None
    return {"params": params, "returnAnnotation": ret}


# --------------------------------------------------------------------------
# docstrings: style detection + normalized sections
# --------------------------------------------------------------------------
def _detect_style(raw: str) -> Optional[str]:
    """Per-docstring style detection (SPEC M3)."""
    if raw is None:
        return None
    lines = raw.splitlines()
    # numpy: a "Parameters"/"Returns"/... header underlined with dashes.
    for i, line in enumerate(lines[:-1]):
        head = line.strip()
        under = lines[i + 1].strip()
        if head in {"Parameters", "Returns", "Raises", "Attributes", "Yields"} and set(
            under
        ) == {"-"} and len(under) >= 3:
            return "numpy"
    # sphinx: reST field lists.
    if ":param" in raw or ":returns:" in raw or ":rtype:" in raw or ":raises" in raw:
        return "sphinx"
    # google: labelled sections ending in a colon.
    for label in ("Args:", "Returns:", "Raises:", "Yields:", "Attributes:"):
        if any(line.strip() == label for line in lines):
            return "google"
    return None


_PARSER = {"numpy": Parser.numpy, "google": Parser.google, "sphinx": Parser.sphinx}


def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return s.strip()


def _docstring_sections(raw: str, style: Optional[str]) -> Optional[dict]:
    """Parse with griffe's parser for `style`, normalize to the IR_EXT shape.

    Equivalent numpy/google/sphinx docstrings yield equivalent sections
    (whitespace-trimmed).
    """
    if not raw or style is None:
        return None
    try:
        sections = Docstring(raw).parse(_PARSER[style])
    except Exception:
        return None

    summary: Optional[str] = None
    parameters: list = []
    returns: Optional[str] = None
    raises: list = []

    for sec in sections:
        kind = sec.kind.value
        if kind == "text" and summary is None:
            summary = _norm(sec.value)
        elif kind == "parameters":
            for p in sec.value:
                parameters.append(
                    {
                        "name": p.name,
                        "annotation": str(p.annotation) if p.annotation is not None else None,
                        "description": _norm(p.description) or "",
                    }
                )
        elif kind == "returns":
            descs = [_norm(r.description) or "" for r in sec.value]
            joined = "\n".join(d for d in descs if d)
            returns = joined or None
        elif kind == "raises":
            for r in sec.value:
                raises.append(
                    {
                        "type": str(r.annotation) if r.annotation is not None else None,
                        "description": _norm(r.description) or "",
                    }
                )

    return {
        "summary": summary,
        "parameters": parameters,
        "returns": returns,
        "raises": raises,
    }


# --------------------------------------------------------------------------
# public-member resolution (R7)
# --------------------------------------------------------------------------
def _runtime_all(dotted: str) -> Optional[list]:
    """Import `dotted` and return its real (possibly dynamic) __all__, else None."""
    try:
        mod = importlib.import_module(dotted)
    except Exception:
        return None
    names = getattr(mod, "__all__", None)
    if names is None:
        return None
    return list(names)


def _griffe_public(obj: Any) -> list:
    """Fallback: non-underscore members, in declaration order."""
    return [name for name in obj.members if not name.startswith("_")]


def _resolve(member: Any) -> Any:
    """Resolve an alias to its target object (public re-imports, R7)."""
    try:
        return member.target if member.is_alias else member
    except Exception:
        return member


# --------------------------------------------------------------------------
# tree walk
# --------------------------------------------------------------------------
def _walk(obj: Any, dotted: str, public_path: str, items: dict, parent_is_class: bool):
    """Emit an ApiItem for `obj` and recurse into its public members.

    `dotted` is the real importable path (for runtime __all__ lookup);
    `public_path` is the canonical PUBLIC fullName used as the key/anchor.
    """
    kind = _map_kind(obj, parent_is_class)
    is_container = kind in ("module", "class", "exception")
    is_method = kind == "method"

    item: dict = {
        "fullName": public_path,
        "name": public_path.rsplit(".", 1)[-1],
        "kind": kind,
        "docstring": obj.docstring.value if obj.docstring else None,
        "anchor": public_path,
    }

    sig = _signature(obj, is_method)
    if sig is not None:
        item["signature"] = sig

    if kind in ("class", "exception"):
        item["bases"] = [str(b) for b in obj.bases]

    if obj.docstring:
        raw = obj.docstring.value
        style = _detect_style(raw)
        if style:
            item["docstringStyle"] = style
        secs = _docstring_sections(raw, style)
        if secs is not None:
            item["docstringSections"] = secs

    children: list = []
    if is_container:
        # public membership: prefer runtime __all__, else griffe non-underscore.
        names = _runtime_all(dotted) if kind in ("module",) else None
        if names is None:
            names = _griffe_public(obj)
        for name in names:
            if name not in obj.members:
                continue
            member = obj.members[name]
            target = _resolve(member)
            if target is None:
                continue
            child_public = f"{public_path}.{name}"
            child_dotted = f"{dotted}.{name}"
            children.append(child_public)
            _walk(
                target,
                child_dotted,
                child_public,
                items,
                parent_is_class=(kind in ("class", "exception")),
            )
        item["children"] = children

    items[public_path] = item


def _build_from_loader(loader: Any, roots: list, package: str) -> dict:
    """Load `package` with `loader` and walk it into an ApiIndex dict."""
    # runtime import needs the roots on sys.path.
    for r in roots:
        if r not in sys.path:
            sys.path.insert(0, r)

    top = loader.load(package)

    items: dict = {}
    # The public fullName root is the package name as given (e.g. "sample"
    # or "styles.numpy_mod"); griffe's top.path matches it.
    _walk(top, package, top.path, items, parent_is_class=False)

    return {"items": items, "roots": [top.path]}


def build_index(roots: list, package: str) -> dict:
    """Cold, stateless analysis: a fresh GriffeLoader per call."""
    loader = griffe.GriffeLoader(search_paths=roots)
    return _build_from_loader(loader, roots, package)


# Alias — the SPEC M5 name for the cold entry point.
def analyze(roots: list, package: str) -> dict:
    return build_index(roots, package)


class Analyzer:
    """WARM analysis state for the persistent sidecar (SPEC M5 §7).

    Keeps one GriffeLoader alive across ``analyze`` calls so griffe's parsed
    modules are reused. ``invalidate`` drops the cached module(s) — from BOTH
    griffe's collection (by discarding the loader) and Python's own import
    cache (``sys.modules``) — so the next ``analyze`` re-reads from disk and
    reflects edits without a cold process restart.
    """

    def __init__(self) -> None:
        self._loader: Any = None
        self._roots: Optional[list] = None

    def _get_loader(self, roots: list) -> Any:
        if self._loader is None or self._roots != roots:
            self._loader = griffe.GriffeLoader(search_paths=roots)
            self._roots = roots
        return self._loader

    def analyze(self, roots: list, package: str) -> dict:
        loader = self._get_loader(roots)
        return _build_from_loader(loader, roots, package)

    def invalidate(self, package: str) -> None:
        # Drop griffe's cached parse: the cheapest correct thing is to discard
        # the loader so the next analyze rebuilds it from disk.
        self._loader = None
        self._roots = None
        # Drop the runtime import cache for `package` (and submodules) so the
        # __all__ re-import picks up the edited source.
        for name in list(sys.modules):
            if name == package or name.startswith(package + "."):
                del sys.modules[name]
        importlib.invalidate_caches()
