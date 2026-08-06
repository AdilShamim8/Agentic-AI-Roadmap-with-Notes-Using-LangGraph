"""Unit tests for the eval metrics aggregator."""

from __future__ import annotations

import pytest

from evals.metrics import aggregate
from evals.runner import CaseResult


def _cr(
    name: str, *, passed: bool = True, no_reg: bool = True, llm: int = 5, cost: float = 0.1
) -> CaseResult:
    return CaseResult(
        name=name,
        target_test="t",
        passed=passed,
        no_regression=no_reg,
        iterations=1,
        llm_calls=llm,
        cost_usd=cost,
        status="passed" if passed else "failed",
    )


def test_aggregate_empty() -> None:
    m = aggregate([])
    assert m.n_cases == 0
    assert m.pass_rate == 0.0


def test_aggregate_all_pass() -> None:
    results = [_cr("c1"), _cr("c2"), _cr("c3")]
    m = aggregate(results)
    assert m.n_cases == 3
    assert m.n_passed == 3
    assert m.pass_rate == 1.0
    assert m.no_regression_rate == 1.0
    assert m.cost_per_patch_usd == pytest.approx(0.1)
    assert m.median_llm_calls == 5


def test_aggregate_mixed() -> None:
    results = [
        _cr("c1", passed=True, no_reg=True, llm=4, cost=0.2),
        _cr("c2", passed=True, no_reg=False, llm=8, cost=0.5),
        _cr("c3", passed=False, no_reg=False, llm=12, cost=0.9),
    ]
    m = aggregate(results)
    assert m.n_cases == 3
    assert m.n_passed == 2
    assert m.pass_rate == 2 / 3
    assert m.n_no_regression == 1
    assert m.no_regression_rate == 0.5  # 1 of 2 passed
    # cost_per_patch = total spend (incl. failed) / n_passed — penalizes waste.
    assert m.cost_per_patch_usd == pytest.approx((0.2 + 0.5 + 0.9) / 2)
    assert m.median_llm_calls == 8  # median of [4, 8, 12]
    assert m.total_cost_usd == pytest.approx(1.6)


def test_aggregate_none_passed() -> None:
    results = [_cr("c1", passed=False), _cr("c2", passed=False)]
    m = aggregate(results)
    assert m.n_passed == 0
    assert m.pass_rate == 0.0
    assert m.no_regression_rate == 0.0
    assert m.cost_per_patch_usd == 0.0
