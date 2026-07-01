"""Fixture: an exception hierarchy for transitive `_is_exception` detection.

``NetworkIssue`` derives from ``Exception`` only INDIRECTLY (via ``Retryable``),
which the old direct-bases-only check misclassified as a plain ``class``.
"""

__all__ = ["Retryable", "NetworkIssue", "PlainThing"]


class Retryable(Exception):
    """A base exception (direct subclass of Exception)."""


class NetworkIssue(Retryable):
    """Indirect subclass — must be classified as ``exception``, not ``class``."""


class PlainThing:
    """A non-exception class — must stay ``class``."""
