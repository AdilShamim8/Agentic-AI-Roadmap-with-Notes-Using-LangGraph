"""MCP filesystem server.

Exposes two tools over the Model Context Protocol:
- read_file: read the contents of a file
- list_directory: list files in a directory

Run:
    python examples/mcp_filesystem_server.py

The server reads JSON-RPC requests from stdin and writes responses to
stdout. It is consumed by an MCP client (see mcp_client_demo.py, which
you would write using langchain-mcp-adapters).

Dependencies:
    pip install mcp anyio
"""

from __future__ import annotations

import os
from typing import Any

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

server = Server("filesystem-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List the tools this server exposes."""
    return [
        Tool(
            name="read_file",
            description=(
                "Read the contents of a file. Use when the user asks to "
                "read, view, or display a file. Do not use for directories "
                "(use list_directory instead). Returns the file contents as text."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file, e.g. '/home/user/notes.txt'.",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="list_directory",
            description=(
                "List files in a directory. Use when the user asks what "
                "files are in a folder, or to browse a directory. Returns "
                "one filename per line."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the directory.",
                    }
                },
                "required": ["path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle a tool call. Returns the result as a list of TextContent."""
    try:
        if name == "read_file":
            path = arguments["path"]
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return [TextContent(type="text", text=content)]
        if name == "list_directory":
            path = arguments["path"]
            entries = sorted(os.listdir(path))
            return [TextContent(type="text", text="\n".join(entries))]
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        # Return the error to the LLM, do not raise.
        return [TextContent(type="text", text=f"Error: {e}")]


async def main() -> None:
    """Run the MCP server over stdio."""
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
