"""Add your own evaluator.

This example shows how to subclass `BaseEvaluator`, register it, and use
it in a run. The evaluator we add here checks whether the agent's answer
contains a URL (a common requirement for grounded QA agents).

Run:
    python examples/custom_evaluator.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EVAL_LLM_PROVIDER", "mock")
os.environ.setdefault("EVAL_PROJECT_ROOT", str(ROOT))

from eval.agents.sample_agents import ReActSampleAgent  # noqa: E402
from eval.config import get_settings  # noqa: E402
from eval.evaluators import EvaluatorRegistry  # noqa: E402
from eval.evaluators.base import BaseEvaluator  # noqa: E402
from eval.reporter import write_report  # noqa: E402
from eval.runner import Runner, RunnerConfig  # noqa: E402
from eval.schemas import AgentOutput, DatasetRow, EvalResult, Trajectory  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Subclass BaseEvaluator.
# ---------------------------------------------------------------------------


class ContainsUrlEvaluator(BaseEvaluator):
    """Pass iff the answer contains at least one http(s) URL."""

    name = "contains_url"

    _URL_RE = re.compile(r"https?://[^\s)]+", re.IGNORECASE)

    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        text = str(output.answer or "")
        matches = self._URL_RE.findall(text)
        passed = len(matches) >= 1
        return EvalResult(
            evaluator=self.display_name(),
            row_id=row.id,
            passed=passed,
            score=1.0 if passed else 0.0,
            rationale=(
                f"Found {len(matches)} URL(s)."
                if passed
                else "No URL found in answer."
            ),
            details={"urls": matches},
        )


# ---------------------------------------------------------------------------
# 2. Register it.
# ---------------------------------------------------------------------------


EvaluatorRegistry.register("contains_url", ContainsUrlEvaluator)


# ---------------------------------------------------------------------------
# 3. Use it.
# ---------------------------------------------------------------------------


def main() -> None:
    settings = get_settings()

    runner = Runner(
        agent=ReActSampleAgent(),
        dataset_path=str(settings.datasets_dir / "react.jsonl"),
        evaluators=[
            EvaluatorRegistry.build("exact_match"),
            EvaluatorRegistry.build("contains_url"),  # <-- our new one
        ],
        config=RunnerConfig(workers=1, show_progress=False, seed=42, llm_provider="mock"),
    )

    report = runner.run()
    md, _ = write_report(report, settings.report_dir / "custom_evaluator.md")

    s = report.summary
    print(f"\n  Agent:      {s.agent}")
    print(f"  Pass rate:  {s.pass_rate * 100:.1f}% ({s.n_passed}/{s.n_rows})")
    print(f"  Evaluators: {list(s.evaluator_scores)}")
    print(f"  Report:     {md}")
    print("\n  (contains_url will be 0% — ReActSampleAgent never emits URLs.)")


if __name__ == "__main__":
    main()
