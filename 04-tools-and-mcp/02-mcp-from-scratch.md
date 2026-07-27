# MCP from scratch

Module: 04-tools-and-mcp
Chapter: 02-mcp-from-scratch
Status: stable
Last reviewed: 2026-07-27
Estimated time: 3 hours

## Learning objectives

- Explain the MCP protocol (JSON-RPC 2.0 over stdio or SSE)
- Name the three primitives (tools, resources, prompts) and when to use each
- Describe the MCP lifecycle (initialize, list, call)
- Build a minimal MCP server by hand (without the SDK) to understand the protocol

## Prerequisites

- [01 Tool design](01-tool-design.md)

## Conceptual foundation

The Model Context Protocol (MCP) is an open protocol for exposing tools, resources, and prompts to LLMs. It was announced by Anthropic in late 2024 and by mid-2026 had become the de facto standard for tool interop: every major agent framework (LangGraph, OpenAI Agents SDK, CrewAI, AutoGen) can consume MCP servers, and a growing ecosystem of pre-built MCP servers covers everything from filesystem access to database queries to web search.

The protocol is JSON-RPC 2.0 over either stdio (for local servers) or Server-Sent Events (for remote servers). The client (the agent framework) starts the server, sends JSON-RPC requests, and receives JSON-RPC responses. The protocol is transport-agnostic - the same server can be invoked over stdio locally or over SSE remotely.

The three primitives:

1. Tools. Functions the LLM can call. This is the most common primitive. A tool has a name, a description, a JSON Schema for arguments, and a handler that takes the arguments and returns a result.

2. Resources. Data the LLM can read. A resource has a URI (like `file:///path/to/file` or `db://table/row`), a MIME type, and content. Resources are for static or semi-static data that the LLM reads but does not "call" - a file, a database row, a config.

3. Prompts. Pre-defined prompt templates the LLM can use. A prompt has a name, a description, and a template. Prompts are less common in practice; they are useful when an MCP server wants to expose a curated prompt (e.g., "the right way to query this database").

The lifecycle:

1. Initialize. The client sends an `initialize` request with its protocol version and capabilities. The server responds with its protocol version and capabilities. This is the handshake.

2. List. The client sends a `tools/list`, `resources/list`, or `prompts/list` request. The server responds with the available tools, resources, or prompts. The client uses this to populate the LLM's tool list.

3. Call. The client sends a `tools/call` request with the tool name and arguments. The server executes the tool and returns the result (a list of content items, typically text).

The protocol is stateful within a session (the server can maintain state between calls) but stateless across sessions (a new connection is a fresh start). For stateful tools (a database connection, a file handle), the server manages the state internally.

Why MCP won: before MCP, every agent framework had its own tool format. A tool written for LangChain would not work with OpenAI's SDK or CrewAI. MCP decoupled tool authoring from agent framework - write the tool once as an MCP server, consume it from any framework. This is the same decoupling that HTTP achieved for web services.

## Worked example

A minimal MCP server written by hand (without the SDK) to show the protocol. This server exposes one tool: `echo`. It is not useful in production, but it shows every part of the protocol. Full code in [`examples/mcp_from_scratch_demo.py`](../examples/mcp_from_scratch_demo.py).

```python
import json
import sys

def handle_request(req: dict) -> dict:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "echo-server", "version": "0.1.0"},
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [{
                    "name": "echo",
                    "description": "Echoes the input back. Useful for testing.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string", "description": "The text to echo."}},
                        "required": ["text"],
                    },
                }]
            },
        }
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if name == "echo":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": args.get("text", "")}],
                    "isError": False,
                },
            }
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

# MCP servers read JSON-RPC requests from stdin and write responses to stdout
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    req = json.loads(line)
    resp = handle_request(req)
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()
```

In production, you would use the `mcp` SDK (next chapter) which handles the protocol plumbing. But reading this raw implementation is the best way to understand what the SDK does for you.

## Evaluation

Test the server by sending `initialize`, `tools/list`, and `tools/call` requests and verifying the responses. The eval is a set of JSON-RPC fixtures.

## Production notes

In production, never write an MCP server by hand - use the `mcp` SDK. The SDK handles protocol versioning, error codes, content types, and transport (stdio, SSE, WebSocket). The hand-written version is for understanding; the SDK version is for shipping.

## Common pitfalls

- Confusing tools, resources, and prompts. Why: they sound similar. Fix: tools are functions the LLM calls; resources are data the LLM reads; prompts are templates the LLM uses.
- Writing MCP servers by hand in production. Why: it works for simple cases. Fix: use the SDK.

## Further reading

- [MCP specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Anthropic MCP announcement](https://www.anthropic.com/news/model-context-protocol)

## Checklist

- [ ] Explain the three MCP primitives and when to use each
- [ ] Describe the initialize-list-call lifecycle
- [ ] Read the hand-written MCP server and explain what each method handler does
- [ ] Run the hand-written server and call it from a minimal JSON-RPC client
