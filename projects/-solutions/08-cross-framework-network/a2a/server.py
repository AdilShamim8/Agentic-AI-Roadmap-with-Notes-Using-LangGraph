"""
A2A Server — FastAPI implementation of the A2A protocol.

Exposes any agent as an A2A-compatible server that:

* Serves an **Agent Card** at ``GET /.well-known/agent.json``.
* Accepts JSON-RPC 2.0 requests at ``POST /`` for:
    - ``tasks/send``         — synchronous task execution
    - ``tasks/sendSubscribe`` — streaming task execution (SSE)
    - ``tasks/get``          — retrieve task state
    - ``tasks/cancel``       — cancel a running task
    - ``tasks/list``         — list all tasks

Agents are integrated by providing a :class:`TaskManager` whose
:meth:`TaskManager.on_send_task` is called for each incoming task.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Callable

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from a2a.exceptions import (
    InternalError,
    InvalidParamsError,
    InvalidRequestError,
    JSONRPCError,
    MethodNotFoundError,
    TaskNotFoundError,
    UnsupportedOperationError,
)
from a2a.models import (
    A2AMethod,
    AgentCard,
    JSONRPCResponse,
    Message,
    Task,
    TaskState,
    TaskStatus,
)
from a2a.protocol import make_error_response, make_success_response, parse_request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task Manager (abstract + in-memory)
# ---------------------------------------------------------------------------
class TaskManager(ABC):
    """Abstract base for task storage and execution."""

    @abstractmethod
    async def on_send_task(self, params: dict[str, Any]) -> Task:
        """Handle ``tasks/send`` — create or update a task and return it."""

    @abstractmethod
    async def on_send_task_subscribe(
        self, params: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        """Handle ``tasks/sendSubscribe`` — stream task updates as SSE events."""

    @abstractmethod
    async def on_get_task(self, params: dict[str, Any]) -> Task:
        """Handle ``tasks/get`` — return the current task state."""

    @abstractmethod
    async def on_cancel_task(self, params: dict[str, Any]) -> Task:
        """Handle ``tasks/cancel`` — cancel a task."""

    @abstractmethod
    async def on_list_tasks(self) -> list[Task]:
        """Handle ``tasks/list`` — return all known tasks."""


class InMemoryTaskManager(TaskManager):
    """
    In-memory task store with pluggable agent execution.

    Subclasses (or callers) provide an ``execute`` coroutine that takes a
    :class:`Task` and returns the updated :class:`Task`.  Between submission
    and completion the manager transitions the task through the
    ``submitted → working → completed`` lifecycle.
    """

    def __init__(
        self,
        execute: Callable[[Task], Any] | None = None,
        streaming_execute: Callable[[Task], Any] | None = None,
    ) -> None:
        self._tasks: dict[str, Task] = {}
        self._execute: Callable[[Task], Any] | None = execute
        self._streaming_execute: Callable[[Task], Any] | None = streaming_execute

    # -- storage helpers ----------------------------------------------------
    async def _upsert(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    async def _get(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' not found")
        return task

    # -- JSON-RPC handlers --------------------------------------------------
    async def on_send_task(self, params: dict[str, Any]) -> Task:
        task = self._task_from_params(params)

        # If this is an existing task being updated, preserve history.
        existing = self._tasks.get(task.id)
        if existing is not None:
            existing.history.extend(task.history)
            task.history = existing.history
            task.artifacts = existing.artifacts + task.artifacts

        # Transition to WORKING immediately so callers see progress.
        task.status = TaskStatus(state=TaskState.WORKING)
        await self._upsert(task)

        if self._execute is not None:
            try:
                task = await self._execute(task)  # type: ignore[assignment]
            except Exception as exc:
                logger.exception("Task execution failed: %s", exc)
                task.status = TaskStatus(
                    state=TaskState.FAILED,
                    message=Message(
                        role="agent",
                        parts=[{"type": "text", "text": f"Execution error: {exc}"}],
                    ),
                )
        await self._upsert(task)
        return task

    async def on_send_task_subscribe(
        self, params: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        task = self._task_from_params(params)
        task.status = TaskStatus(state=TaskState.WORKING)
        await self._upsert(task)

        # Yield the "working" status first.
        yield self._task_to_event(task)

        if self._streaming_execute is not None:
            try:
                async for updated in self._streaming_execute(task):
                    task = updated
                    await self._upsert(task)
                    yield self._task_to_event(task)
            except Exception as exc:
                logger.exception("Streaming task failed: %s", exc)
                task.status = TaskStatus(
                    state=TaskState.FAILED,
                    message=Message(
                        role="agent",
                        parts=[{"type": "text", "text": f"Streaming error: {exc}"}],
                    ),
                )
                await self._upsert(task)
                yield self._task_to_event(task)
        else:
            # Fall back to non-streaming execute.
            if self._execute is not None:
                task = await self._execute(task)  # type: ignore[assignment]
                await self._upsert(task)
            yield self._task_to_event(task)

    async def on_get_task(self, params: dict[str, Any]) -> Task:
        task_id = params.get("id")
        if not task_id:
            raise InvalidParamsError("Missing 'id' in params")
        return await self._get(task_id)

    async def on_cancel_task(self, params: dict[str, Any]) -> Task:
        task_id = params.get("id")
        if not task_id:
            raise InvalidParamsError("Missing 'id' in params")
        task = await self._get(task_id)
        if task.status.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED):
            from a2a.exceptions import TaskNotCancelableError

            raise TaskNotCancelableError(
                f"Task '{task_id}' is in state {task.status.state.value} and cannot be canceled"
            )
        task.status = TaskStatus(state=TaskState.CANCELED)
        await self._upsert(task)
        return task

    async def on_list_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _task_from_params(params: dict[str, Any]) -> Task:
        """Build a Task from ``tasks/send`` params."""
        if "message" not in params and "id" not in params:
            raise InvalidParamsError("Params must contain 'message' or 'id'")
        message_data = params.get("message")
        if message_data is not None:
            message = Message(**message_data)
            history = [message]
        else:
            history = []
        status = TaskStatus(state=TaskState.SUBMITTED)
        task = Task(
            id=params.get("id") or Task.model_fields["id"].default_factory(),  # type: ignore[attr-defined]
            contextId=params.get("contextId") or Task.model_fields["contextId"].default_factory(),  # type: ignore[attr-defined]
            status=status,
            history=history,
            metadata=params.get("metadata"),
        )
        return task

    @staticmethod
    def _task_to_event(task: Task) -> dict[str, Any]:
        """Convert a Task to a JSON-RPC result dict for SSE."""
        return task.model_dump(mode="json", exclude_none=True)


# ---------------------------------------------------------------------------
# A2A Server (FastAPI)
# ---------------------------------------------------------------------------
class A2AServer:
    """FastAPI application that serves an A2A agent."""

    def __init__(
        self,
        agent_card: AgentCard,
        task_manager: TaskManager,
        host: str = "0.0.0.0",
        port: int = 8000,
    ) -> None:
        self.agent_card = agent_card
        self.task_manager = task_manager
        self.host = host
        self.port = port
        self.app = FastAPI(title=f"A2A Agent: {agent_card.name}")
        self._setup_routes()

    # -- routing ------------------------------------------------------------
    def _setup_routes(self) -> None:
        @self.app.get("/.well-known/agent.json")
        async def agent_card_endpoint() -> dict[str, Any]:
            return self.agent_card.model_dump(mode="json", exclude_none=True)

        @self.app.get("/")
        async def root() -> dict[str, str]:
            return {
                "service": self.agent_card.name,
                "agent_card": "/.well-known/agent.json",
                "jsonrpc": "/ (POST)",
            }

        @self.app.post("/")
        async def jsonrpc_handler(request: Request) -> JSONResponse:
            try:
                body = await request.json()
            except Exception:
                err = InvalidRequestError("Body is not valid JSON")
                return JSONResponse(
                    make_error_response(err).model_dump(exclude_none=True)
                )

            # Batch request?
            if isinstance(body, list):
                results = await asyncio.gather(
                    *[self._handle_single(req) for req in body],
                    return_exceptions=False,
                )
                # Filter out notifications (no id → no response)
                responses = [r for r in results if r is not None]
                if not responses:
                    return JSONResponse(content=None, status_code=204)
                return JSONResponse(responses)

            response = await self._handle_single(body)
            if response is None:
                return JSONResponse(content=None, status_code=204)
            return JSONResponse(response)

        @self.app.post("/tasks/sendSubscribe")
        async def send_subscribe(request: Request) -> StreamingResponse:
            """SSE streaming endpoint for ``tasks/sendSubscribe``."""
            try:
                body = await request.json()
            except Exception:
                err = InvalidRequestError("Body is not valid JSON")
                return JSONResponse(  # type: ignore[return-value]
                    make_error_response(err).model_dump(exclude_none=True)
                )

            async def event_stream() -> AsyncIterator[bytes]:
                try:
                    params = body.get("params", {})
                    async for event in self.task_manager.on_send_task_subscribe(params):
                        data = json.dumps(event)
                        yield f"data: {data}\n\n".encode()
                except JSONRPCError as exc:
                    err_data = make_error_response(exc, body.get("id")).model_dump(
                        exclude_none=True
                    )
                    yield f"data: {json.dumps(err_data)}\n\n".encode()

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

    async def _handle_single(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        """Dispatch a single JSON-RPC request."""
        try:
            req = parse_request(raw)
        except JSONRPCError as exc:
            return make_error_response(exc, raw.get("id")).model_dump(exclude_none=True)

        request_id = req.id
        method = req.method
        params = req.params or {}

        try:
            if method == A2AMethod.SEND:
                task = await self.task_manager.on_send_task(params)
                result = task.model_dump(mode="json", exclude_none=True)
                return make_success_response(result, request_id).model_dump(
                    exclude_none=True
                )

            elif method == A2AMethod.GET:
                task = await self.task_manager.on_get_task(params)
                result = task.model_dump(mode="json", exclude_none=True)
                return make_success_response(result, request_id).model_dump(
                    exclude_none=True
                )

            elif method == A2AMethod.CANCEL:
                task = await self.task_manager.on_cancel_task(params)
                result = task.model_dump(mode="json", exclude_none=True)
                return make_success_response(result, request_id).model_dump(
                    exclude_none=True
                )

            elif method == A2AMethod.LIST_TASKS:
                tasks = await self.task_manager.on_list_tasks()
                result = [t.model_dump(mode="json", exclude_none=True) for t in tasks]
                return make_success_response(result, request_id).model_dump(
                    exclude_none=True
                )

            elif method == A2AMethod.SEND_SUBSCRIBE:
                # SSE is handled by the dedicated /tasks/sendSubscribe route.
                raise UnsupportedOperationError(
                    "Use POST /tasks/sendSubscribe with SSE for streaming tasks"
                )

            elif method == A2AMethod.SET_PUSH_NOTIFICATION:
                raise UnsupportedOperationError("Push notifications not supported")

            elif method == A2AMethod.GET_PUSH_NOTIFICATION:
                raise UnsupportedOperationError("Push notifications not supported")

            else:
                raise MethodNotFoundError(f"Unknown method: {method}")

        except JSONRPCError as exc:
            return make_error_response(exc, request_id).model_dump(exclude_none=True)
        except Exception as exc:
            logger.exception("Unhandled error processing %s: %s", method, exc)
            return make_error_response(
                InternalError(f"Internal error: {exc}"), request_id
            ).model_dump(exclude_none=True)

    # -- run ----------------------------------------------------------------
    def run(self) -> None:
        """Start the uvicorn server (blocking)."""
        uvicorn.run(self.app, host=self.host, port=self.port)

    def run_async(self) -> None:
        """Start uvicorn without blocking the event loop."""
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="info")
        server = uvicorn.Server(config)
        asyncio.run(server.serve())
