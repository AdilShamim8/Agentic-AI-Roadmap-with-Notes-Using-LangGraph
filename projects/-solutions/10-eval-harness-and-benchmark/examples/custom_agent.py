"""Plug in your own agent.

This example shows how to wrap any agent (LangGraph, OpenAI Agents SDK,
CrewAI, or plain Python) in a `BaseAgent` so the harness can evaluate it.

Run:
    python examples/custom_agent.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EVAL_LLM_PROVIDER", "mock")
os.environ.setdefault("EVAL_PROJECT_ROOT", str(ROOT))

from eval.agents.base import BaseAgent  # noqa: E402
from eval.config import get_settings  # noqa: E402
from eval.evaluators import EvaluatorRegistry  # noqa: E402
from eval.reporter import write_report  # noqa: E402
from eval.runner import Runner, RunnerConfig  # noqa: E402
from eval.schemas import AgentOutput, ToolCall, Trajectory, TrajectoryStep  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Define your agent.
#
#    Subclass `BaseAgent` and implement `run(input) -> AgentOutput`.
#    You can do *anything* inside `run` — call an LLM, hit a tool, query a
#    database. The harness only cares that you return an `AgentOutput` with
#    at least `.answer` populated.
# ---------------------------------------------------------------------------


class MyCustomAgent(BaseAgent):
    """A toy agent that just uppercases the input.

    Replace the body of `run` with whatever your real agent does.
    """

    name = "MyCustomAgent"
    pattern = "react"  # tells the registry which datasets to suggest

    def run(self, input: str) -> AgentOutput:
        # Pretend this is a LangGraph call:
        answer = input.upper()

        # Build a trajectory so trajectory evaluators can run:
        steps = [
            TrajectoryStep(
                thought="I'll uppercase the input.",
                action="uppercase",
                tool_call=ToolCall(
                    name="uppercase",
                    args={"text": input},
                    result=answer,
                ),
                observation=answer,
            ),
            TrajectoryStep(thought="Done.", action="finish"),
        ]
        return AgentOutput(
            answer=answer,
            trajectory=Trajectory(steps=steps, metadata={"pattern": "custom"}),
            metadata={"agent_version": "0.1.0"},
        )


# ---------------------------------------------------------------------------
# 2. Run the harness against it.
# ---------------------------------------------------------------------------


def main() -> None:
    settings = get_settings()

    runner = Runner(
        agent=MyCustomAgent(),
        dataset_path=str(settings.datasets_dir / "react.jsonl"),
        evaluators=[
            EvaluatorRegistry.build("exact_match"),
            EvaluatorRegistry.build("contains"),
        ],
        config=RunnerConfig(workers=1, show_progress=False, seed=42, llm_provider="mock"),
    )

    report = runner.run()
    md, _ = write_report(report, settings.report_dir / "custom_agent.md")

    s = report.summary
    print(f"\n  Agent:      {s.agent}")
    print(f"  Pass rate:  {s.pass_rate * 100:.1f}% ({s.n_passed}/{s.n_rows})")
    print(f"  Report:     {md}")
    print("\n  (A 0% pass rate is expected — the agent just uppercases input!)")


if __name__ == "__main__":
    main()
