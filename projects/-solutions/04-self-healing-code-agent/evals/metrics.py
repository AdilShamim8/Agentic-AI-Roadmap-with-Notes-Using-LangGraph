"""Rubric metrics aggregation.

The 4 metrics from the project spec:

  - Pass rate:        fraction of cases whose target test now passes.
  - No-regression:    fraction of *successful* patches that didn't break other tests.
  - Cost per patch:   mean USD spent per *successful* patch.
  - Trajectory efficiency: median LLM calls per case.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from evals.runner import CaseResult


@dataclass
class EvalMetrics:
    """Aggregated rubric metrics."""

    n_cases: int = 0
    n_passed: int = 0
    n_no_regression: int = 0
    pass_rate: float = 0.0
    no_regression_rate: float = 0.0
    cost_per_patch_usd: float = 0.0
    median_llm_calls: float = 0.0
    mean_llm_calls: float = 0.0
    total_cost_usd: float = 0.0
    per_case: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "n_cases": self.n_cases,
            "n_passed": self.n_passed,
            "n_no_regression": self.n_no_regression,
            "pass_rate": round(self.pass_rate, 4),
            "no_regression_rate": round(self.no_regression_rate, 4),
            "cost_per_patch_usd": round(self.cost_per_patch_usd, 4),
            "median_llm_calls": round(self.median_llm_calls, 2),
            "mean_llm_calls": round(self.mean_llm_calls, 2),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "per_case": self.per_case,
        }


def aggregate(results: list[CaseResult]) -> EvalMetrics:
    """Compute the rubric metrics from a list of per-case results."""
    n = len(results)
    if n == 0:
        return EvalMetrics()

    passed = [r for r in results if r.passed]
    n_passed = len(passed)
    n_no_regression = sum(1 for r in passed if r.no_regression)

    llm_calls = [r.llm_calls for r in results]
    total_cost = sum(r.cost_usd for r in results)

    return EvalMetrics(
        n_cases=n,
        n_passed=n_passed,
        n_no_regression=n_no_regression,
        pass_rate=n_passed / n,
        no_regression_rate=(n_no_regression / n_passed) if n_passed else 0.0,
        cost_per_patch_usd=(total_cost / n_passed) if n_passed else 0.0,
        median_llm_calls=statistics.median(llm_calls) if llm_calls else 0.0,
        mean_llm_calls=statistics.mean(llm_calls) if llm_calls else 0.0,
        total_cost_usd=total_cost,
        per_case=[r.to_dict() for r in results],
    )
