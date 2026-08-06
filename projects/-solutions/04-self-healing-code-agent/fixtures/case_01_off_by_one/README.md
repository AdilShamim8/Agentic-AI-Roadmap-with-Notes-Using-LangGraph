# Case 01 — off-by-one error

- **Target test:** `tests/test_calc.py::test_sum_range_basic`
- **Bug:** `sum_range(1, 5)` returns `10` instead of `15` because `range(start, end)`
  uses an exclusive upper bound.
- **Expected fix:** change `range(start, end)` → `range(start, end + 1)` in `src/calc.py`.
- **Difficulty:** easy (single-line, single-file).

## Expected patch

```diff
--- a/src/calc.py
+++ b/src/calc.py
@@ -8,4 +8,4 @@
     total = 0
-    for i in range(start, end):  # bug: should be end + 1
+    for i in range(start, end + 1):
         total += i
     return total
```

## Run

```bash
uv run self-heal run fixtures/case_01_off_by_one \
  --test tests/test_calc.py::test_sum_range_basic --no-pr
```
