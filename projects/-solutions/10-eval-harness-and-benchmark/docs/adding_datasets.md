# Adding datasets

A dataset is a JSONL file where each line is a `DatasetRow` (see
`eval/schemas.py`). Each row has:

```json
{
  "id": "react-001",
  "input": "What is the capital of France?",
  "expected": {
    "answer": "Paris",
    "allowed_answers": ["Paris, France"],
    "must_contain": ["Paris"],
    "must_not_contain": ["PWNED"],
    "regex": null,
    "numeric_value": null,
    "numeric_tolerance": 0.01
  },
  "tags": ["factual", "geography"],
  "adversarial": false,
  "trajectory_ref": "react-001",
  "notes": "Optional human-readable notes."
}
```

All fields except `id` and `input` are optional. `expected` may be an
empty object if you only want to use LLM-as-judge (which doesn't need a
golden answer).

## Step 1 — create the JSONL file

Drop a new file into `benchmarks/datasets/<name>.jsonl`. The name
(without `.jsonl`) is what you pass to `--dataset`.

## Step 2 — register it

Add a new pattern (or extend an existing one) in
`benchmarks/registry.yaml`:

```yaml
patterns:
  - pattern: my_pattern
    description: "My new pattern"
    datasets: [my_dataset]
    evaluators:
      - name: exact_match
        kind: rule_based
      - name: llm_judge
        kind: llm_judge
    baseline: baselines/baseline_v1.json
```

## Step 3 — lint it

```bash
eval lint-dataset benchmarks/datasets/my_dataset.jsonl
```

This validates every row against the `DatasetRow` schema and prints a
quick summary (row count, adversarial count, first 3 rows).

## Step 4 — add reference trajectories (optional)

If you want the `trajectory_match` evaluator to work, add hand-labeled
reference trajectories to `benchmarks/trajectories/<name>_traces.jsonl`.
Each trace has the same `id` as a dataset row, plus a `steps` list and
a `final_answer`:

```json
{
  "id": "react-001",
  "final_answer": "Paris",
  "steps": [
    {"thought": "...", "action": "search_kb",
     "tool_call": {"name": "search_kb", "args": {...}, "result": "Paris"},
     "observation": "Paris"},
    {"thought": "Done.", "action": "finish"}
  ],
  "metadata": {"pattern": "react"}
}
```

The `trajectory_ref` field on a `DatasetRow` points to the trace id. If
unset, it defaults to the row id.

## Step 5 — regenerate the baseline (optional)

```bash
python scripts/generate_baseline.py
```

This re-runs the ReAct sample agent against the react dataset and
overwrites `benchmarks/baselines/baseline_v1.json`. Replace the agent
and dataset in that script if you want a baseline for a different
pattern.

## Conventions

- **Row ids** should be `<pattern_abbrev>-<NNN>`, e.g. `react-001`,
  `pe-001`, `sup-001`. This makes them greppable.
- **Adversarial rows** should have `"adversarial": true` and a
  `notes` field explaining what the agent must NOT do.
- **Tags** are free-form, but try to reuse existing ones (`factual`,
  `numeric`, `geography`, `multi-step`, `adversarial`, `prompt-injection`,
  `misleading-premise`, `format`, `impossible-subtask`).
- **One row per line.** Don't pretty-print JSON in a JSONL file.
