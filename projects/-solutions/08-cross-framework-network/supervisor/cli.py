#!/usr/bin/env python
"""
Supervisor CLI — run the LangGraph supervisor from the command line.

Usage::

    python -m supervisor.cli "Research and write about multi-agent AI systems"

    # With custom agent URLs:
    RESEARCH_AGENT_URL=http://research:8001 WRITING_AGENT_URL=http://writer:8002 \
        python -m supervisor.cli "Your task here"

    # Save output to a file:
    python -m supervisor.cli "Your task" --output result.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from supervisor.graph import SupervisorGraph


def format_summary(state) -> str:
    """Format a human-readable summary of the supervisor run."""
    lines = [
        "\n" + "=" * 60,
        "SUPERVISOR RUN SUMMARY",
        "=" * 60,
        f"Task: {state.task}",
        f"Steps: {len(state.plan)}",
        f"Handoffs: {len(state.handoffs)}",
        f"Iterations: {state.iteration}",
        "",
        "Plan:",
    ]
    for step in state.plan:
        status_icon = {"done": "✓", "failed": "✗", "skipped": "⊘"}.get(
            step.status.value, "→"
        )
        lines.append(
            f"  {status_icon} [{step.agent.value}] {step.description[:80]}"
            f" ({step.latency_ms:.0f}ms)"
        )

    if state.handoffs:
        lines.append("")
        lines.append("A2A Handoffs:")
        for h in state.handoffs:
            status = "OK" if h.success else f"FAIL: {h.error}"
            lines.append(
                f"  step {h.step_id} → {h.agent.value} @ {h.agent_url}: "
                f"{h.latency_ms:.0f}ms [{status}]"
            )

        total_latency = sum(h.latency_ms for h in state.handoffs)
        avg_latency = total_latency / len(state.handoffs)
        lines.append("")
        lines.append(f"Total handoff latency: {total_latency:.0f}ms")
        lines.append(f"Average handoff latency: {avg_latency:.0f}ms")

    lines.append("")
    lines.append(f"Final output: {len(state.final_output)} chars")
    lines.append("=" * 60)
    return "\n".join(lines)


async def run(task: str, output_file: str | None, json_output: bool) -> int:
    """Run the supervisor and print/save results."""
    graph = SupervisorGraph()
    state = await graph.run(task)

    if json_output:
        output = {
            "task": state.task,
            "plan": [
                {
                    "id": s.id,
                    "description": s.description,
                    "agent": s.agent.value,
                    "status": s.status.value,
                    "latency_ms": s.latency_ms,
                }
                for s in state.plan
            ],
            "handoffs": [
                {
                    "step_id": h.step_id,
                    "agent": h.agent.value,
                    "latency_ms": h.latency_ms,
                    "success": h.success,
                }
                for h in state.handoffs
            ],
            "final_output": state.final_output,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_summary(state))
        print("\n--- FINAL OUTPUT ---\n")
        print(state.final_output)

    if output_file:
        with open(output_file, "w") as f:
            f.write(state.final_output)
        logging.info("Output saved to %s", output_file)

    return 0 if not state.has_failures() else 1


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Run the LangGraph supervisor on a task"
    )
    parser.add_argument("task", help="The task to execute")
    parser.add_argument(
        "--output", "-o", help="Save final output to this file"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    args = parser.parse_args()

    exit_code = asyncio.run(run(args.task, args.output, args.json))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
