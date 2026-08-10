"""
LangGraph-style Supervisor Graph.

Implements a state-machine supervisor that orchestrates the two A2A agents.
The graph structure is:

    START → plan → execute ↔ (loop) → synthesize → END
                        ↓
                   (no more steps → synthesize)

This mirrors a LangGraph ``StateGraph`` with conditional edges.  The
implementation is self-contained (no LangGraph dependency required) but
follows the same conceptual model.
"""

from __future__ import annotations

import logging
from typing import Any

from supervisor.a2a_adapter import A2AAdapter
from supervisor.nodes import (
    execute_node,
    plan_node,
    should_continue,
    synthesize_node,
)
from supervisor.state import SupervisorState

logger = logging.getLogger(__name__)


class SupervisorGraph:
    """
    A LangGraph-style supervisor that orchestrates A2A agents.

    Usage::

        graph = SupervisorGraph()
        result = await graph.run("Research and write about A2A protocol")
        print(result.final_output)
    """

    def __init__(
        self,
        adapter: A2AAdapter | None = None,
        max_iterations: int = 10,
    ) -> None:
        self.adapter = adapter or A2AAdapter()
        self.max_iterations = max_iterations

    async def run(self, task: str) -> SupervisorState:
        """
        Execute the supervisor graph on a user task.

        Returns the final :class:`SupervisorState` with ``final_output``
        populated.
        """
        state = SupervisorState(task=task, max_iterations=self.max_iterations)

        # Node 1: Plan
        logger.info("=" * 60)
        logger.info("SUPERVISOR: starting task: %s", task[:100])
        logger.info("=" * 60)
        update = await plan_node(state)
        state.plan = update["plan"]

        # Node 2: Execute (loop)
        while should_continue(state) == "execute":
            update = await execute_node(state, self.adapter)
            # Merge update into state.
            if "results" in update:
                state.results = update["results"]
            if "handoffs" in update:
                state.handoffs = update["handoffs"]
            state.iteration = update.get("iteration", state.iteration + 1)

        # Node 3: Synthesize
        update = await synthesize_node(state)
        state.final_output = update.get("final_output", "")

        # Cleanup
        await self.adapter.close()

        logger.info("=" * 60)
        logger.info("SUPERVISOR: completed. %d handoffs, %d chars output",
                     len(state.handoffs), len(state.final_output))
        logger.info("=" * 60)

        return state

    async def run_streaming(self, task: str):
        """
        Execute the supervisor graph, yielding state updates as they occur.

        Yields ``(node_name, state)`` tuples after each node completes.
        Useful for real-time UI updates.
        """
        state = SupervisorState(task=task, max_iterations=self.max_iterations)

        yield ("plan_start", state)
        update = await plan_node(state)
        state.plan = update["plan"]
        yield ("plan_done", state)

        while should_continue(state) == "execute":
            step = state.next_pending_step()
            yield ("execute_start", state)
            update = await execute_node(state, self.adapter)
            if "results" in update:
                state.results = update["results"]
            if "handoffs" in update:
                state.handoffs = update["handoffs"]
            state.iteration = update.get("iteration", state.iteration + 1)
            yield ("execute_done", state)

        yield ("synthesize_start", state)
        update = await synthesize_node(state)
        state.final_output = update.get("final_output", "")
        yield ("synthesize_done", state)

        await self.adapter.close()
