# Evaluation

The project ships a small evaluation harness that runs the agent over a
directory of fixture cases and reports the four rubric metrics from the
spec.

## Rubric

| metric | target | how measured |
|--------|--------|--------------|
| Pass rate | ≥ 40% | fraction of cases whose target test now passes |
| No-regression rate | ≥ 95% | of *successful* patches, fraction that don't break other tests |
| Cost per patch | < $1.00 | total USD spent (incl. failed cases) ÷ number of successful patches |
| Trajectory efficiency | median < 8 LLM calls | per-case LLM call count |

The 40% / 95% / $1 / 8-calls targets come straight from the project spec
(which itself mirrors SWE-bench-lite baselines). On the bundled fixtures
with a strong model (GPT-4o or Claude Sonnet 4.5) you should comfortably
beat all four.

## Fixtures

Each fixture under `fixtures/` is a self-contained Python repo:

```
case_XX_name/
  src/...                # buggy source
  tests/test_*.py        # failing test(s)
  pyproject.toml         # sets pythonpath = ["src"] so tests can import src
  case.json              # metadata: target_test, bug_summary, difficulty
  expected_patch.diff    # gold patch (informational; not enforced)
  README.md              # human-readable case description
```

The bundled cases are deliberately small and toy-like so the harness can run
in seconds:

| case | bug | files | difficulty |
|------|-----|-------|------------|
| `case_01_off_by_one` | `range(start, end)` should be `range(start, end + 1)` | 1 | easy |
| `case_02_wrong_exception` | raises `ValueError` instead of `ZeroDivisionError` | 1 | easy |
| `case_03_multifile` | 1-based rank passed to a 0-based `select` | 2 (stretch goal) | medium |

### Adding a real case

To evaluate against SWE-bench-lite-style cases, drop new `case_*/`
directories into `fixtures/` (or point `--fixtures` at a different dir).
Each case needs:

- A `tests/` dir with at least one failing test.
- A `case.json` with `target_test` set to the pytest nodeid that should pass
  after the patch.
- A `pyproject.toml` (or `conftest.py` / `setup.py`) that makes `src/`
  importable.

The eval runner copies each case into a temp dir, initializes git, runs the
agent, then re-runs the full suite to confirm pass + no-regression.

## Running the harness

```bash
# all cases
uv run self-heal-eval run --fixtures fixtures --max-iterations 3

# one case
uv run self-heal-eval run --fixtures fixtures --only case_01

# JSON output (for CI / dashboards)
uv run self-heal-eval run --fixtures fixtures --json > eval-report.json

# list without running
uv run self-heal-eval list --fixtures fixtures
```

## Sample output

```
per-case results
├ case            ┤ passed ┤ no-reg ┤ iters ┤ llm ┤ cost   ┤ status   ┤
│ case_01_off_by_one     │   ✓    │   ✓    │   1   │  3  │ $0.0021 │ passed   │
│ case_02_wrong_exception│   ✓    │   ✓    │   1   │  3  │ $0.0019 │ passed   │
│ case_03_multifile      │   ✓    │   ✓    │   2   │  6  │ $0.0042 │ passed   │

rubric metrics
├ metric               ┤ value  ┤ target ┤
│ pass rate            │ 100.0% │ ≥ 40%  │
│ no-regression rate   │ 100.0% │ ≥ 95%  │
│ cost per patch       │ $0.002 │ < $1   │
│ median LLM calls     │   3.0  │ < 8    │
│ total cost           │ $0.008 │        │
│ cases                │   3/3  │        │
```

(Numbers above are illustrative; actual cost depends on the configured model
and prompt lengths.)

## Interpreting results

- **Pass rate < 40%** — usually means the model is too weak, the prompt is
  ambiguous, or the fixtures are too hard. Start by inspecting LangSmith
  trajectories for the failed cases.
- **No-regression rate < 95%** — the patch is too aggressive (refactoring
  unrelated code). Tighten the patch prompt ("smallest possible change").
- **Cost per patch > $1** — either the model is expensive, the context
  window is bloated (cap file reads), or the loop is iterating too many
  times before succeeding.
- **Median LLM calls > 8** — the diagnosis is poor, so the first patch
  fails and reflexion kicks in. Improve the diagnosis prompt or feed more
  context.
