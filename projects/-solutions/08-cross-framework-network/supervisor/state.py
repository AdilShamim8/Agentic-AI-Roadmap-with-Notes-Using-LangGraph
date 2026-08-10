"""
Supervisor state — mirrors a LangGraph ``State`` TypedDict.

The state flows through the graph nodes and accumulates:

    * ``task``:          the original user request
    * ``plan``:          decomposed steps with agent assignments
    * ``results``:       accumulated results from each step
    * ``handoffs``:      per-handoff timing data (for eval)
    * ``final_output``:  the synthesized result
    * ``error``:         error message if the graph fails
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    """Status of a single plan step."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentType(str, Enum):
    """Which A2A agent a step is routed to."""

    RESEARCH = "research"
    WRITING = "writing"
    SUPERVISOR = "supervisor"  # for self-synthesis steps


@dataclass
class PlanStep:
    """A single step in the supervisor's plan."""

    id: int
    description: str
    agent: AgentType
    status: StepStatus = StepStatus.PENDING
    input: str = ""
    output: str = ""
    latency_ms: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffRecord:
    """Record of a single A2A handoff (for interop metrics)."""

    step_id: int
    agent: AgentType
    agent_url: str
    task_id: str | None = None
    latency_ms: float = 0.0
    success: bool = True
    error: str | None = None
    request_size: int = 0
    response_size: int = 0


@dataclass
class SupervisorState:
    """
    Mutable state that flows through the supervisor graph.

    Mirrors the LangGraph ``State`` pattern: each node receives the state,
    performs work, and returns a (partial) state update that gets merged.
    """

    task: str = ""
    plan: list[PlanStep] = field(default_factory=list)
    results: dict[int, str] = field(default_factory=dict)  # step_id → output
    handoffs: list[HandoffRecord] = field(default_factory=list)
    final_output: str = ""
    error: str | None = None
    iteration: int = 0
    max_iterations: int = 10

    def next_pending_step(self) -> PlanStep | None:
        """Return the next pending step, or None if all are done."""
        for step in self.plan:
            if step.status in (StepStatus.PENDING,):
                return step
        return None

    def all_steps_done(self) -> bool:
        """True if every step is in a terminal state."""
        return all(
            s.status in (StepStatus.DONE, StepStatus.FAILED, StepStatus.SKIPPED)
            for s in self.plan
        )

    def has_failures(self) -> bool:
        """True if any step failed."""
        return any(s.status == StepStatus.FAILED for s in self.plan)
