"""Fixture: functions exercising every Python parameter kind.

Used to verify signatureString() reconstructs the positional-only ``/``, the
``*args`` variadic, the keyword-only ``*`` separator, and ``**kwargs``.
"""

__all__ = ["mix", "kwonly", "posonly"]


def mix(pos, /, both, *args, kw, **extra):
    """One of every parameter kind (the `*args` introduces the kw-only group)."""
    return (pos, both, args, kw, extra)


def kwonly(a, *, b, c):
    """Keyword-only params introduced by a bare ``*`` separator."""
    return (a, b, c)


def posonly(a, b, /, c):
    """Positional-only params before the ``/``."""
    return (a, b, c)
