"""Tests for the reporter."""

from __future__ import annotations

import json
from pathlib import Path

from eval.agents.sample_agents import ReActSampleAgent
from eval.evaluators import EvaluatorRegistry
from eval.reporter import diff_against_baseline, render_json, render_markdown, write_report
from eval.runner import Runner, RunnerConfig


def _make_report(datasets_dir: Path):
    runner = Runner(
        agent=ReActSampleAgent(),
        dataset_path=str(datasets_dir / "react.jsonl"),
        evaluators=[EvaluatorRegistry.build("exact_match")],
        config=RunnerConfig(workers=1, show_progress=False, seed=42),
    )
    return runner.run()


def test_render_markdown_has_sections(datasets_dir: Path):
    report = _make_report(datasets_dir)
    md = render_markdown(report)
    assert "# Eval report" in md
    assert "## Per-row results" in md
    assert "## Per-evaluator aggregate" in md
    assert "## Reproducibility" in md
    assert "react" in md


def test_render_json_is_parseable(datasets_dir: Path):
    report = _make_report(datasets_dir)
    js = render_json(report)
    data = json.loads(js)
    assert data["summary"]["dataset"] == "react"
    assert data["summary"]["n_rows"] == 12
    assert len(data["rows"]) == 12


def test_write_report_creates_files(datasets_dir: Path, tmp_path: Path):
    report = _make_report(datasets_dir)
    md_path = tmp_path / "out" / "r.md"
    md, js = write_report(report, md_path)
    assert md.exists()
    assert js.exists()
    assert md.read_text(encoding="utf-8").startswith("# Eval report")
    json.loads(js.read_text(encoding="utf-8"))


def test_diff_against_baseline(datasets_dir: Path):
    """The diff should produce a dict keyed by metric name."""

    report = _make_report(datasets_dir)
    # Use the precomputed baseline.
    baseline = Path(__file__).resolve().parents[1] / "benchmarks" / "baselines" / "baseline_v1.json"
    diff = diff_against_baseline(report, baseline)
    assert "pass_rate" in diff
    assert "exact_match" in diff


def test_report_reproducible(datasets_dir: Path):
    """Same agent + dataset + seed -> identical summary."""

    r1 = _make_report(datasets_dir)
    r2 = _make_report(datasets_dir)
    assert r1.summary.pass_rate == r2.summary.pass_rate
    assert r1.summary.evaluator_scores == r2.summary.evaluator_scores
