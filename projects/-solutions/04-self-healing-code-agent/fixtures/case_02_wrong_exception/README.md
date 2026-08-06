# Case 02 — wrong exception type

- **Target test:** `tests/test_calc.py::test_divide_by_zero`
- **Bug:** `divide(1, 0)` raises `ValueError`, but the test expects `ZeroDivisionError`.
- **Expected fix:** raise `ZeroDivisionError` instead of `ValueError` in `src/calc.py`.
- **Difficulty:** easy (single-line, single-file).

## Expected patch

```diff
--- a/src/calc.py
+++ b/src/calc.py
@@ -8,3 +8,3 @@
     if denominator == 0:
-        raise ValueError("denominator is zero")  # bug: wrong exception type
+        raise ZeroDivisionError("denominator is zero")
     return numerator / denominator
```

## Run

```bash
uv run self-heal run fixtures/case_02_wrong_exception \
  --test tests/test_calc.py::test_divide_by_zero --no-pr
```
