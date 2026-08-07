"""MCP server package.

Each module in this package is an independent stdio MCP server, spawned on
demand by the agent via the entries in ``registry.json``::

    python3 -m mcp_servers.filesystem_server
    python3 -m mcp_servers.calculator_server
    python3 -m mcp_servers.sqlite_server
    python3 -m mcp_servers.search_server
    python3 -m mcp_servers.custom_server

Every server uses ``mcp.server.fastmcp.FastMCP`` so the protocol wiring is
identical – only the tool definitions differ.
"""

__all__ = [
    "filesystem_server",
    "calculator_server",
    "sqlite_server",
    "search_server",
    "custom_server",
]
