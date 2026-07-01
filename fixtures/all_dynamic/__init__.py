"""Package building ``__all__`` dynamically at import time.

End result must equal ``["a", "B"]`` (order a then B).
"""

__all__ = []


def _export(obj):
    """Register ``obj`` in ``__all__`` by name and return it."""
    __all__.append(obj.__name__)
    return obj


@_export
def a():
    """Function a."""
    return "a"


class B:
    """Class B."""


__all__ += ["B"]
