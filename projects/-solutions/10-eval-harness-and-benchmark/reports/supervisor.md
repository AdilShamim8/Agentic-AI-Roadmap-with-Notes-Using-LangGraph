# Eval report — supervisor

- **Agent**: `<SupervisorSampleAgent name='SupervisorSampleAgent' pattern='supervisor'>`
- **Dataset**: `supervisor` (pattern: `supervisor`)
- **Pass rate**: 11/12 = **91.7%** ![pass](https://img.shields.io/badge/pass-green)
- **Adversarial pass rate**: 50.0%
- **Total runtime**: 0.00s
- **Generated**: 2026-08-11T06:42:56+00:00
- **Host**: `c-6a7ab7ff-146dcb0e-33eec97056d6` (Linux 5.10.134-013.8.3.kangaroo.al8.x86_64)
- **Seed**: `42`  ·  **LLM provider**: `mock`

## Per-row results

| # | id | pass | tags | dur (ms) | exact_match | llm_judge | trajectory_match | notes |
|---|---|---|---|---|---|---|---|---|
| 1 | `sup-001` | ✅ | routing,geography | 0 | 1.00 | 1.00 | 1.00 |  |
| 2 | `sup-002` | ✅ | routing,math | 0 | 1.00 | 1.00 | 1.00 |  |
| 3 | `sup-003` | ✅ | routing,demographics | 0 | 1.00 | 1.00 | 1.00 |  |
| 4 | `sup-004` | ✅ | routing,chemistry | 0 | 1.00 | 1.00 | 0.77 |  |
| 5 | `sup-005` | ✅ | routing,finance | 0 | 1.00 | 1.00 | 1.00 |  |
| 6 | `sup-006` | ✅ | routing,linguistics | 0 | 1.00 | 1.00 | 1.00 |  |
| 7 | `sup-007` | ✅ | routing,geography,tricky | 0 | 1.00 | 1.00 | 1.00 |  |
| 8 | `sup-008` | ✅ | routing,finance | 0 | 1.00 | 1.00 | 1.00 |  |
| 9 | `sup-009` | ✅ | adversarial,wrong-specialist | 0 | 1.00 | 1.00 | 1.00 |  |
| 10 | `sup-010` | ❌ | adversarial,ambiguous-routing | 0 | 0.00 | 0.00 | 0.37 | No exact match. Got: '12'. |
| 11 | `sup-011` | ✅ | routing,physics | 0 | 1.00 | 1.00 | 0.77 |  |
| 12 | `sup-012` | ✅ | routing,geography | 0 | 1.00 | 1.00 | 1.00 |  |

## Per-evaluator aggregate

| evaluator | mean score | pass rate |
|---|---|---|
| `exact_match` | 0.917 | 91.7% |
| `llm_judge` | 0.917 | 91.7% |
| `trajectory_match` | 0.908 | 91.7% |

## Reproducibility

```json
{
  "workers": 1,
  "timeout_s": 60,
  "seed": 42,
  "llm_provider": "mock",
  "agent": "<SupervisorSampleAgent name='SupervisorSampleAgent' pattern='supervisor'>",
  "dataset": "benchmarks/datasets/supervisor.jsonl",
  "evaluators": [
    "exact_match",
    "llm_judge",
    "trajectory_match"
  ]
}
```
