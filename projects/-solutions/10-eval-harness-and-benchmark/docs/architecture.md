# Architecture

This document describes the internal architecture of the eval harness.
For usage, see the [README](../README.md).

## Design principles

1. **Deterministic by default.** Same agent + dataset + evaluators + seed →
   byte-identical report. Parallelism is opt-in, never the default.
2. **Crash-safe.** If an agent or evaluator blows up on one row, the
   runner captures the exception, marks the row as failed, and continues.
   The report always contains every row.
3. **Framework-agnostic.** The runner does not care whether your agent is
   LangGraph, OpenAI Agents SDK, CrewAI, or plain Python. Anything that
   subclasses `BaseAgent` works.
4. **One contract for evaluators.** Every evaluator implements
   `evaluate(row, output, trajectory) -> EvalResult`. Adding a new
   evaluator is a one-file change.
5. **Reports are baselines.** A "baseline" is just a previous report's
   JSON. No special format, no migration scripts.

## Component map

```
                 ┌────────────────────────────────────────────┐
                 │                   CLI (Rich)                │
                 │   eval run --agent X --dataset Y            │
                 └───────────────┬────────────────────────────┘
                                 │
                                 ▼
         ┌───────────────────────────────────────────────────┐
         │  Registry (benchmarks/registry.yaml)              │
         │  pattern → { datasets, evaluators, baseline }      │
         └───────────────┬───────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────────────────────┐
         │  Runner                                          │
         │  for row in dataset:                             │
         │      output, trajectory = agent.run(row.input)    │
         │      for ev in evaluators:                       │
         │          results.append(ev.evaluate(...))        │
         └───────────────┬───────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────────────────────┐
         │  Reporter                                        │
         │  Markdown + JSON, with baseline delta             │
         └───────────────────────────────────────────────────┘
```

## The schema layer (`eval/schemas.py`)

All data flowing through the harness is a Pydantic model:

- `DatasetRow` — one row of a golden dataset (input + expected + tags).
- `ExpectedOutput` — the golden answer + optional hints (`must_contain`,
  `regex`, `numeric_value`, etc.). Allows extra fields so you can attach
  custom hints without forking the schema.
- `AgentOutput` — what an agent returns. `answer` is required;
  `trajectory` is optional but heavily used.
- `Trajectory` / `TrajectoryStep` / `ToolCall` — the execution trace.
- `EvalResult` — one evaluator's verdict on one row.
- `RowResult` — all evaluator results for one row + the agent output.
- `RunSummary` / `RunReport` — the aggregate.

Everything is `model_config = ConfigDict(extra="allow")` where it makes
sense, so real-world agents that produce messy output do not blow up the
harness.

## The evaluator layer (`eval/evaluators/`)

Every evaluator inherits from `BaseEvaluator`:

```python
class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult: ...
```

`EvaluatorRegistry` is a name → class registry. `eval/evaluators/__init__.py`
registers the built-in evaluators at import time, so just importing the
package makes them available.

### Rule-based evaluators (`rule_based.py`)

Fast, deterministic, zero API cost:

- `exact_match` — normalised string equality.
- `contains` — `must_contain` / `must_not_contain` substrings.
- `regex_match` — regex against the answer.
- `numeric_close` — first number in the answer vs. `numeric_value` ±
  `numeric_tolerance`.
- `json_field_match` — dotted-path lookup into a JSON answer.

### LLM-as-judge (`llm_judge.py`)

Three providers:

- `mock` (default) — deterministic stub that scores by token-overlap.
  No API key required. Reproducible to the byte.
- `openai` — calls the OpenAI chat completions API. Requires
  `OPENAI_API_KEY`.
- `anthropic` — calls the Anthropic messages API. Requires
  `ANTHROPIC_API_KEY`.

Provider selection is via `EVAL_LLM_PROVIDER` env var or the
`provider=` param on the evaluator spec.

The judge is prompted with a rubric and asked to return a JSON object
`{"score": <0-1>, "passed": <bool>, "rationale": "<sentence>"}`. The
parser is robust to extra prose and missing fields.

### Trajectory (`trajectory.py`)

Compares the agent's executed trajectory to a hand-labeled reference
(stored in `benchmarks/trajectories/*.jsonl`). Three sub-scores:

1. **Step count** — penalty if the agent took a wildly different number
   of steps than the reference.
2. **Tool-call sequence** — Jaccard + positional overlap of the ordered
   tool-call names.
3. **Final state** — normalised string match of the final answer.

Final score is a weighted average (default 0.2 / 0.4 / 0.4). Weights are
configurable per-evaluator via the registry.

### Reliability (`reliability.py`)

Cohen's kappa and Krippendorff's alpha for inter-rater agreement. Used
by the `eval kappa` CLI command to check that two evaluators agree on
the same dataset. The spec target is kappa > 0.6.

## The runner (`eval/runner.py`)

The runner is a plain Python class — no asyncio, no decorators, no
magic. It iterates rows, calls the agent, calls each evaluator, and
collects results.

Key properties:

- **Sequential by default.** Set `EVAL_WORKERS=N` (or `--workers N`) to
  parallelise with a `ThreadPoolExecutor`.
- **Crash-safe.** `_run_one` wraps both the agent call and each
  evaluator call in try/except. Failures become `EvalResult` rows with
  `passed=False` and the error message in `rationale`.
- **Rich progress bar.** Streams per-row pass/fail to the console so
  long-running evals don't look frozen.

## The reporter (`eval/reporter.py`)

Two outputs per run:

1. **Markdown** (`.md`) — human-readable, with per-row table, per-
  evaluator aggregate, baseline delta, and reproducibility meta.
2. **JSON** (`.json`) — the same data as a Pydantic-serialised
  `RunReport`. Can be loaded back as a baseline.

A baseline is just a previous JSON report. `diff_against_baseline`
compares the current summary to the baseline summary and returns a dict
of deltas (e.g. `{"pass_rate": +0.05, "exact_match": +0.1}`).

## The CLI (`eval/cli.py`)

Built with Typer + Rich. Five subcommands:

- `eval run` — run an agent against a dataset (or pattern).
- `eval list` — print the benchmark registry.
- `eval lint-dataset` — validate a JSONL dataset against the schema.
- `eval kappa` — compute Cohen's kappa between two evaluators.
- `eval evaluators` — list all registered evaluators.

The CLI is intentionally thin — every command just wires together
pieces from the rest of the package and prints something useful.

## Extending the harness

Three extension points, each documented in its own file:

1. **Add a dataset** — see [adding_datasets.md](adding_datasets.md).
2. **Add an evaluator** — see [writing_evaluators.md](writing_evaluators.md).
3. **Add an agent** — see `examples/custom_agent.py`.
