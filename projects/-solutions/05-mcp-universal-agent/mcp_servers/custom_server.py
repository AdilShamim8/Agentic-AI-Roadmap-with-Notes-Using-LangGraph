"""Custom utility MCP server.

A grab-bag of small, dependency-free tools that don't fit any of the other
servers: string transforms, UUID generation, currency conversion (static
rates) and a tiny in-memory key/value store. Useful as the "5th server"
required by the project spec and as a stretching ground for tool-selection
under noisy descriptions.

Run as a stdio MCP server::

    python3 -m mcp_servers.custom_server
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Dict

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("custom")

# Static currency rates relative to USD. Update periodically in production.
_RATES: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "PKR": 278.5,
    "INR": 83.2,
    "BDT": 117.4,
    "JPY": 156.8,
    "CNY": 7.24,
}

# Per-process key/value store (resets when the server restarts).
_KV: Dict[str, str] = {}


@mcp.tool()
def uuid_v4() -> str:
    """Generate a random RFC-4122 version-4 UUID string.

    Use this whenever the user asks for a unique identifier, a transaction
    id, a one-time token, etc.

    Returns:
        A 36-character UUID string, e.g. ``123e4567-e89b-12d3-a456-426614174000``.
    """
    return str(uuid.uuid4())


@mcp.tool()
def hash_text(text: str, algorithm: str = "sha256") -> str:
    """Return the cryptographic hash of ``text``.

    Supported algorithms: ``md5``, ``sha1``, ``sha256`` (default), ``sha512``.

    Examples:
        hash_text("hello")                      -> 2cf24dba...
        hash_text("hello", algorithm="md5")     -> 5d41402a...

    Args:
        text: The input string to hash.
        algorithm: One of ``md5``, ``sha1``, ``sha256``, ``sha512``.

    Returns:
        Hex-encoded digest string.
    """
    algo = algorithm.lower()
    if algo not in {"md5", "sha1", "sha256", "sha512"}:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    h = hashlib.new(algo)
    h.update(text.encode("utf-8"))
    return h.hexdigest()


@mcp.tool()
def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert ``amount`` from one currency to another using static rates.

    Rates are relative to USD and updated manually. For live rates, replace
    the body of this function with an API call (e.g. exchangerate.host).

    Examples:
        convert_currency(100, "USD", "PKR") -> 27850.0
        convert_currency(50, "EUR", "USD")  -> 54.35

    Args:
        amount: Numeric amount to convert.
        from_currency: ISO 4217 source currency code (e.g. "USD").
        to_currency: ISO 4217 target currency code.

    Returns:
        Converted amount as a float.
    """
    f = from_currency.upper()
    t = to_currency.upper()
    if f not in _RATES or t not in _RATES:
        missing = {f, t} - set(_RATES)
        raise ValueError(f"Unknown currency code(s): {missing}")
    usd = amount / _RATES[f]
    return usd * _RATES[t]


@mcp.tool()
def transform_string(text: str, operation: str) -> str:
    """Apply a string transformation to ``text``.

    Supported operations: ``upper``, ``lower``, ``title``, ``capitalize``,
    ``reverse``, ``slugify``, ``base64_encode``, ``base64_decode``,
    ``camelcase``.

    Examples:
        transform_string("hello world", "title")       -> "Hello World"
        transform_string("Hello", "reverse")           -> "olleH"
        transform_string("Hello World", "slugify")     -> "hello-world"
        transform_string("hi there", "base64_encode")  -> "aGkgdGhlcmU="

    Args:
        text: The input string.
        operation: One of the operations listed above.

    Returns:
        The transformed string.
    """
    op = operation.lower()
    if op == "upper":
        return text.upper()
    if op == "lower":
        return text.lower()
    if op == "title":
        return text.title()
    if op == "capitalize":
        return text.capitalize()
    if op == "reverse":
        return text[::-1]
    if op == "slugify":
        return "".join(c if c.isalnum() or c in "- " else "" for c in text).strip().lower().replace(" ", "-")
    if op == "camelcase":
        parts = [p for p in text.replace("_", " ").replace("-", " ").split() if p]
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:]) if parts else ""
    if op == "base64_encode":
        import base64
        return base64.b64encode(text.encode("utf-8")).decode("ascii")
    if op == "base64_decode":
        import base64
        return base64.b64decode(text.encode("ascii")).decode("utf-8")
    raise ValueError(f"Unknown operation: {operation}")


@mcp.tool()
def kv_store(action: str, key: str, value: str = "") -> str:
    """Tiny in-memory key/value store for short-lived scratchpad state.

    Supported actions: ``set`` (write), ``get`` (read), ``delete`` (remove),
    ``list`` (return all keys, ``key`` is ignored).

    State is per-process and resets when the server restarts. Use this for
    transient scratchpad data the agent needs between tool calls within a
    single session – NOT for durable storage.

    Args:
        action: One of ``set``, ``get``, ``delete``, ``list``.
        key: The key to operate on.
        value: The value to set (only used when action == "set").

    Returns:
        For ``get``: the stored value (or empty string if missing).
        For ``set`` / ``delete``: a confirmation string.
        For ``list``: a newline-joined list of keys.
    """
    a = action.lower()
    if a == "set":
        _KV[key] = value
        return f"OK: set {key!r} ({len(value)} chars)"
    if a == "get":
        return _KV.get(key, "")
    if a == "delete":
        return f"OK: deleted {key!r}" if _KV.pop(key, None) is not None else f"WARN: {key!r} not found"
    if a == "list":
        return "\n".join(sorted(_KV.keys()))
    raise ValueError(f"Unknown action: {action}")


if __name__ == "__main__":
    mcp.run(transport="stdio")
