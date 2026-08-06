"""Case 01 — off-by-one error.

Bug: `sum_range(1, 5)` should return 1+2+3+4+5 = 15, but the implementation
uses an exclusive upper bound and returns 1+2+3+4 = 10.

The fix: change `range(start, end)` to `range(start, end + 1)`.
"""


def sum_range(start: int, end: int) -> int:
    """Return the sum of all integers from `start` to `end` inclusive."""
    total = 0
    for i in range(start, end):  # bug: should be end + 1
        total += i
    return total
