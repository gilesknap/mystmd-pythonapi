"""Sample package mirroring :py:mod:`re`, with a case clash."""
from ._core import Match, match
from . import subpkg

__all__ = ["Match", "match", "subpkg"]
