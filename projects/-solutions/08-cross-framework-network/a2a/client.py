"""
A2A Client — async client for consuming A2A agents.

Provides a high-level interface for:
    * Discovering an agent via its Agent Card.
    * Sending tasks (synchronous and streaming).
    * Querying, canceling, and listing tasks.

Usage::

    client = A2AClient("http://localhost:8001")
    card = await client.get_agent_card()
    task = await client.send_task("Summarize the latest AI news")
    print(task.artifacts[0].parts[0].text)
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncIterator

import httpx

from a2a.exceptions import JSONRPCError
from a2a.models import (
    AgentCard,
    Message,
    MessageRole,
    Task,
    TextPart,
)

logger = logging.getLogger(__name__)


class A2AClient:
    """Async client for an A2A-compatible agent server."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # Normalize base URL (strip trailing slash).
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._transport = transport
        self._agent_card: AgentCard | None = None

    # -- lifecycle ----------------------------------------------------------
    async def __aenter__(self) -> "A2AClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=self._transport,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # -- discovery ----------------------------------------------------------
    async def get_agent_card(self) -> AgentCard:
        """Fetch and cache the agent's Agent Card."""
        client = await self._ensure_client()
        resp = await client.get("/.well-known/agent.json")
        resp.raise_for_status()
        self._agent_card = AgentCard(**resp.json())
        return self._agent_card

    @property
    def agent_card(self) -> AgentCard | None:
        return self._agent_card

    # -- JSON-RPC -----------------------------------------------------------
    async def _call(
        self, method: str, params: dict[str, Any], request_id: str | None = None
    ) -> dict[str, Any]:
        """Send a JSON-RPC 2.0 request and return the ``result`` field."""
        client = await self._ensure_client()
        rid = request_id or str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params,
        }
        resp = await client.post("/", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            err = data["error"]
            raise JSONRPCError(
                f"A2A error {err.get('code')}: {err.get('message')}",
                data=err.get("data"),
            )
        return data.get("result", {})

    async def _call_streaming(
        self, method: str, params: dict[str, Any], request_id: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a streaming JSON-RPC request via SSE and yield events."""
        client = await self._ensure_client()
        rid = request_id or str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params,
        }
        async with client.stream(
            "POST", "/tasks/sendSubscribe", json=payload
        ) as resp:
            resp.raise_for_status()
            event_data = ""
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    event_data = line[6:]
                elif line == "" and event_data:
                    try:
                        event = json.loads(event_data)
                    except json.JSONDecodeError:
                        logger.warning("Could not parse SSE event: %s", event_data)
                        event_data = ""
                        continue
                    if "error" in event and event.get("error"):
                        err = event["error"]
                        raise JSONRPCError(
                            f"A2A streaming error {err.get('code')}: {err.get('message')}",
                            data=err.get("data"),
                        )
                    yield event
                    event_data = ""

    # -- high-level API -----------------------------------------------------
    async def send_task(
        self,
        text: str | None = None,
        *,
        message: Message | None = None,
        task_id: str | None = None,
        context_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """
        Send a task synchronously and return the completed :class:`Task`.

        Either ``text`` (simple string) or ``message`` (full Message) must
        be provided.
        """
        if message is None:
            if text is None:
                raise ValueError("Either 'text' or 'message' must be provided")
            message = Message(
                role=MessageRole.USER,
                parts=[TextPart(text=text)],
            )

        params: dict[str, Any] = {"message": message.model_dump(mode="json")}
        if task_id:
            params["id"] = task_id
        if context_id:
            params["contextId"] = context_id
        if metadata:
            params["metadata"] = metadata

        result = await self._call("tasks/send", params)
        return Task(**result)

    async def send_task_streaming(
        self,
        text: str | None = None,
        *,
        message: Message | None = None,
        task_id: str | None = None,
        context_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator[Task]:
        """Send a task and yield :class:`Task` updates as they arrive (SSE)."""
        if message is None:
            if text is None:
                raise ValueError("Either 'text' or 'message' must be provided")
            message = Message(
                role=MessageRole.USER,
                parts=[TextPart(text=text)],
            )

        params: dict[str, Any] = {"message": message.model_dump(mode="json")}
        if task_id:
            params["id"] = task_id
        if context_id:
            params["contextId"] = context_id
        if metadata:
            params["metadata"] = metadata

        async for event in self._call_streaming("tasks/sendSubscribe", params):
            yield Task(**event)

    async def get_task(self, task_id: str) -> Task:
        """Retrieve the current state of a task by ID."""
        result = await self._call("tasks/get", {"id": task_id})
        return Task(**result)

    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a running task."""
        result = await self._call("tasks/cancel", {"id": task_id})
        return Task(**result)

    async def list_tasks(self) -> list[Task]:
        """List all tasks known to the agent."""
        result = await self._call("tasks/list", {})
        return [Task(**t) for t in result]


__all__ = ["A2AClient"]
