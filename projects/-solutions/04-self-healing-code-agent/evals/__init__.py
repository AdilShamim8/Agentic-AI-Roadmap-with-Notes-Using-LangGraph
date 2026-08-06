"""Evaluation harness for the self-healing agent.

Runs the agent over a directory of fixture cases, computes the rubric metrics
(pass rate, no-regression rate, cost per patch, trajectory efficiency), and
prints a report.
"""

from evals.metrics import EvalMetrics, aggregate
from evals.runner import CaseResult, EvalRunner, discover_cases

__all__ = [
    "CaseResult",
    "EvalMetrics",
    "EvalRunner",
    "aggregate",
    "discover_cases",
]
