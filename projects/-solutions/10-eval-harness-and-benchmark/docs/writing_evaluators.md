# Writing evaluators

Every evaluator inherits from `BaseEvaluator` and implements one method:

```python
from eval.evaluators.base import BaseEvaluator
from eval.schemas import AgentOutput, DatasetRow, EvalResult, Trajectory


class MyEvaluator(BaseEvaluator):
    name = "my_evaluator"

    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        # ... your logic ...
        return EvalResult(
            evaluator=self.display_name(),
            row_id=row.id,
            passed=True,          # bool
            score=1.0,            # float in [0, 1]
            rationale="...",      # optional, short string
            details={"key": "v"}, # optional, any JSON-serialisable dict
        )
```

## The contract

- `row` — the golden dataset row. Has `id`, `input`, `expected`
  (`ExpectedOutput`), `tags`, `adversarial`, `trajectory_ref`.
- `output` — the agent's output. Has `answer` (str | dict | list |
  None), `trajectory`, `metadata`.
- `trajectory` — the agent's execution trajectory. Same as
  `output.trajectory`; passed separately for convenience.
- Return: an `EvalResult` with `passed`, `score` (0-1), optional
  `rationale`, optional `details`.

`score` does NOT have to be 0 or 1 — partial credit is encouraged.
`passed` should be `True` iff the score crosses your pass threshold
(0.7 is the convention).

## Registering your evaluator

```python
from eval.evaluators import EvaluatorRegistry

EvaluatorRegistry.register("my_evaluator", MyEvaluator)
```

After this, you can use it in the registry YAML:

```yaml
evaluators:
  - name: my_evaluator
    kind: rule_based
    params:
      some_param: some_value
```

The `params` dict is passed as `**kwargs` to your evaluator's
`__init__`. (Don't forget to call `super().__init__(**params)`.)

## Patterns to steal from

### Rule-based

See `eval/evaluators/rule_based.py`. The pattern is:

1. Pull what you need from `row.expected`.
2. Compute a deterministic score from `output.answer`.
3. Return an `EvalResult` with full `details` so the report can show
   *why* it passed/failed.

### LLM-as-judge

See `eval/evaluators/llm_judge.py`. The pattern is:

1. Build a system prompt with a rubric.
2. Build a user prompt with the question, answer, and expected.
3. Call `self.client.complete(system, user)` to get a string.
4. Parse the string into `(score, passed, rationale)`.
5. Use the `mock` provider in tests so they're deterministic.

### Trajectory

See `eval/evaluators/trajectory.py`. The pattern is:

1. Load a hand-labeled reference trajectory by id (cache it).
2. If no reference exists, return a neutral 1.0 (don't penalise).
3. Compute sub-scores (step count, tool sequence, final state).
4. Return a weighted average as the final score.

## Testing your evaluator

Drop a test file in `tests/` and use the helpers from
`tests/test_evaluators.py`:

```python
from eval.schemas import DatasetRow, ExpectedOutput, AgentOutput
from eval.evaluators import EvaluatorRegistry

def test_my_evaluator_pass():
    row = DatasetRow(id="x", input="?", expected=ExpectedOutput(answer="42"))
    out = AgentOutput(answer="42")
    ev = EvaluatorRegistry.build("my_evaluator")
    assert ev.evaluate(row, out).passed
```

Always include:

- A positive case (clearly should pass).
- A negative case (clearly should fail).
- A partial-credit case (score in (0, 1)).
- A determinism test (same input → same output, twice).

## Common pitfalls

- **Don't call the LLM directly.** Go through `build_llm_client()` so
  the `mock` provider works in CI.
- **Don't mutate `row` or `output`.** They're Pydantic models; treat
  them as read-only.
- **Don't raise.** If something goes wrong, return an `EvalResult`
  with `passed=False` and the error in `rationale`. The runner will
  catch exceptions, but it's better to handle them yourself so the
  report is informative.
- **Always set `details`.** Future-you will thank past-you when
  debugging a failing run at 2am.
