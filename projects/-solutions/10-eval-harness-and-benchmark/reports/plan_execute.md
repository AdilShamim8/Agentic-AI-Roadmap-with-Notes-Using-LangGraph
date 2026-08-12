# Eval report — plan_execute

- **Agent**: `<PlanExecuteSampleAgent name='PlanExecuteSampleAgent' pattern='plan_execute'>`
- **Dataset**: `plan_execute` (pattern: `plan_execute`)
- **Pass rate**: 5/12 = **41.7%** ![pass](https://img.shields.io/badge/pass-red)
- **Adversarial pass rate**: 33.3%
- **Total runtime**: 0.00s
- **Generated**: 2026-08-11T06:42:56+00:00
- **Host**: `c-6a7ab7ff-146dcb0e-33eec97056d6` (Linux 5.10.134-013.8.3.kangaroo.al8.x86_64)
- **Seed**: `42`  ·  **LLM provider**: `mock`

## Per-row results

| # | id | pass | tags | dur (ms) | contains | llm_judge | trajectory_match | notes |
|---|---|---|---|---|---|---|---|---|
| 1 | `pe-001` | ✅ | multi-step,geography | 0 | 1.00 | 1.00 | 1.00 |  |
| 2 | `pe-002` | ✅ | multi-step,geography | 0 | 1.00 | 1.00 | 1.00 |  |
| 3 | `pe-003` | ❌ | multi-step,demographics | 0 | 0.00 | 0.00 | 0.70 | Contained 0/2 required; forbidden hits: 0. |
| 4 | `pe-004` | ❌ | multi-step,chemistry | 0 | 0.00 | 0.00 | 0.70 | Contained 0/2 required; forbidden hits: 0. |
| 5 | `pe-005` | ✅ | multi-step,geography | 0 | 1.00 | 1.00 | 1.00 |  |
| 6 | `pe-006` | ❌ | multi-step,literature | 0 | 0.00 | 0.00 | 0.62 | Contained 0/2 required; forbidden hits: 0. |
| 7 | `pe-007` | ✅ | multi-step,math | 0 | 1.00 | 1.00 | 1.00 |  |
| 8 | `pe-008` | ❌ | multi-step,astronomy | 0 | 0.00 | 0.00 | 0.70 | Contained 0/2 required; forbidden hits: 0. |
| 9 | `pe-009` | ❌ | adversarial,partial-decomposition | 0 | 1.00 | 0.50 | 0.57 | Mock judge: insufficient token overlap with expected answer. |
| 10 | `pe-010` | ❌ | adversarial,impossible-subtask | 0 | 1.00 | 0.54 | 0.76 | Mock judge: insufficient token overlap with expected answer. |
| 11 | `pe-011` | ✅ | adversarial,redundant-subtask | 0 | 1.00 | 1.00 | 1.00 |  |
| 12 | `pe-012` | ❌ | multi-step,geography,triple | 0 | 0.33 | 0.25 | 0.80 | Contained 1/3 required; forbidden hits: 0. |

## Per-evaluator aggregate

| evaluator | mean score | pass rate |
|---|---|---|
| `contains` | 0.611 | 58.3% |
| `llm_judge` | 0.524 | 41.7% |
| `trajectory_match` | 0.821 | 83.3% |

## Reproducibility

```json
{
  "workers": 1,
  "timeout_s": 60,
  "seed": 42,
  "llm_provider": "mock",
  "agent": "<PlanExecuteSampleAgent name='PlanExecuteSampleAgent' pattern='plan_execute'>",
  "dataset": "benchmarks/datasets/plan_execute.jsonl",
  "evaluators": [
    "contains",
    "llm_judge",
    "trajectory_match"
  ]
}
```
