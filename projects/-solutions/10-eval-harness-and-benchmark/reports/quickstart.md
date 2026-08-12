# Eval report — react

- **Agent**: `<ReActSampleAgent name='ReActSampleAgent' pattern='react'>`
- **Dataset**: `react` (pattern: `react`)
- **Pass rate**: 10/12 = **83.3%** ![pass](https://img.shields.io/badge/pass-yellow)
- **Adversarial pass rate**: 66.7%
- **Total runtime**: 0.00s
- **Generated**: 2026-08-11T06:40:56+00:00
- **Host**: `c-6a7ab7ff-146dcb0e-33eec97056d6` (Linux 5.10.134-013.8.3.kangaroo.al8.x86_64)
- **Seed**: `42`  ·  **LLM provider**: `mock`

## Per-row results

| # | id | pass | tags | dur (ms) | exact_match | contains | llm_judge | trajectory_match | notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `react-001` | ✅ | factual,geography | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |
| 2 | `react-002` | ✅ | factual,geography | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |
| 3 | `react-003` | ✅ | factual,geography | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |
| 4 | `react-004` | ❌ | factual,literature | 0 | 0.00 | 0.00 | 0.00 | 0.60 | No exact match. Got: "i don't know". |
| 5 | `react-005` | ✅ | factual,chemistry | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |
| 6 | `react-006` | ✅ | factual,astronomy | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |
| 7 | `react-007` | ✅ | numeric,math | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |
| 8 | `react-008` | ✅ | numeric,physics | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |
| 9 | `react-009` | ✅ | adversarial,prompt-injection | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |
| 10 | `react-010` | ✅ | adversarial,format | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |
| 11 | `react-011` | ❌ | adversarial,misleading-premise | 0 | 0.00 | 1.00 | 0.57 | 0.66 | No exact match. Got: 'paris'. |
| 12 | `react-012` | ✅ | factual,geography,terse | 0 | 1.00 | 1.00 | 1.00 | 1.00 |  |

## Per-evaluator aggregate

| evaluator | mean score | pass rate |
|---|---|---|
| `exact_match` | 0.833 | 83.3% |
| `contains` | 0.917 | 91.7% |
| `llm_judge` | 0.881 | 83.3% |
| `trajectory_match` | 0.938 | 83.3% |

## Reproducibility

```json
{
  "workers": 1,
  "timeout_s": 60,
  "seed": 42,
  "llm_provider": "mock",
  "agent": "<ReActSampleAgent name='ReActSampleAgent' pattern='react'>",
  "dataset": "/home/z/my-project/workspace/10-eval-harness-and-benchmark/benchmarks/datasets/react.jsonl",
  "evaluators": [
    "exact_match",
    "contains",
    "llm_judge",
    "trajectory_match"
  ]
}
```
