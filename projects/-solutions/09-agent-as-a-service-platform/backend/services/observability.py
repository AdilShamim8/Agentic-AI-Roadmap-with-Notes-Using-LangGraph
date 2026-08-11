"""Observability service — Prometheus metrics + LangSmith hooks."""
import logging
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Prometheus metrics
# -----------------------------------------------------------------------------
AGENT_INVOCATIONS = Counter(
    "a2a_agent_invocations_total",
    "Total agent invocations",
    ["agent_id", "status"],
)

AGENT_INVOCATION_DURATION = Histogram(
    "a2a_agent_invocation_duration_ms",
    "Agent invocation duration in milliseconds",
    ["agent_id"],
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000),
)

AGENTS_DEPLOYED = Gauge(
    "a2a_agents_deployed_total",
    "Total number of deployed agents (by status)",
    ["status"],
)

COLD_START_LATENCY = Histogram(
    "a2a_cold_start_ms",
    "Cold-start latency for an idle agent (ms)",
    buckets=(100, 500, 1000, 2000, 3000, 5000, 10000),
)


class ObservabilityService:
    """Wraps metric recording so routers don't touch Prometheus directly."""

    def __init__(self) -> None:
        self.langsmith_enabled = bool(__import__("config").settings.langsmith_api_key)

    def record_invocation(
        self, agent_id: str, duration_ms: int, status: str
    ) -> None:
        AGENT_INVOCATIONS.labels(agent_id=agent_id, status=status).inc()
        AGENT_INVOCATION_DURATION.labels(agent_id=agent_id).observe(duration_ms)

    def record_cold_start(self, duration_ms: int) -> None:
        COLD_START_LATENCY.observe(duration_ms)

    def record_deploy(self, status: str) -> None:
        AGENTS_DEPLOYED.labels(status=status).inc()

    async def trace_invocation(
        self, agent_id: str, message: str, output: str
    ) -> None:
        """Send a trace to LangSmith if configured."""
        if not self.langsmith_enabled:
            return
        try:
            # LangSmith SDK integration would go here
            logger.debug("Tracing invocation for agent %s", agent_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("LangSmith trace failed: %s", e)


observability = ObservabilityService()
