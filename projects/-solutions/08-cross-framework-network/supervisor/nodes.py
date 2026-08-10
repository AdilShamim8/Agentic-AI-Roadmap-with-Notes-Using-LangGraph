"""
Supervisor graph nodes — the processing functions for each step.

Each node receives the :class:`SupervisorState` and returns a partial
state update (dict) that gets merged into the current state.

Nodes:
    * ``plan_node``      — decompose the task into steps
    * ``execute_node``   — run the next pending step via A2A
    * ``synthesize_node`` — combine all results into final output
"""

from __future__ import annotations

import logging
import re
from typing import Any

from llm import get_llm
from llm.base import LLMBackend
from supervisor.a2a_adapter import A2AAdapter
from supervisor.state import (
    AgentType,
    HandoffRecord,
    PlanStep,
    StepStatus,
    SupervisorState,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plan node — decompose the task
# ---------------------------------------------------------------------------
PLANNING_SYSTEM = (
    "You are a task planning assistant. Given a user task, decompose it into "
    "2-4 concrete steps. Each step should be assigned to either the 'research' "
    "agent (for information gathering) or the 'writing' agent (for content "
    "production). Output each step on its own line in the format:\n"
    "[agent_type] step description\n\n"
    "Example:\n"
    "[research] Research the current state of multi-agent AI systems\n"
    "[writing] Write a blog post summarizing the research findings"
)


def _parse_plan(raw_plan: str, task: str) -> list[PlanStep]:
    """Parse the LLM's plan output into PlanStep objects."""
    steps: list[PlanStep] = []
    for i, line in enumerate(raw_plan.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        # Match [agent_type] description
        match = re.match(
            r"\[(research|writing|supervisor)\]\s*(.+)",
            line,
            re.IGNORECASE,
        )
        if match:
            agent_str = match.group(1).lower()
            agent = AgentType(agent_str)
            description = match.group(2).strip()
            steps.append(
                PlanStep(
                    id=i,
                    description=description,
                    agent=agent,
                    input=description,
                )
            )
        else:
            # Unparseable line — treat as a research step.
            steps.append(
                PlanStep(
                    id=i,
                    description=line,
                    agent=AgentType.RESEARCH,
                    input=line,
                )
            )

    # Fallback: if no steps were parsed, create a default 2-step plan.
    if not steps:
        steps = [
            PlanStep(
                id=0,
                description=f"Research: {task}",
                agent=AgentType.RESEARCH,
                input=task,
            ),
            PlanStep(
                id=1,
                description=f"Write about: {task}",
                agent=AgentType.WRITING,
                input=task,
            ),
        ]
    return steps


async def plan_node(state: SupervisorState) -> dict[str, Any]:
    """
    Decompose the user task into a plan of steps.

    Uses the LLM to generate a decomposition, then parses it into
    :class:`PlanStep` objects.
    """
    logger.info("PLAN: decomposing task: %s", state.task[:100])
    llm = get_llm()
    response = await llm.generate(
        prompt=f"User task: {state.task}\n\nDecompose this into steps.",
        system=PLANNING_SYSTEM,
        max_tokens=512,
        temperature=0.3,
    )
    plan = _parse_plan(response.text, state.task)
    logger.info("PLAN: created %d steps", len(plan))
    for step in plan:
        logger.info(
            "  step %d [%s]: %s", step.id, step.agent.value, step.description[:80]
        )
    return {"plan": plan}


# ---------------------------------------------------------------------------
# Execute node — run the next pending step
# ---------------------------------------------------------------------------
async def execute_node(
    state: SupervisorState,
    adapter: A2AAdapter,
) -> dict[str, Any]:
    """
    Execute the next pending step via A2A.

    Updates the step's status, calls the appropriate agent, and records
    the handoff telemetry.
    """
    step = state.next_pending_step()
    if step is None:
        return {}

    logger.info("EXECUTE: step %d [%s]", step.id, step.agent.value)
    step.status = StepStatus.RUNNING

    # Build the input text, including context from previous steps.
    input_text = step.input
    if state.results:
        context_parts = [
            f"[Step {sid} result]: {result[:500]}"
            for sid, result in sorted(state.results.items())
        ]
        if context_parts:
            input_text = (
                f"Previous context:\n{'-' * 40}\n"
                + "\n".join(context_parts)
                + f"\n{'-' * 40}\n\nNow handle this:\n{step.input}"
            )

    try:
        output, handoff = await adapter.call_agent(
            agent=step.agent,
            text=input_text,
            step_id=step.id,
        )
        step.output = output
        step.status = StepStatus.DONE
        step.latency_ms = handoff.latency_ms

        results = dict(state.results)
        results[step.id] = output
        handoffs = list(state.handoffs) + [handoff]

        logger.info(
            "EXECUTE: step %d done (%.1fms, %d chars)",
            step.id,
            handoff.latency_ms,
            len(output),
        )
        return {"results": results, "handoffs": handoffs, "iteration": state.iteration + 1}

    except Exception as exc:
        logger.error("EXECUTE: step %d failed: %s", step.id, exc)
        step.status = StepStatus.FAILED
        step.error = str(exc)
        return {"iteration": state.iteration + 1}


# ---------------------------------------------------------------------------
# Synthesize node — combine results into final output
# ---------------------------------------------------------------------------
SYNTHESIS_SYSTEM = (
    "You are a synthesis assistant. Given a user task and the outputs from "
    "multiple sub-tasks, produce a coherent, well-structured final response "
    "that addresses the original task. Integrate the sub-task outputs "
    "seamlessly, removing redundancy and ensuring a logical flow."
)


async def synthesize_node(state: SupervisorState) -> dict[str, Any]:
    """
    Combine all step results into a final synthesized output.

    Uses the LLM to merge the sub-task outputs into a coherent response
    that addresses the original user task.
    """
    logger.info("SYNTHESIZE: combining %d results", len(state.results))

    if not state.results:
        return {"final_output": "[No results to synthesize]"}

    if len(state.results) == 1:
        # Single result — return it directly with minimal wrapping.
        output = list(state.results.values())[0]
        return {"final_output": output}

    llm = get_llm()
    parts = []
    for step_id, result in sorted(state.results.items()):
        step = next((s for s in state.plan if s.id == step_id), None)
        label = step.description if step else f"Step {step_id}"
        parts.append(f"--- Sub-task: {label} ---\n{result}")
    combined = "\n\n".join(parts)

    response = await llm.generate(
        prompt=(
            f"Original user task: {state.task}\n\n"
            f"Sub-task results:\n{combined}\n\n"
            f"Produce the final synthesized response."
        ),
        system=SYNTHESIS_SYSTEM,
        max_tokens=1024,
        temperature=0.5,
    )

    return {"final_output": response.text}


# ---------------------------------------------------------------------------
# Routing function — decide what to run next
# ---------------------------------------------------------------------------
def should_continue(state: SupervisorState) -> str:
    """
    Routing logic after execute_node.

    Returns:
        ``"execute"`` if there are more pending steps.
        ``"synthesize"`` if all steps are done (or failed).
    """
    if state.iteration >= state.max_iterations:
        logger.warning("Max iterations reached (%d), synthesizing", state.max_iterations)
        return "synthesize"
    if state.next_pending_step() is not None:
        return "execute"
    return "synthesize"
