"""
A2A Protocol Exception Hierarchy.

These exceptions map to JSON-RPC 2.0 error codes as defined in the
A2A specification. Each error carries a code, message, and optional data.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 standard error codes
# ---------------------------------------------------------------------------
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# A2A-specific error codes (server errors, range -32000 to -32099)
TASK_NOT_FOUND = -32001
TASK_NOT_CANCELABLE = -32002
PUSH_NOTIFICATION_NOT_SUPPORTED = -32003
UNSUPPORTED_OPERATION = -32004


class A2AError(Exception):
    """Base exception for all A2A errors."""

    def __init__(self, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.data = data


class JSONRPCError(A2AError):
    """Base class for JSON-RPC 2.0 errors that carry a numeric code."""

    code: int = INTERNAL_ERROR

    def __init__(self, message: str, data: Any = None) -> None:
        super().__init__(message, data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the JSON-RPC error object."""
        obj: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            obj["data"] = self.data
        return obj


class InvalidRequestError(JSONRPCError):
    """The JSON sent is not a valid Request object."""

    code = INVALID_REQUEST


class MethodNotFoundError(JSONRPCError):
    """The method does not exist or is not available."""

    code = METHOD_NOT_FOUND


class InvalidParamsError(JSONRPCError):
    """Invalid method parameter(s)."""

    code = INVALID_PARAMS


class InternalError(JSONRPCError):
    """Internal JSON-RPC error."""

    code = INTERNAL_ERROR


class TaskNotFoundError(JSONRPCError):
    """The requested task ID was not found."""

    code = TASK_NOT_FOUND


class TaskNotCancelableError(JSONRPCError):
    """The task cannot be canceled (e.g. already completed)."""

    code = TASK_NOT_CANCELABLE


class PushNotificationNotSupportedError(JSONRPCError):
    """Push notifications are not supported by this agent."""

    code = PUSH_NOTIFICATION_NOT_SUPPORTED


class UnsupportedOperationError(JSONRPCError):
    """The agent does not support this operation."""

    code = UNSUPPORTED_OPERATION
