"""Quickstart - run the harness programmatically (no CLI).

Run:
    python examples/quickstart.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EVAL_LLM_PROVIDER", "mock")
os.environ.setdefault("EVAL_PROJECT_ROOT", str(ROOT))

from eval.agents.sample_agents import ReActSampleAgent  # noqa: E402
from eval.config import get_settings  # noqa: E402
from eval.evaluators import EvaluatorRegistry  # noqa: E402
from eval.reporter import write_report  # noqa: E402
from eval.runner import Runner, RunnerConfig  # noqa: E402


def main() -> None:
    settings = get_settings()
    dataset_path = settings.datasets_dir / "react.jsonl"

    runner = Runner(
        agent=ReActSampleAgent(),
        dataset_path=str(dataset_path),
        evaluators=[
            EvaluatorRegistry.build("exact_match"),
            EvaluatorRegistry.build("contains"),
            EvaluatorRegistry.build("llm_judge", {"provider": "mock"}),
            EvaluatorRegistry.build("trajectory_match"),
        ],
        config=RunnerConfig(workers=1, show_progress=False, seed=42, llm_provider="mock"),
    )

    report = runner.run()
    md, js = write_report(report, settings.report_dir / "quickstart.md")

    s = report.summary
    print(f"\n  Dataset:    {s.dataset}")
    print(f"  Pass rate:  {s.pass_rate * 100:.1f}% ({s.n_passed}/{s.n_rows})")
    print(f"  Evaluators: {list(s.evaluator_scores)}")
    print(f"  Report:     {md}")
    print(f"  JSON:       {js}")


if __name__ == "__main__":
    main()
