"""Core primitives for the :py:mod:`sample` package."""


class Match:
    """A successful match result.

    This object wraps the outcome of a successful :py:func:`match`.

    Key ideas:

    - it holds the **matched** text,
    - groups are addressable by index,
    - index ``0`` is the whole match.
    """

    def group(self, index=0):
        """Return the matched substring.

        Retrieves the substring captured by a group.

        - ``index=0`` returns the **entire** match,
        - higher indices return captured sub-groups.

        The cost is {math}`O(1)` since groups are precomputed.
        """


def match(pattern, string):
    """Try to match ``pattern`` at the start of ``string``.

    Attempts to apply the regular expression `pattern` to `string`.

    Parameters:

    - **pattern**: the pattern to apply,
    - **string**: the subject text to scan.

    Returns a :py:class:`Match` on success, or {math}`\\varnothing`
    (``None``) when there is no match.
    """
