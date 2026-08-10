"""
JSON-RPC 2.0 protocol helpers for A2A.

Provides utility functions for building and parsing JSON-RPC requests
and responses, including error envelopes.
"""

from __future__ import annotations

from typing import Any

from a2a.exceptions import JSONRPCError
from a2a.models import JSONRPCRequest, JSONRPCResponse


def make_request(
    method: str,
    params: dict[str, Any] | None = None,
    request_id: str | int | None = None,
) -> JSONRPCRequest:
    """Build a JSON-RPC 2.0 request object."""
    return JSONRPCRequest(
        jsonrpc="2.0",
        id=request_id,
        method=method,
        params=params,
    )


def make_success_response(
    result: Any,
    request_id: str | int | None = None,
) -> JSONRPCResponse:
    """Build a JSON-RPC 2.0 success response."""
    return JSONRPCResponse(jsonrpc="2.0", id=request_id, result=result, error=None)


def make_error_response(
    error: JSONRPCError,
    request_id: str | int | None = None,
) -> JSONRPCResponse:
    """Build a JSON-RPC 2.0 error response from an A2A exception."""
    return JSONRPCResponse(
        jsonrpc="2.0",
        id=request_id,
        result=None,
        error=error.to_dict(),
    )


def parse_request(raw: dict[str, Any]) -> JSONRPCRequest:
    """Parse and validate a raw dict into a JSONRPCRequest.

    Raises:
        InvalidRequestError: if the payload is not valid JSON-RPC 2.0.
    """
    from a2a.exceptions import InvalidRequestError

    if not isinstance(raw, dict):
        raise InvalidRequestError("Request must be a JSON object")
    if raw.get("jsonrpc") != "2.0":
        raise InvalidRequestError("Missing or invalid 'jsonrpc' field (must be '2.0')")
    if "method" not in raw:
        raise InvalidRequestError("Missing 'method' field")
    return JSONRPCRequest(**raw)
