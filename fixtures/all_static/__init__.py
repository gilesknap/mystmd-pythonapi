"""Package exposing a static, literal ``__all__``."""


def a():
    """Function a."""
    return "a"


class B:
    """Class B."""


__all__ = ["a", "B"]
