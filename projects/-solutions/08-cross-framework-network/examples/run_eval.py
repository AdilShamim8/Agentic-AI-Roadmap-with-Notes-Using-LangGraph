#!/usr/bin/env python
"""
Run the full evaluation locally.

Starts both A2A agent servers in background threads, then runs the
evaluation dataset through the supervisor and prints the metrics.

Usage::

    python -m examples.run_eval           # full eval (20 tasks)
    python -m examples.run_eval --limit 5 # first 5 tasks
"""

from __future__ import annotations

import argparse
import asyncio
import logging
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
from eval.runner import run_eval


def _start_server(server, name: str) -> threading.Thread:
    config = uvicorn.Config(server.app, host=server.host, port=server.port, log_level="warning")
    instance = uvicorn.Server(config)

    def _run():
        asyncio.run(instance.serve())

    t = threading.Thread(target=_run, daemon=True, name=name)
    t.start()
    return t


async def _wait(url: str, timeout: float = 10.0) -> bool:
    from a2a.client import A2AClient

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            async with A2AClient(url) as c:
                await c.get_agent_card()
                return True
        except Exception:
            await asyncio.sleep(0.3)
    return False


async def main(limit: int | None) -> None:
    # Start agents
    rs = build_a2a_server(research_card(), ResearchAgentExecutor(), port=8001)
    ws = build_a2a_server(writer_card(), WriterCrewExecutor(), port=8002)
    _start_server(rs, "research")
    _start_server(ws, "writer")

    if not await _wait("http://localhost:8001"):
        raise RuntimeError("Research agent failed to start")
    if not await _wait("http://localhost:8002"):
        raise RuntimeError("Writer crew failed to start")

    print("Both agents ready. Starting evaluation...\n")
    await run_eval(limit=limit, verbose=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(main(args.limit))
