# Eval report — map_reduce

- **Agent**: `<MapReduceSampleAgent name='MapReduceSampleAgent' pattern='map_reduce'>`
- **Dataset**: `map_reduce` (pattern: `map_reduce`)
- **Pass rate**: 0/12 = **0.0%** ![pass](https://img.shields.io/badge/pass-red)
- **Adversarial pass rate**: 0.0%
- **Total runtime**: 0.00s
- **Generated**: 2026-08-11T06:42:57+00:00
- **Host**: `c-6a7ab7ff-146dcb0e-33eec97056d6` (Linux 5.10.134-013.8.3.kangaroo.al8.x86_64)
- **Seed**: `42`  ·  **LLM provider**: `mock`

## Per-row results

| # | id | pass | tags | dur (ms) | contains | llm_judge | trajectory_match | notes |
|---|---|---|---|---|---|---|---|---|
| 1 | `mr-001` | ❌ | map-reduce,geography | 0 | 0.00 | 0.00 | 0.60 | Contained 0/3 required; forbidden hits: 0. |
| 2 | `mr-002` | ❌ | map-reduce,geography | 0 | 0.00 | 0.00 | 0.60 | Contained 0/2 required; forbidden hits: 0. |
| 3 | `mr-003` | ❌ | map-reduce,finance | 0 | 0.33 | 0.17 | 0.60 | Contained 1/3 required; forbidden hits: 0. |
| 4 | `mr-004` | ❌ | map-reduce,chemistry | 0 | 0.00 | 0.00 | 0.60 | Contained 0/3 required; forbidden hits: 0. |
| 5 | `mr-005` | ❌ | map-reduce,linguistics | 0 | 0.00 | 0.00 | 0.60 | Contained 0/2 required; forbidden hits: 0. |
| 6 | `mr-006` | ❌ | map-reduce,geography | 0 | 0.00 | 0.00 | 0.60 | Contained 0/2 required; forbidden hits: 0. |
| 7 | `mr-007` | ❌ | map-reduce,demographics | 0 | 0.00 | 0.00 | 0.60 | Contained 0/2 required; forbidden hits: 0. |
| 8 | `mr-008` | ❌ | map-reduce,geography | 0 | 0.00 | 0.00 | 0.60 | Contained 0/2 required; forbidden hits: 0. |
| 9 | `mr-009` | ❌ | adversarial,impossible-item | 0 | 0.00 | 0.00 | 0.60 | Contained 0/2 required; forbidden hits: 0. |
| 10 | `mr-010` | ❌ | adversarial,duplicates | 0 | 0.00 | 0.00 | 0.60 | Contained 0/1 required; forbidden hits: 0. |
| 11 | `mr-011` | ❌ | map-reduce,math | 0 | 0.00 | 0.00 | 0.60 | Contained 0/2 required; forbidden hits: 0. |
| 12 | `mr-012` | ❌ | map-reduce,geography,quad | 0 | 0.00 | 0.00 | 0.60 | Contained 0/4 required; forbidden hits: 0. |

## Per-evaluator aggregate

| evaluator | mean score | pass rate |
|---|---|---|
| `contains` | 0.028 | 0.0% |
| `llm_judge` | 0.014 | 0.0% |
| `trajectory_match` | 0.600 | 0.0% |

## Reproducibility

```json
{
  "workers": 1,
  "timeout_s": 60,
  "seed": 42,
  "llm_provider": "mock",
  "agent": "<MapReduceSampleAgent name='MapReduceSampleAgent' pattern='map_reduce'>",
  "dataset": "benchmarks/datasets/map_reduce.jsonl",
  "evaluators": [
    "contains",
    "llm_judge",
    "trajectory_match"
  ]
}
```
