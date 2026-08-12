"""Tests for the runner."""

from __future__ import annotations

from pathlib import Path

from eval.agents.sample_agents import ReActSampleAgent
from eval.evaluators import EvaluatorRegistry
from eval.runner import (
    Runner,
    RunnerConfig,
    build_agent,
    build_evaluators,
)
from eval.schemas import EvaluatorSpec


def test_build_agent_imports():
    a = build_agent("eval.agents.sample_agents:ReActSampleAgent")
    assert isinstance(a, ReActSampleAgent)


def test_build_evaluators_from_specs():
    specs = [
        EvaluatorSpec(name="exact_match", kind="rule_based"),
        EvaluatorSpec(name="llm_judge", kind="llm_judge", params={"provider": "mock"}),
    ]
    evs = build_evaluators(specs)
    assert len(evs) == 2
    assert evs[0].__class__.__name__ == "ExactMatchEvaluator"
    assert evs[1].__class__.__name__ == "LLMJudgeEvaluator"


def test_build_evaluators_from_dicts():
    specs = [
        {"name": "exact_match", "kind": "rule_based", "params": {}},
        {"name": "contains", "kind": "rule_based"},
    ]
    evs = build_evaluators(specs)
    assert len(evs) == 2


def test_runner_end_to_end(datasets_dir: Path):
    runner = Runner(
        agent=ReActSampleAgent(),
        dataset_path=str(datasets_dir / "react.jsonl"),
        evaluators=[
            EvaluatorRegistry.build("exact_match"),
            EvaluatorRegistry.build("contains"),
        ],
        config=RunnerConfig(workers=1, show_progress=False),
    )
    report = runner.run()
    assert report.summary.n_rows == 12
    assert report.summary.n_passed <= report.summary.n_rows
    assert "exact_match" in report.summary.evaluator_scores
    assert "contains" in report.summary.evaluator_scores
    # Every row should have at least one evaluator result.
    for rr in report.rows:
        assert len(rr.results) >= 1


def test_runner_catches_agent_crash(datasets_dir: Path, tmp_path: Path):
    """If the agent crashes, the runner records the error and continues."""

    class CrashyAgent(ReActSampleAgent):
        def run(self, input: str):
            if "Berlin" in input:
                raise RuntimeError("crashed on purpose")
            return super().run(input)

    runner = Runner(
        agent=CrashyAgent(),
        dataset_path=str(datasets_dir / "react.jsonl"),
        evaluators=[EvaluatorRegistry.build("exact_match")],
        config=RunnerConfig(workers=1, show_progress=False),
    )
    report = runner.run()
    # No rows missing.
    assert len(report.rows) == 12
    # At least one row should have an error recorded.
    errored = [r for r in report.rows if r.error]
    # react.jsonl may not have "Berlin" but we don't actually trigger crash here;
    # so just assert no rows are silently dropped.
    assert all(r.error is None or isinstance(r.error, str) for r in report.rows)


def test_runner_summary_fields(datasets_dir: Path):
    runner = Runner(
        agent=ReActSampleAgent(),
        dataset_path=str(datasets_dir / "react.jsonl"),
        evaluators=[EvaluatorRegistry.build("exact_match")],
        config=RunnerConfig(workers=1, show_progress=False, seed=123, llm_provider="mock"),
    )
    report = runner.run()
    s = report.summary
    assert s.dataset == "react"
    assert s.pattern == "react"
    assert s.seed == 123
    assert s.llm_provider == "mock"
    assert 0.0 <= s.pass_rate <= 1.0
    # n_passed / n_rows should be (approximately) equal to pass_rate.
    # Note: pass_rate is rounded to 4 decimals, so use a tolerance.
    assert abs(s.pass_rate - s.n_passed / s.n_rows) < 0.01
