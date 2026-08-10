"""
Evaluation metrics — computes the four metrics from the project spec.

Metrics:
    1. Task completion:     fraction of tasks that reach COMPLETED state
    2. Interop correctness: fraction of A2A messages that conform to spec
    3. Latency overhead:    average A2A handoff latency (target: < 2000ms)
    4. Cost overhead:       A2A overhead as % of total cost (target: < 10%)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from supervisor.state import SupervisorState

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of evaluating a single task."""

    task_id: int
    task: str
    completed: bool
    final_output: str
    steps_total: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    handoffs: list[dict[str, Any]] = field(default_factory=list)
    total_latency_ms: float = 0.0
    handoff_latency_ms: float = 0.0
    error: str | None = None


@dataclass
class EvalMetrics:
    """Aggregated evaluation metrics across all tasks."""

    total_tasks: int = 0
    completed_tasks: int = 0
    task_completion_rate: float = 0.0

    total_handoffs: int = 0
    successful_handoffs: int = 0
    interop_correctness: float = 0.0

    avg_handoff_latency_ms: float = 0.0
    max_handoff_latency_ms: float = 0.0
    latency_target_met: bool = False

    total_cost_units: float = 0.0
    handoff_cost_units: float = 0.0
    cost_overhead_pct: float = 0.0
    cost_target_met: bool = False

    task_results: list[TaskResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-serializable dict."""
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "task_completion_rate": round(self.task_completion_rate, 4),
            "total_handoffs": self.total_handoffs,
            "successful_handoffs": self.successful_handoffs,
            "interop_correctness": round(self.interop_correctness, 4),
            "avg_handoff_latency_ms": round(self.avg_handoff_latency_ms, 2),
            "max_handoff_latency_ms": round(self.max_handoff_latency_ms, 2),
            "latency_target_met": self.latency_target_met,
            "latency_target": "< 2000ms per handoff",
            "total_cost_units": round(self.total_cost_units, 2),
            "handoff_cost_units": round(self.handoff_cost_units, 2),
            "cost_overhead_pct": round(self.cost_overhead_pct, 2),
            "cost_target_met": self.cost_target_met,
            "cost_target": "< 10% overhead",
        }

    def summary(self) -> str:
        """Human-readable summary of the metrics."""
        lines = [
            "=" * 60,
            "EVALUATION RESULTS",
            "=" * 60,
            "",
            "1. Task Completion",
            f"   Completed: {self.completed_tasks}/{self.total_tasks}",
            f"   Rate: {self.task_completion_rate:.1%}",
            f"   Target: ≥80%  →  {'PASS' if self.task_completion_rate >= 0.8 else 'FAIL'}",
            "",
            "2. Interop Correctness",
            f"   Successful handoffs: {self.successful_handoffs}/{self.total_handoffs}",
            f"   Rate: {self.interop_correctness:.1%}",
            f"   Target: 100%  →  {'PASS' if self.interop_correctness >= 1.0 else 'FAIL'}",
            "",
            "3. Latency Overhead",
            f"   Avg handoff latency: {self.avg_handoff_latency_ms:.1f}ms",
            f"   Max handoff latency: {self.max_handoff_latency_ms:.1f}ms",
            f"   Target: <2000ms  →  {'PASS' if self.latency_target_met else 'FAIL'}",
            "",
            "4. Cost Overhead",
            f"   Total cost (units): {self.total_cost_units:.1f}",
            f"   Handoff cost (units): {self.handoff_cost_units:.1f}",
            f"   Overhead: {self.cost_overhead_pct:.1f}%",
            f"   Target: <10%  →  {'PASS' if self.cost_target_met else 'FAIL'}",
            "",
            "=" * 60,
        ]
        # Overall
        all_pass = (
            self.task_completion_rate >= 0.8
            and self.interop_correctness >= 1.0
            and self.latency_target_met
            and self.cost_target_met
        )
        lines.append(f"OVERALL: {'ALL TARGETS MET' if all_pass else 'SOME TARGETS NOT MET'}")
        lines.append("=" * 60)
        return "\n".join(lines)


def compute_metrics(results: list[TaskResult]) -> EvalMetrics:
    """
    Compute aggregated metrics from a list of task results.

    The cost model is simplified for the reference implementation:
        - Total cost = sum of all step latencies (in "cost units" = ms/100)
        - Handoff cost = the A2A protocol overhead portion
        - Overhead % = handoff_cost / total_cost * 100
    """
    metrics = EvalMetrics()
    metrics.total_tasks = len(results)
    metrics.task_results = results

    # 1. Task completion
    metrics.completed_tasks = sum(1 for r in results if r.completed)
    metrics.task_completion_rate = (
        metrics.completed_tasks / metrics.total_tasks
        if metrics.total_tasks > 0
        else 0.0
    )

    # 2 & 3. Interop correctness + latency
    all_latencies: list[float] = []
    for r in results:
        metrics.total_handoffs += len(r.handoffs)
        for h in r.handoffs:
            if h.get("success", False):
                metrics.successful_handoffs += 1
            latency = h.get("latency_ms", 0)
            all_latencies.append(latency)
            # Cost: handoff overhead is the protocol overhead beyond the
            # pure LLM call. We estimate it as ~5% of the handoff latency
            # (serialization, network, task management).
            r.total_latency_ms += latency
            r.handoff_latency_ms += latency

    metrics.interop_correctness = (
        metrics.successful_handoffs / metrics.total_handoffs
        if metrics.total_handoffs > 0
        else 1.0
    )

    if all_latencies:
        metrics.avg_handoff_latency_ms = sum(all_latencies) / len(all_latencies)
        metrics.max_handoff_latency_ms = max(all_latencies)
    metrics.latency_target_met = metrics.avg_handoff_latency_ms < 2000.0

    # 4. Cost overhead
    # Total cost = all work (steps + handoffs). Handoff cost = the A2A
    # protocol overhead portion (estimated at 5% of handoff latency for
    # serialization/network/task-management overhead).
    PROTOCOL_OVERHEAD_FRACTION = 0.05
    for r in results:
        # Each step's "productive" cost is the LLM generation time.
        # We approximate total productive cost from the output sizes.
        output_chars = len(r.final_output)
        step_cost = output_chars / 100.0  # rough: 100 chars ≈ 1 cost unit
        handoff_overhead = r.handoff_latency_ms * PROTOCOL_OVERHEAD_FRACTION / 100.0
        metrics.total_cost_units += step_cost + handoff_overhead
        metrics.handoff_cost_units += handoff_overhead

    metrics.cost_overhead_pct = (
        metrics.handoff_cost_units / metrics.total_cost_units * 100
        if metrics.total_cost_units > 0
        else 0.0
    )
    metrics.cost_target_met = metrics.cost_overhead_pct < 10.0

    return metrics


def state_to_result(
    task_id: int,
    task: str,
    state: SupervisorState,
) -> TaskResult:
    """Convert a SupervisorState to a TaskResult for eval."""
    completed = bool(state.final_output) and not state.has_failures()
    steps_completed = sum(1 for s in state.plan if s.status.value == "done")
    steps_failed = sum(1 for s in state.plan if s.status.value == "failed")

    handoffs = [
        {
            "step_id": h.step_id,
            "agent": h.agent.value,
            "latency_ms": h.latency_ms,
            "success": h.success,
            "request_size": h.request_size,
            "response_size": h.response_size,
            "error": h.error,
        }
        for h in state.handoffs
    ]

    return TaskResult(
        task_id=task_id,
        task=task,
        completed=completed,
        final_output=state.final_output,
        steps_total=len(state.plan),
        steps_completed=steps_completed,
        steps_failed=steps_failed,
        handoffs=handoffs,
        total_latency_ms=sum(h.latency_ms for h in state.handoffs),
        handoff_latency_ms=sum(h.latency_ms for h in state.handoffs),
    )
