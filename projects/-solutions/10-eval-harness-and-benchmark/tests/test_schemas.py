"""Tests for the Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eval.schemas import (
    AgentOutput,
    DatasetRow,
    ExpectedOutput,
    PatternEntry,
    ToolCall,
    Trajectory,
    TrajectoryStep,
)


def test_dataset_row_minimal():
    row = DatasetRow(id="x-001", input="hi")
    assert row.id == "x-001"
    assert row.input == "hi"
    assert row.adversarial is False
    assert row.expected.answer is None
    assert row.tags == []


def test_dataset_row_with_expected():
    row = DatasetRow(
        id="x-002",
        input="What is the capital of France?",
        expected={"answer": "Paris", "must_contain": ["Paris"]},
    )
    assert row.expected.answer == "Paris"
    assert row.expected.must_contain == ["Paris"]


def test_dataset_row_requires_id_and_input():
    with pytest.raises(ValidationError):
        DatasetRow()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        DatasetRow(id="x")  # type: ignore[call-arg]


def test_expected_output_extra_fields_allowed():
    """ExpectedOutput allows extra fields so users can add custom hints."""

    e = ExpectedOutput(answer="42", custom_hint="accept any number")
    assert e.answer == "42"
    assert e.model_dump().get("custom_hint") == "accept any number"


def test_agent_output_with_trajectory():
    out = AgentOutput(
        answer="Paris",
        trajectory=Trajectory(
            steps=[
                TrajectoryStep(
                    thought="think",
                    tool_call=ToolCall(name="search", args={"q": "x"}, result="Paris"),
                )
            ]
        ),
    )
    assert out.answer == "Paris"
    assert len(out.trajectory.steps) == 1
    assert out.trajectory.steps[0].tool_call.name == "search"


def test_eval_result_score_range():
    """EvalResult.score must be in [0, 1]."""

    from eval.schemas import EvalResult

    EvalResult(evaluator="x", row_id="r", passed=True, score=0.0)
    EvalResult(evaluator="x", row_id="r", passed=True, score=1.0)
    with pytest.raises(ValidationError):
        EvalResult(evaluator="x", row_id="r", passed=True, score=1.5)
    with pytest.raises(ValidationError):
        EvalResult(evaluator="x", row_id="r", passed=True, score=-0.1)


def test_pattern_entry_roundtrip():
    p = PatternEntry(
        pattern="react",
        datasets=["react"],
        evaluators=[{"name": "exact_match", "kind": "rule_based"}],
    )
    assert p.pattern == "react"
    assert p.evaluators[0].name == "exact_match"
