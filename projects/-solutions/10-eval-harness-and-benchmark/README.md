# Project 10 — Eval Harness and Benchmark

> Difficulty: ⭐⭐⭐⭐ · Estimated time: 3–4 weeks · Status: reference implementation

A reusable evaluation harness for benchmarking LangGraph (and other) agents
against standardized golden datasets, with **per-pattern** datasets and
**rule-based / LLM-as-judge / trajectory** evaluators. Think of it as
**"pytest for agents"** — drop it into any agentic project and get a real
eval suite, not a vibe check.

This is the canonical **"eval"** project from the Agentic AI Roadmap. It
exercises the evaluation discipline that most directly separates senior
agentic AI engineers from junior ones.

---

## Table of contents

1. [Why this project exists](#why-this-project-exists)
2. [Architecture](#architecture)
3. [Quickstart](#quickstart)
4. [CLI reference](#cli-reference)
5. [Datasets](#datasets)
6. [Evaluators](#evaluators)
7. [Plugging in your own agent](#plugging-in-your-own-agent)
8. [Reports](#reports)
9. [Reproducibility & reliability](#reproducibility--reliability)
10. [Stretch goals](#stretch-goals)
11. [Project layout](#project-layout)
12. [License](#license)

---

## Why this project exists

Most agent teams ship a demo, get a "wow", then quietly lose the ability to
tell whether v2 is actually better than v1. The fix is not more demos — it
is a deterministic, version-controlled eval harness that can be run from CI
on every commit. This project is that harness.

Concretely, it gives you:

- A **CLI** (`eval run --agent <path> --dataset <name>`) that runs an agent
  against a golden dataset and prints a pass/fail table.
- A **benchmark registry** (YAML) that maps each agent pattern (ReAct,
  plan-and-execute, supervisor, swarm, map-reduce) to the datasets and
  evaluators that are appropriate for it.
- A **runner** that executes the agent row-by-row, captures the trajectory,
  and feeds both into evaluators.
- A library of **evaluators** with a uniform interface
  (`evaluate(input, expected, output, trajectory) -> EvalResult`), so you
  can mix rule-based, LLM-as-judge, and trajectory evaluators in one run.
- A **reporter** that emits a Markdown report with per-test pass/fail,
  per-evaluator scores, and a delta against a stored baseline.

The harness also evaluates *itself*: see the meta-eval rubric below.

## Architecture

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

The runner is intentionally sequential-and-deterministic by default.
Parallelism is opt-in via `EVAL_WORKERS`, because reproducibility matters
more than throughput in an eval harness.

## Quickstart

```bash
# 1. Install (editable, with dev deps)
make dev-install

# 2. Copy env template (defaults work out-of-the-box with the mock judge)
cp .env.example .env

# 3. Run the end-to-end demo: a sample ReAct agent vs the react dataset
make demo

# 4. Open the generated report
cat reports/demo_react.md
```

You should see a Rich-rendered progress bar, a per-row table, and a final
summary block. No API keys required — the harness ships with a deterministic
**mock LLM judge** so it works offline.

## CLI reference

```bash
# Run a single agent against a single dataset
eval run --agent eval.agents.sample_agents:ReActSampleAgent --dataset react

# Run against a whole pattern (uses registry.yaml)
eval run --agent eval.agents.sample_agents:PlanExecuteSampleAgent --pattern plan_execute

# Compare against a stored baseline
eval run --agent my_agent:Agent --dataset react --baseline benchmarks/baselines/baseline_v1.json

# Lint a dataset for schema errors
eval lint-dataset benchmarks/datasets/react.jsonl

# Print the registry
eval list

# Compute inter-rater agreement (kappa) between two judges on a dataset
eval kappa --dataset react --judge-a rule_based --judge-b llm_judge
```

Run `eval --help` for the full list.

## Datasets

A dataset is a JSONL file where each line is a row with the following shape
(see `eval.schemas.DatasetRow`):

```json
{
  "id": "react-001",
  "input": "What is the capital of France?",
  "expected": {"answer": "Paris"},
  "tags": ["factual", "geography"],
  "adversarial": false,
  "trajectory_ref": "react-001"
}
```

Five golden datasets ship with the harness, one per pattern:

| Pattern          | File                                       | Rows |
|------------------|--------------------------------------------|------|
| ReAct            | `benchmarks/datasets/react.jsonl`          | 12   |
| Plan-and-execute | `benchmarks/datasets/plan_execute.jsonl`   | 12   |
| Supervisor       | `benchmarks/datasets/supervisor.jsonl`     | 12   |
| Swarm            | `benchmarks/datasets/swarm.jsonl`          | 12   |
| Map-reduce       | `benchmarks/datasets/map_reduce.jsonl`     | 12   |

Each dataset includes a mix of factual, multi-step, and **adversarial**
cases (rows with `"adversarial": true`). The spec calls for 50 rows each —
this reference ships 12 representative rows per pattern and a `make
expand-datasets` helper (TODO) that grows them to 50.

## Evaluators

Every evaluator inherits from `eval.evaluators.base.BaseEvaluator` and
implements:

```python
def evaluate(self, row: DatasetRow, output: AgentOutput, trajectory: Trajectory) -> EvalResult
```

Three families ship out of the box:

1. **Rule-based** (`rule_based.py`) — `exact_match`, `contains`,
   `regex_match`, `numeric_close`, `json_field_match`. Fast, deterministic,
   zero API cost.
2. **LLM-as-judge** (`llm_judge.py`) — calls an LLM with a rubric prompt
   and parses a 0–1 score plus a rationale. Supports `mock`, `openai`, and
   `anthropic` providers via `EVAL_LLM_PROVIDER`. The mock provider is a
   deterministic stub, so the harness is fully usable offline.
3. **Trajectory** (`trajectory.py`) — compares the agent's executed
   trajectory to a hand-labeled reference trajectory
   (`benchmarks/trajectories/*.jsonl`). Checks step count, tool-call
   sequence, and final-state equality.

## Plugging in your own agent

Subclass `eval.agents.base.BaseAgent` and implement `run(self, input: str)
-> AgentOutput`. Then point the CLI at it with a `module:Class` path:

```python
# my_agent.py
from eval.agents.base import BaseAgent, AgentOutput

class MyAgent(BaseAgent):
    def run(self, input: str) -> AgentOutput:
        # ... your LangGraph / OpenAI Agents SDK / CrewAI code ...
        return AgentOutput(answer="...", steps=[...])
```

```bash
eval run --agent my_agent:MyAgent --dataset react
```

See `examples/custom_agent.py` for a fully worked example, and
`examples/custom_evaluator.py` for how to add your own evaluator.

## Reports

Each run writes two files into `reports/`:

- `<name>.md` — a human-readable Markdown report with:
  - Per-test pass/fail table
  - Per-evaluator aggregate score
  - Delta vs baseline (if `--baseline` was passed)
  - Reproducibility meta-info (seed, provider, host)
- `<name>.json` — the same data in machine-readable form for CI gating.

A baseline is just a previous report's JSON, so you can pin a known-good
run and gate PRs on regressions:

```bash
eval run --agent my_agent:Agent --dataset react \
         --baseline reports/last_green.json
```

## Reproducibility & reliability

The harness is designed to be reproducible to within **2 percentage points**
on the same agent/dataset/evaluator (the spec target). Three mechanisms
enforce this:

1. **Deterministic seed** (`EVAL_SEED=42`) flows into both the mock judge
   and the runner's shuffle order.
2. **Temperature 0** for the LLM judge by default (override via
   `EVAL_LLM_TEMPERATURE` if you must).
3. **Sequential execution** by default. Parallel workers are opt-in.

For **inter-rater reliability** (target: Cohen's kappa > 0.6 on 100
samples), use `eval kappa` to compute agreement between any two evaluators
on a dataset. The harness ships with a `reliability.py` module that
implements Cohen's kappa and Krippendorff's alpha.

### Meta-eval rubric (the harness evaluates itself)

| Metric              | Target                      | How measured                                   |
|---------------------|-----------------------------|------------------------------------------------|
| Pattern coverage    | 5+ patterns                 | Count of patterns in `registry.yaml`           |
| Evaluator reliability | kappa > 0.6               | `eval kappa --judge-a rule_based --judge-b llm_judge` |
| Runtime             | under 10 minutes            | 50-row dataset, one agent, default workers     |
| Reproducibility     | within 2 percentage points  | Run twice, diff aggregate scores               |

## Stretch goals

The spec lists three stretch goals. The codebase is structured to make them
additive, not invasive:

- **Non-LangGraph agents (OpenAI Agents SDK, CrewAI)** via A2A — implement
  `BaseAgent` for each SDK; the runner does not care.
- **Online evals** — add a `eval watch` subcommand that consumes production
  traces (e.g. from LangSmith) and re-runs evaluators against them.
- **Comparative evals (A/B)** — `eval compare --agent-a X --agent-b Y
  --dataset Z` runs both and emits a side-by-side delta report.

These are left as exercises / PRs.

## Project layout

```
10-eval-harness-and-benchmark/
├── README.md
├── pyproject.toml
├── requirements*.txt
├── Makefile
├── .env.example
├── eval/
│   ├── cli.py                # Rich + typer CLI
│   ├── config.py             # env-driven config
│   ├── schemas.py            # Pydantic models
│   ├── registry.py           # YAML registry loader
│   ├── runner.py             # the runner
│   ├── reporter.py           # Markdown + JSON reporter
│   ├── utils.py
│   ├── evaluators/
│   │   ├── base.py
│   │   ├── rule_based.py
│   │   ├── llm_judge.py
│   │   ├── trajectory.py
│   │   └── reliability.py    # kappa, alpha
│   └── agents/
│       ├── base.py
│       └── sample_agents.py  # one sample agent per pattern
├── benchmarks/
│   ├── registry.yaml
│   ├── datasets/*.jsonl      # 5 golden datasets
│   ├── trajectories/*.jsonl  # hand-labeled reference trajectories
│   └── baselines/baseline_v1.json
├── tests/                    # pytest suite
├── examples/                 # quickstart, custom_agent, custom_evaluator
├── reports/                  # generated reports (gitignored)
└── docs/                     # architecture / dataset / evaluator guides
```

## License

MIT — see [LICENSE](LICENSE).
