"""Pydantic schemas for the eval harness.

These models are the contract between the runner, the evaluators, and the
reporter. They are deliberately permissive (most fields are optional) so
that real-world agents — which rarely produce clean structured output — can
still be evaluated without a thousand KeyError surprises.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Inputs / golden data
# ---------------------------------------------------------------------------


class ExpectedOutput(BaseModel):
    """The expected output for a dataset row.

    Only `answer` is required. Everything else is optional metadata that
    evaluators may or may not use.
    """

    model_config = ConfigDict(extra="allow")

    answer: str | dict[str, Any] | list[Any] | None = Field(
        default=None,
        description="The canonical answer. May be a string, a JSON object, or a list.",
    )
    allowed_answers: list[str] | None = Field(
        default=None,
        description="Alternative acceptable answers (e.g. 'Paris' / ' paris ').",
    )
    must_contain: list[str] | None = Field(
        default=None,
        description="Substrings that must appear in the agent's answer.",
    )
    must_not_contain: list[str] | None = Field(
        default=None,
        description="Substrings that must NOT appear in the agent's answer.",
    )
    regex: str | None = Field(
        default=None,
        description="A regex the agent's answer must match.",
    )
    numeric_value: float | None = Field(
        default=None,
        description="For numeric answers: the target value (compared with tolerance).",
    )
    numeric_tolerance: float = Field(
        default=0.01,
        description="Absolute tolerance for numeric comparison.",
    )


class DatasetRow(BaseModel):
    """A single row in a golden dataset.

    The shape matches the JSONL files in `benchmarks/datasets/`.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Stable row id, e.g. 'react-001'.")
    input: str = Field(..., description="The user input / task given to the agent.")
    expected: ExpectedOutput = Field(default_factory=ExpectedOutput)
    tags: list[str] = Field(default_factory=list)
    adversarial: bool = Field(
        default=False,
        description="True for adversarial cases (used in reporting).",
    )
    trajectory_ref: str | None = Field(
        default=None,
        description="If set, points to a hand-labeled reference trajectory id.",
    )
    notes: str | None = None


class Dataset(BaseModel):
    """A full dataset (a list of rows + metadata)."""

    name: str
    pattern: str
    description: str | None = None
    rows: list[DatasetRow] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent output & trajectory
# ---------------------------------------------------------------------------


class ToolCall(BaseModel):
    """A single tool call observed in the agent's trajectory."""

    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: Any | None = None
    duration_ms: float | None = None


class TrajectoryStep(BaseModel):
    """One step in an agent's execution trajectory."""

    thought: str | None = None
    action: str | None = Field(default=None, description="Human-readable action label.")
    tool_call: ToolCall | None = None
    observation: str | None = None


class Trajectory(BaseModel):
    """The full execution trajectory of a single agent run."""

    steps: list[TrajectoryStep] = Field(default_factory=list)
    total_duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    """What an agent returns from `run(input)`.

    Only `answer` is required. Trajectory is optional but heavily used by
    trajectory evaluators.
    """

    model_config = ConfigDict(extra="allow")

    answer: str | dict[str, Any] | list[Any] | None = None
    trajectory: Trajectory = Field(default_factory=Trajectory)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Eval results
# ---------------------------------------------------------------------------


class EvalResult(BaseModel):
    """The result of a single evaluator on a single row."""

    evaluator: str = Field(..., description="Evaluator name, e.g. 'exact_match'.")
    row_id: str
    passed: bool
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Continuous score in [0, 1]. 1.0 = perfect.",
    )
    rationale: str | None = Field(
        default=None,
        description="Human-readable explanation, especially for LLM judges.",
    )
    details: dict[str, Any] = Field(default_factory=dict)


class RowResult(BaseModel):
    """All evaluator results for one dataset row, plus the agent output."""

    row: DatasetRow
    output: AgentOutput
    results: list[EvalResult] = Field(default_factory=list)
    passed: bool = Field(..., description="True iff all evaluators passed.")
    duration_ms: float | None = None
    error: str | None = Field(
        default=None,
        description="If the agent crashed, the error message goes here.",
    )


class RunSummary(BaseModel):
    """Aggregate summary of a full run."""

    agent: str
    dataset: str
    pattern: str
    n_rows: int
    n_passed: int
    pass_rate: float
    evaluator_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Mean score per evaluator name.",
    )
    evaluator_pass_rates: dict[str, float] = Field(default_factory=dict)
    adversarial_pass_rate: float | None = None
    total_duration_ms: float | None = None
    seed: int | None = None
    llm_provider: str | None = None
    baseline_diff: dict[str, float] | None = Field(
        default=None,
        description="Delta vs baseline, if a baseline was supplied.",
    )


class RunReport(BaseModel):
    """The full report of a run (rows + summary)."""

    summary: RunSummary
    rows: list[RowResult] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class EvaluatorSpec(BaseModel):
    """An evaluator declaration in the registry YAML."""

    name: str
    kind: Literal["rule_based", "llm_judge", "trajectory"]
    params: dict[str, Any] = Field(default_factory=dict)


class PatternEntry(BaseModel):
    """One pattern entry in the registry."""

    pattern: str
    description: str | None = None
    datasets: list[str] = Field(default_factory=list)
    evaluators: list[EvaluatorSpec] = Field(default_factory=list)
    baseline: str | None = Field(default=None, description="Path to baseline JSON.")
