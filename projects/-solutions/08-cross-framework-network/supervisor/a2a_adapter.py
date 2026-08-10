"""
A2A Adapter for the LangGraph Supervisor.

Provides a clean interface for supervisor nodes to call A2A agents.
Wraps :class:`A2AClient` and records handoff telemetry (latency,
success, payload sizes) for evaluation.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from a2a.client import A2AClient
from a2a.models import Task as A2ATask
from supervisor.state import AgentType, HandoffRecord

logger = logging.getLogger(__name__)


class A2AAdapter:
    """
    Adapter that lets the supervisor call A2A agents with telemetry.

    Each call records a :class:`HandoffRecord` capturing latency, success,
    and payload size — this feeds the interop-overhead evaluation.
    """

    def __init__(
        self,
        research_url: str | None = None,
        writing_url: str | None = None,
    ) -> None:
        self.research_url = (
            research_url
            or os.environ.get("RESEARCH_AGENT_URL", "http://localhost:8001")
        )
        self.writing_url = (
            writing_url
            or os.environ.get("WRITING_AGENT_URL", "http://localhost:8002")
        )
        self._clients: dict[str, A2AClient] = {}

    def _get_client(self, agent: AgentType) -> A2AClient:
        """Get or create an A2AClient for the given agent type."""
        url = self.research_url if agent == AgentType.RESEARCH else self.writing_url
        if url not in self._clients:
            self._clients[url] = A2AClient(url, timeout=120.0)
        return self._clients[url]

    async def call_agent(
        self,
        agent: AgentType,
        text: str,
        step_id: int = 0,
    ) -> tuple[str, HandoffRecord]:
        """
        Send ``text`` to the specified A2A agent and return (output, handoff).

        The handoff record captures timing and payload metrics for eval.
        """
        url = self.research_url if agent == AgentType.RESEARCH else self.writing_url
        client = self._get_client(agent)

        record = HandoffRecord(
            step_id=step_id,
            agent=agent,
            agent_url=url,
            request_size=len(text),
        )

        t0 = time.perf_counter()
        try:
            logger.info(
                "A2A handoff: step=%d agent=%s url=%s", step_id, agent.value, url
            )
            task = await client.send_task(text=text)
            elapsed = (time.perf_counter() - t0) * 1000
            record.latency_ms = elapsed
            record.task_id = task.id

            # Extract output text from the task's artifacts.
            output = self._extract_output(task)
            record.response_size = len(output)
            record.success = True

            logger.info(
                "A2A handoff complete: step=%d latency=%.1fms response=%d chars",
                step_id,
                elapsed,
                len(output),
            )
            return output, record

        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            record.latency_ms = elapsed
            record.success = False
            record.error = str(exc)
            logger.error(
                "A2A handoff failed: step=%d agent=%s error=%s",
                step_id,
                agent.value,
                exc,
            )
            raise

    @staticmethod
    def _extract_output(task: A2ATask) -> str:
        """Extract the output text from a completed A2A task."""
        # Prefer artifacts.
        if task.artifacts:
            texts = []
            for artifact in task.artifacts:
                for part in artifact.parts:
                    if hasattr(part, "text") and part.text:
                        texts.append(part.text)
            if texts:
                return "\n\n".join(texts)

        # Fallback: last agent message.
        for msg in reversed(task.history):
            if msg.role == "agent":
                texts = [
                    p.text for p in msg.parts if hasattr(p, "text") and p.text
                ]
                if texts:
                    return "\n".join(texts)

        # Last resort: status message.
        if task.status.message:
            texts = [
                p.text
                for p in task.status.message.parts
                if hasattr(p, "text") and p.text
            ]
            if texts:
                return "\n".join(texts)

        return "[No output returned by agent]"

    async def close(self) -> None:
        """Close all open A2A clients."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
