"""Indexing helpers."""


def select(values: list[float], index: int) -> float:
    """Return the element of `values` at 0-based `index`.

    Raises IndexError if out of range.
    """
    return values[index]
