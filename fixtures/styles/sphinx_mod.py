"""Sphinx-style (reST field-list) docstring fixture (styles.sphinx_mod)."""


def combine(first, second):
    """Combine two values into a single result.

    :param first: The first value to combine.
    :type first: int
    :param second: The second value to combine.
    :type second: int
    :returns: The combined value of the two inputs.
    :rtype: int
    :raises ValueError: If either input is negative.
    """
    if first < 0 or second < 0:
        raise ValueError("inputs must be non-negative")
    return first + second


class Thing:
    """A thing that holds a value.

    :ivar value: The stored value.
    :vartype value: int
    """

    value = 0
