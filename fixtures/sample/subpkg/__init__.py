"""Nested namespace with a widget builder."""


class Widget:
    """A renderable **widget**.

    - holds view state,
    - knows how to render itself.
    """

    def render(self):
        """Render the widget to a string."""


def build(spec):
    """Build a :py:class:`Widget` from ``spec``.

    - **spec**: the widget specification.
    """


__all__ = ["Widget", "build"]
