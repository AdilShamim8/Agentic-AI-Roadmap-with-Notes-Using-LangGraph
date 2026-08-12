# Eval report — swarm

- **Agent**: `<SwarmSampleAgent name='SwarmSampleAgent' pattern='swarm'>`
- **Dataset**: `swarm` (pattern: `swarm`)
- **Pass rate**: 3/12 = **25.0%** ![pass](https://img.shields.io/badge/pass-red)
- **Adversarial pass rate**: 50.0%
- **Total runtime**: 0.00s
- **Generated**: 2026-08-11T06:42:57+00:00
- **Host**: `c-6a7ab7ff-146dcb0e-33eec97056d6` (Linux 5.10.134-013.8.3.kangaroo.al8.x86_64)
- **Seed**: `42`  ·  **LLM provider**: `mock`

## Per-row results

| # | id | pass | tags | dur (ms) | contains | llm_judge | trajectory_match | notes |
|---|---|---|---|---|---|---|---|---|
| 1 | `swm-001` | ✅ | swarm,geography | 0 | 1.00 | 1.00 | 1.00 |  |
| 2 | `swm-002` | ✅ | swarm,math | 0 | 1.00 | 1.00 | 1.00 |  |
| 3 | `swm-003` | ❌ | swarm,multi-domain | 0 | 0.50 | 0.25 | 0.60 | Contained 1/2 required; forbidden hits: 0. |
| 4 | `swm-004` | ❌ | swarm,multi-domain | 0 | 0.50 | 0.50 | 0.80 | Contained 1/2 required; forbidden hits: 0. |
| 5 | `swm-005` | ❌ | swarm,multi-domain | 0 | 0.50 | 0.25 | 0.60 | Contained 1/2 required; forbidden hits: 0. |
| 6 | `swm-006` | ❌ | swarm,multi-domain | 0 | 0.50 | 0.25 | 0.60 | Contained 1/2 required; forbidden hits: 0. |
| 7 | `swm-007` | ❌ | swarm,multi-domain | 0 | 0.50 | 0.42 | 0.76 | Contained 1/2 required; forbidden hits: 0. |
| 8 | `swm-008` | ❌ | swarm,multi-domain,physics | 0 | 0.50 | 0.45 | 0.76 | Contained 1/2 required; forbidden hits: 0. |
| 9 | `swm-009` | ✅ | adversarial,conflicting-instructions | 0 | 1.00 | 1.00 | 1.00 |  |
| 10 | `swm-010` | ❌ | adversarial,specialist-isolation | 0 | 0.00 | 0.00 | 0.60 | Contained 0/1 required; forbidden hits: 0. |
| 11 | `swm-011` | ❌ | swarm,multi-domain,triple | 0 | 0.33 | 0.17 | 0.60 | Contained 1/3 required; forbidden hits: 0. |
| 12 | `swm-012` | ❌ | swarm,multi-domain | 0 | 0.50 | 0.38 | 0.70 | Contained 1/2 required; forbidden hits: 0. |

## Per-evaluator aggregate

| evaluator | mean score | pass rate |
|---|---|---|
| `contains` | 0.569 | 25.0% |
| `llm_judge` | 0.472 | 25.0% |
| `trajectory_match` | 0.752 | 58.3% |

## Reproducibility

```json
{
  "workers": 1,
  "timeout_s": 60,
  "seed": 42,
  "llm_provider": "mock",
  "agent": "<SwarmSampleAgent name='SwarmSampleAgent' pattern='swarm'>",
  "dataset": "benchmarks/datasets/swarm.jsonl",
  "evaluators": [
    "contains",
    "llm_judge",
    "trajectory_match"
  ]
}
```
