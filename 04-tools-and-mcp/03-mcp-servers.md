# MCP servers

Module: 04-tools-and-mcp
Chapter: 03-mcp-servers
Status: stable
Last reviewed: 2026-07-27
Estimated time: 3 hours

## Learning objectives

- Build an MCP server with the `mcp` Python SDK
- Implement the filesystem, web search, and SQLite servers (the three canonical examples)
- Expose tools, resources, and prompts from a single server
- Test an MCP server in isolation (without an agent)

## Prerequisites

- [02 MCP from scratch](02-mcp-from-scratch.md)

## Conceptual foundation

The `mcp` Python SDK abstracts the JSON-RPC plumbing. You write Python functions decorated with `@mcp.tool()`, `@mcp.resource()`, or `@mcp.prompt()`, and the SDK handles the protocol. The server runs over stdio by default (for local consumption) and can be configured for SSE or WebSocket for remote consumption.

The three canonical MCP servers that every agentic AI engineer should build at least once:

1. Filesystem server. Exposes a directory as resources (`file:///path/to/file`) and a `read_file` / `write_file` / `list_directory` tool set. This is the simplest server and the right starting point.

2. Web search server. Wraps a search API (Tavily, Brave, or a simple `httpx.get` to a search engine) as a `search` tool. This is the server you will use most in real agents.

3. SQLite server. Wraps a SQLite database as a `query` tool and exposes tables as resources. This is the server that teaches you how to handle structured data and SQL injection risks.

The patterns that generalize across all three:

- Each tool has a clear name, a description with when-to-use and when-not-to-use, a JSON Schema for arguments, and a handler that returns a list of content items (usually text).
- Each tool catches its own errors and returns them as content items, not exceptions.
- The server is started with `mcp.run()` and reads JSON-RPC from stdin / writes to stdout.
- The server can be tested by sending JSON-RPC requests directly, without an agent.

## Worked example

A filesystem MCP server built with the SDK. Full code in [`examples/mcp_filesystem_server.py`](../examples/mcp_filesystem_server.py).

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import os
import anyio

server = Server("filesystem-server")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="read_file",
            description=(
                "Read the contents of a file. Use when the user asks to read, "
                "view, or display a file. Do not use for directories (use "
                "list_directory instead). Returns the file contents as text."
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
                "List files in a directory. Use when the user asks what files "
                "are in a folder, or to browse a directory. Returns one filename per line."
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
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "read_file":
            path = arguments["path"]
            with open(path, "r") as f:
                content = f.read()
            return [TextContent(type="text", text=content)]
        if name == "list_directory":
            path = arguments["path"]
            entries = os.listdir(path)
            return [TextContent(type="text", text="\n".join(entries))]
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    anyio.run(main)
```

The web search and SQLite servers follow the same pattern. See [`examples/mcp_websearch_server.py`](../examples/mcp_websearch_server.py) and [`examples/mcp_sqlite_server.py`](../examples/mcp_sqlite_server.py) for full implementations.

## Evaluation

Test each server by sending `tools/list` and `tools/call` requests and verifying the responses. For the filesystem server, create a temp directory with known files and verify `read_file` and `list_directory` return the expected content. For the web search server, mock the search API and verify the tool returns mocked results. For the SQLite server, create an in-memory database with known data and verify `query` returns the expected rows.

## Production notes

In production, MCP servers are usually run as separate processes from the agent. The agent framework spawns the server (or connects to a running server over SSE), lists its tools, and calls them as needed. This decoupling means a single MCP server can be shared across multiple agents, and a single agent can consume tools from multiple MCP servers. The pattern is the same as microservices: each server owns its own resources (filesystem, database, API keys) and exposes a stable interface.

## Common pitfalls

- Raising exceptions from tool handlers. Why: it is the Python idiom. Fix: catch and return as content items.
- Not validating tool arguments. Why: the LLM "usually" passes valid args. Fix: validate; SQL injection via tool arguments is a real vulnerability.
- Hardcoding API keys in the server. Why: it works in dev. Fix: read from environment variables.

## Further reading

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP servers registry](https://github.com/modelcontextprotocol/servers)

## Checklist

- [ ] Build a filesystem MCP server with `read_file` and `list_directory` tools
- [ ] Build a web search MCP server
- [ ] Build a SQLite MCP server with a `query` tool
- [ ] Test each server by sending JSON-RPC requests directly
