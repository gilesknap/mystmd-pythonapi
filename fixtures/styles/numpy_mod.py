"""Numpy-style docstring fixture (styles.numpy_mod)."""


def combine(first, second):
    """Combine two values into a single result.

    Parameters
    ----------
    first : int
        The first value to combine.
    second : int
        The second value to combine.

    Returns
    -------
    int
        The combined value of the two inputs.

    Raises
    ------
    ValueError
        If either input is negative.
    """
    if first < 0 or second < 0:
        raise ValueError("inputs must be non-negative")
    return first + second


class Thing:
    """A thing that holds a value.

    Attributes
    ----------
    value : int
        The stored value.
    """

    value = 0
