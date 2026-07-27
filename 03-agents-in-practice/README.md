# 03 - Agents in practice

Build, debug, and deploy real single-agent systems. By the end of this module, you can ship a conversational agent that uses tools, persists memory across sessions, requires human approval for risky actions, and streams responses to a client.

## What you will learn

- Conversational agents with the message-state pattern
- Persistence: in-memory, SQLite, Postgres checkpointers; the `Store` API for cross-thread memory
- Tool integration with `ToolNode`, dynamic tool loading, error handling
- Human-in-the-loop with `interrupt()` and `Command(resume=...)`
- Streaming: token streaming, event streaming, and when to use each
- LangGraph Studio for visual debugging

## Chapters

- [01 Conversational agents](01-conversational-agents.md) - the message-state pattern, the `add_messages` reducer, multi-turn memory
- [02 Persistence and memory](02-persistence-and-memory.md) - checkpointers, thread IDs, the `Store` API for long-term memory
- [03 Tool integration](03-tool-integration.md) - `ToolNode`, dynamic tool loading, tool error handling
- [04 Human-in-the-loop](04-human-in-the-loop.md) - `interrupt()`, `Command(resume=...)`, approval workflows
- [05 Streaming and UX](05-streaming-and-ux.md) - token streaming, event streaming, frontend patterns
- [06 LangGraph Studio](06-langgraph-studio.md) - visual debugging, step-through execution

## Prerequisites

- [02 LangGraph core](../02-langgraph-core/)

## Time

3 weeks at 2 to 3 hours per day.

## What is next

After this module, you are ready for [04 Tools and MCP](../04-tools-and-mcp/), where you will standardize your tools as MCP servers and consume them from any framework.
