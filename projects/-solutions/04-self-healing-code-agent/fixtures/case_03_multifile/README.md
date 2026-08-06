"""Case 03 — multi-file bug (stretch goal).

Bug spans two modules:

- `mathlib/stats.py::percentile` uses `1`-based indexing when calling into
  `mathlib/indexing.py::select`, but `select` expects `0`-based indexing.
- The result: `percentile([10, 20, 30, 40, 50], 50)` returns `40` (the value
  at 1-based position 4) instead of `30` (the value at 0-based position 3).

The fix has two acceptable forms:

  (a) Patch `stats.py` to use 0-based indexing when calling `select`.
  (b) Patch `indexing.py` to accept 1-based indexing.

This fixture ships (a) as the expected patch, but the eval harness accepts
either form as long as the test passes and no regressions are introduced.
"""
