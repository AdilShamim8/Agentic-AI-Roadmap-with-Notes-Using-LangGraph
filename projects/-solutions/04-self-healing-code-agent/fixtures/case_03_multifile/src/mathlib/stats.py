"""Statistics helpers."""

from mathlib.indexing import select


def percentile(values: list[float], pct: int) -> float:
    """Return the `pct`-th percentile of `values` (0 <= pct <= 100).

    Uses nearest-rank: the index is `ceil(pct/100 * n)`, 1-based.
    """
    n = len(values)
    if n == 0:
        raise ValueError("empty list")
    if not 0 <= pct <= 100:
        raise ValueError("pct must be between 0 and 100")

    sorted_vals = sorted(values)
    # 1-based rank.
    rank = max(1, (pct * n + 99) // 100)
    # BUG: passing a 1-based rank directly to `select`, which expects 0-based.
    return select(sorted_vals, rank)
