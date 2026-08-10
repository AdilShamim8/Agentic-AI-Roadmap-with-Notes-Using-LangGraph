"""
A2A Protocol Core Package.

This package implements the Agent-to-Agent (A2A) protocol, a JSON-RPC 2.0
based protocol for inter-agent communication. It provides the building
blocks for exposing any agent as an A2A server and consuming A2A agents
from any client.

Components:
    - models:      Pydantic data models (AgentCard, Task, Message, Part, ...)
    - exceptions:  A2A protocol error types
    - protocol:    JSON-RPC 2.0 constants and helpers
    - server:      Base A2A server (FastAPI) with task management
    - client:      Async A2A client (httpx)
"""

from a2a.models import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    AgentProvider,
    Task,
    TaskState,
    TaskStatus,
    Message,
    MessageRole,
    TextPart,
    DataPart,
    FilePart,
    Artifact,
    PushNotificationConfig,
)
from a2a.exceptions import (
    A2AError,
    JSONRPCError,
    InvalidRequestError,
    MethodNotFoundError,
    InvalidParamsError,
    InternalError,
    TaskNotFoundError,
    TaskNotCancelableError,
    PushNotificationNotSupportedError,
    UnsupportedOperationError,
)
from a2a.server import A2AServer, TaskManager, InMemoryTaskManager
from a2a.client import A2AClient

__version__ = "0.1.0"

__all__ = [
    # Models
    "AgentCard",
    "AgentCapabilities",
    "AgentSkill",
    "AgentProvider",
    "Task",
    "TaskState",
    "TaskStatus",
    "Message",
    "MessageRole",
    "TextPart",
    "DataPart",
    "FilePart",
    "Artifact",
    "PushNotificationConfig",
    # Exceptions
    "A2AError",
    "JSONRPCError",
    "InvalidRequestError",
    "MethodNotFoundError",
    "InvalidParamsError",
    "InternalError",
    "TaskNotFoundError",
    "TaskNotCancelableError",
    "PushNotificationNotSupportedError",
    "UnsupportedOperationError",
    # Server / Client
    "A2AServer",
    "TaskManager",
    "InMemoryTaskManager",
    "A2AClient",
]
