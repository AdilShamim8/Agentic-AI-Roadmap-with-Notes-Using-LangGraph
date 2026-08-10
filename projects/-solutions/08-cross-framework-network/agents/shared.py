"""
Shared utilities for A2A agent servers.

Provides a helper to extract the user's text from an A2A Task's message
history, and a function to build an A2A server from an agent card and
an async execute callable.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from a2a.models import (
    AgentCard,
    Artifact,
    Message,
    MessageRole,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)
from a2a.server import A2AServer, InMemoryTaskManager

logger = logging.getLogger(__name__)


def extract_user_text(task: Task) -> str:
    """
    Extract the latest user-provided text from a task's message history.

    Scans ``task.history`` for the most recent ``user`` message and
    concatenates all ``TextPart`` fragments.
    """
    for msg in reversed(task.history):
        if msg.role == MessageRole.USER:
            texts = [
                p.text for p in msg.parts if hasattr(p, "text") and p.text
            ]
            if texts:
                return "\n".join(texts)
    # Fallback: check the status message.
    if task.status.message and task.status.message.role == MessageRole.USER:
        texts = [
            p.text
            for p in task.status.message.parts
            if hasattr(p, "text") and p.text
        ]
        if texts:
            return "\n".join(texts)
    return ""


def complete_task(task: Task, output_text: str, *, model: str = "unknown") -> Task:
    """
    Mark a task as completed and attach the output as an artifact.

    The output text is wrapped in a :class:`TextPart` inside an
    :class:`Artifact`, and a final ``agent`` message is appended to
    the task history.
    """
    artifact = Artifact(
        name="result",
        description="Agent output",
        parts=[TextPart(text=output_text)],
        metadata={"model": model},
    )
    task.artifacts.append(artifact)

    agent_message = Message(
        role=MessageRole.AGENT,
        parts=[TextPart(text=output_text)],
        taskId=task.id,
        contextId=task.contextId,
    )
    task.history.append(agent_message)
    task.status = TaskStatus(state=TaskState.COMPLETED, message=agent_message)
    return task


def build_a2a_server(
    agent_card: AgentCard,
    execute: Callable[[Task], Any],
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
) -> A2AServer:
    """
    Construct an :class:`A2AServer` for the given agent card and executor.

    The ``execute`` callable receives a :class:`Task` and must return the
    updated :class:`Task` (with status set to ``COMPLETED`` or ``FAILED``).
    """
    manager = InMemoryTaskManager(execute=execute)
    return A2AServer(
        agent_card=agent_card,
        task_manager=manager,
        host=host,
        port=port,
    )
