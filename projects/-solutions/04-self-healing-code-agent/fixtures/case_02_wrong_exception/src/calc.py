"""Case 02 — wrong exception type.

Bug: `divide(1, 0)` should raise `ZeroDivisionError`, but the implementation
explicitly raises `ValueError` for the zero-divisor case. The test expects
`ZeroDivisionError`.

The fix: raise `ZeroDivisionError` instead of `ValueError`.
"""


def divide(numerator: float, denominator: float) -> float:
    """Divide two numbers, raising ZeroDivisionError on a zero denominator."""
    if denominator == 0:
        raise ValueError("denominator is zero")  # bug: wrong exception type
    return numerator / denominator
