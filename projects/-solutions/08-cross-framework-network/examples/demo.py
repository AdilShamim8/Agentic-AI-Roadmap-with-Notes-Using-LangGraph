#!/usr/bin/env python
"""
Quick demo — runs the full cross-framework network on a sample task.

This script:
    1. Starts both A2A agent servers in background threads (in-process).
    2. Runs the LangGraph supervisor on a sample task.
    3. Prints the result and interop metrics.

No external services or API keys required — uses the mock LLM by default.

Usage::

    python -m examples.demo
    python -m examples.demo --task "Your custom task"
    python -m examples.demo --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import threading
import time

import uvicorn

from agents.crewai_writer.server import (
    WriterCrewExecutor,
    get_agent_card as writer_card,
)
from agents.openai_research.server import (
    ResearchAgentExecutor,
    get_agent_card as research_card,
)
from agents.shared import build_a2a_server
from supervisor.graph import SupervisorGraph

logger = logging.getLogger(__name__)


def _start_server_in_thread(server, name: str) -> threading.Thread:
    """Start a uvicorn server in a background thread."""
    config = uvicorn.Config(
        server.app,
        host=server.host,
        port=server.port,
        log_level="warning",  # reduce noise
    )
    instance = uvicorn.Server(config)

    def _run():
        asyncio.run(instance.serve())

    thread = threading.Thread(target=_run, daemon=True, name=name)
    thread.start()
    return thread


async def wait_for_agent(url: str, timeout: float = 10.0) -> bool:
    """Wait for an A2A agent to be ready."""
    from a2a.client import A2AClient

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            async with A2AClient(url) as client:
                await client.get_agent_card()
                return True
        except Exception:
            await asyncio.sleep(0.3)
    return False


async def run_demo(task: str, json_output: bool = False) -> dict:
    """Run the full demo."""
    # 1. Start agent servers in background threads.
    research_card_obj = research_card(base_url="http://localhost:8001")
    research_server = build_a2a_server(
        research_card_obj, ResearchAgentExecutor(), port=8001
    )
    writer_card_obj = writer_card(base_url="http://localhost:8002")
    writer_server = build_a2a_server(
        writer_card_obj, WriterCrewExecutor(), port=8002
    )

    t1 = _start_server_in_thread(research_server, "research-agent")
    t2 = _start_server_in_thread(writer_server, "writer-crew")

    # 2. Wait for agents to be ready.
    if not await wait_for_agent("http://localhost:8001"):
        raise RuntimeError("Research agent did not start")
    if not await wait_for_agent("http://localhost:8002"):
        raise RuntimeError("Writer crew did not start")
    logger.info("Both A2A agents are ready")

    # 3. Run the supervisor.
    graph = SupervisorGraph()
    state = await graph.run(task)

    # 4. Format output.
    result = {
        "task": task,
        "plan": [
            {
                "id": s.id,
                "agent": s.agent.value,
                "description": s.description,
                "status": s.status.value,
                "latency_ms": round(s.latency_ms, 1),
            }
            for s in state.plan
        ],
        "handoffs": [
            {
                "step_id": h.step_id,
                "agent": h.agent.value,
                "url": h.agent_url,
                "latency_ms": round(h.latency_ms, 1),
                "success": h.success,
            }
            for h in state.handoffs
        ],
        "final_output": state.final_output,
        "metrics": {
            "total_steps": len(state.plan),
            "completed_steps": sum(1 for s in state.plan if s.status.value == "done"),
            "total_handoffs": len(state.handoffs),
            "avg_handoff_latency_ms": round(
                sum(h.latency_ms for h in state.handoffs) / max(len(state.handoffs), 1), 1
            ),
            "final_output_length": len(state.final_output),
        },
    }
    return result


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run a quick demo of the cross-framework network")
    parser.add_argument(
        "--task",
        default="Research the A2A protocol and write a blog post about it",
        help="The task to execute",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = asyncio.run(run_demo(args.task, json_output=args.json))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\n" + "=" * 60)
        print("CROSS-FRAMEWORK NETWORK DEMO")
        print("=" * 60)
        print(f"\nTask: {result['task']}\n")
        print("-" * 60)
        print("PLAN:")
        for step in result["plan"]:
            icon = {"done": "✓", "failed": "✗", "running": "→"}.get(step["status"], "?")
            print(f"  {icon} [{step['agent']}] {step['description'][:70]}")
        print("-" * 60)
        print("A2A HANDOFFS:")
        for h in result["handoffs"]:
            print(f"  → {h['agent']} @ {h['url']}: {h['latency_ms']}ms [{'OK' if h['success'] else 'FAIL'}]")
        print("-" * 60)
        print("METRICS:")
        m = result["metrics"]
        print(f"  Steps: {m['completed_steps']}/{m['total_steps']} completed")
        print(f"  Handoffs: {m['total_handoffs']}")
        print(f"  Avg handoff latency: {m['avg_handoff_latency_ms']}ms")
        print(f"  Output length: {m['final_output_length']} chars")
        print("-" * 60)
        print("\nFINAL OUTPUT:\n")
        print(result["final_output"][:2000])
        if len(result["final_output"]) > 2000:
            print(f"\n... ({len(result['final_output']) - 2000} more chars)")
        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
