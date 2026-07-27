# 04 - Tools and MCP

Tool design as a first-class skill, and the Model Context Protocol as the standard tool interop layer. By the end of this module, you can build MCP servers from scratch, consume them from LangGraph agents, and implement dynamic tool discovery.

## What you will learn

- Tool design as a prompt-engineering discipline (schemas, descriptions, error returns)
- The MCP protocol (JSON-RPC, the three primitives, the lifecycle)
- Building MCP servers in Python with the `mcp` SDK
- Consuming MCP servers from LangGraph via `langchain-mcp-adapters`
- Dynamic tool discovery and registries

## Chapters

- [01 Tool design](01-tool-design.md) - schemas, descriptions, when-to-use and when-not-to-use, error returns
- [02 MCP from scratch](02-mcp-from-scratch.md) - the protocol, the three primitives (tools, resources, prompts), the lifecycle
- [03 MCP servers](03-mcp-servers.md) - building filesystem, web search, and SQLite MCP servers in Python
- [04 MCP client in LangGraph](04-mcp-client-in-langgraph.md) - `MultiServerMCPClient`, dynamic tool loading, error handling
- [05 Tool discovery and registries](05-tool-discovery-and-registries.md) - dynamic registration, capability catalogs, versioning

## Prerequisites

- [03 Agents in practice](../03-agents-in-practice/)

## Time

2 to 3 weeks at 2 to 3 hours per day.

## What is next

After this module, you are ready for [05 Agentic patterns](../05-agentic-patterns/), where you will compose agents that use these tools in ReAct, plan-and-execute, reflexion, and supervisor patterns.
