"""
A2A Protocol Data Models.

Pydantic v2 models for the Agent-to-Agent protocol. These define the
shape of every message exchanged between A2A servers and clients.

Reference: https://google.github.io/A2A/
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TaskState(str, Enum):
    """Lifecycle states of an A2A task."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"
    UNKNOWN = "unknown"


class MessageRole(str, Enum):
    """Role of a message participant."""

    USER = "user"
    AGENT = "agent"


# ---------------------------------------------------------------------------
# Agent discovery models
# ---------------------------------------------------------------------------
class AgentProvider(BaseModel):
    """Organization or person that published the agent."""

    organization: str
    url: str | None = None


class AgentCapabilities(BaseModel):
    """Optional capabilities advertised by the agent."""

    streaming: bool = False
    pushNotifications: bool = False
    stateTransitionHistory: bool = False


class AgentSkill(BaseModel):
    """A capability the agent can perform."""

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    inputModes: list[str] | None = None
    outputModes: list[str] | None = None


class AgentCard(BaseModel):
    """
    Agent Card — the discovery document served at ``/.well-known/agent.json``.

    Describes the agent's identity, capabilities, skills, and endpoint.
    """

    name: str
    description: str
    url: str
    version: str = "1.0.0"
    protocolVersion: str = "0.2.5"
    provider: AgentProvider | None = None
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    skills: list[AgentSkill] = Field(default_factory=list)
    defaultInputModes: list[str] = Field(default_factory=lambda: ["text"])
    defaultOutputModes: list[str] = Field(default_factory=lambda: ["text"])
    documentationUrl: str | None = None


# ---------------------------------------------------------------------------
# Message parts
# ---------------------------------------------------------------------------
class TextPart(BaseModel):
    """A plain-text content part."""

    type: Literal["text"] = "text"
    text: str
    metadata: dict[str, Any] | None = None


class DataPart(BaseModel):
    """A structured-data content part (JSON object)."""

    type: Literal["data"] = "data"
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None


class FileWithBytes(BaseModel):
    """File content delivered inline as bytes."""

    name: str | None = None
    mimeType: str | None = None
    bytes: str  # base64-encoded


class FileWithUri(BaseModel):
    """File content referenced by a URL."""

    name: str | None = None
    mimeType: str | None = None
    uri: str


class FilePart(BaseModel):
    """A file content part (inline bytes or URI)."""

    type: Literal["file"] = "file"
    file: FileWithBytes | FileWithUri
    metadata: dict[str, Any] | None = None


Part = Union[TextPart, DataPart, FilePart]


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
class Message(BaseModel):
    """A single message in a task conversation."""

    role: MessageRole
    parts: list[Part]
    messageId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    taskId: str | None = None
    contextId: str | None = None
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Task status and task
# ---------------------------------------------------------------------------
class TaskStatus(BaseModel):
    """Status of a task at a point in time."""

    state: TaskState
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    message: Message | None = None


class Artifact(BaseModel):
    """An output artifact produced by a task."""

    artifactId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str | None = None
    description: str | None = None
    parts: list[Part] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class Task(BaseModel):
    """
    A unit of work sent to an A2A agent.

    A task has a lifecycle: submitted → working → (completed | failed | canceled).
    It accumulates messages and artifacts over time.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contextId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus
    history: list[Message] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            return TaskStatus(state=TaskState(v))
        return v


# ---------------------------------------------------------------------------
# Push notifications
# ---------------------------------------------------------------------------
class PushNotificationConfig(BaseModel):
    """Configuration for server-to-client push notifications."""

    url: str
    token: str | None = None
    authentication: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# JSON-RPC request / response envelopes
# ---------------------------------------------------------------------------
class JSONRPCRequest(BaseModel):
    """A JSON-RPC 2.0 request."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None


class JSONRPCResponse(BaseModel):
    """A JSON-RPC 2.0 response (success or error)."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any = None
    error: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Protocol method constants
# ---------------------------------------------------------------------------
class A2AMethod:
    """JSON-RPC method names defined by the A2A spec."""

    SEND = "tasks/send"
    SEND_SUBSCRIBE = "tasks/sendSubscribe"
    GET = "tasks/get"
    CANCEL = "tasks/cancel"
    RESUBSCRIBE = "tasks/resubscribe"
    SET_PUSH_NOTIFICATION = "tasks/pushNotification/set"
    GET_PUSH_NOTIFICATION = "tasks/pushNotification/get"
    LIST_TASKS = "tasks/list"


__all__ = [
    "TaskState",
    "MessageRole",
    "AgentProvider",
    "AgentCapabilities",
    "AgentSkill",
    "AgentCard",
    "TextPart",
    "DataPart",
    "FileWithBytes",
    "FileWithUri",
    "FilePart",
    "Part",
    "Message",
    "TaskStatus",
    "Artifact",
    "Task",
    "PushNotificationConfig",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "A2AMethod",
]
