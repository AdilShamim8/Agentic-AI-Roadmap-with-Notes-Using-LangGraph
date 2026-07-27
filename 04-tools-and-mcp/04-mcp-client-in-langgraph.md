# MCP client in LangGraph

Module: 04-tools-and-mcp
Chapter: 04-mcp-client-in-langgraph
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Use `MultiServerMCPClient` to consume MCP servers from a LangGraph agent
- Combine MCP tools with native LangGraph tools in the same agent
- Handle MCP server errors (server down, tool not found, malformed response)
- Measure tool-selection accuracy when the tool list comes from MCP

## Prerequisites

- [03 MCP servers](03-mcp-servers.md)
- [01 Conversational agents](../03-agents-in-practice/01-conversational-agents.md)

## Conceptual foundation

`langchain-mcp-adapters` is the bridge between MCP servers and LangGraph agents. It provides `MultiServerMCPClient`, an async context manager that connects to one or more MCP servers, lists their tools, and returns them as LangChain `Tool` objects that you can pass to `create_react_agent` or use in a custom StateGraph.

The client handles the protocol plumbing: it spawns the server process (for stdio transport) or connects via SSE, sends the `initialize` and `tools/list` requests, and translates MCP tool definitions into LangChain tool definitions. From the agent's perspective, MCP tools look identical to native tools - the agent does not know or care whether a tool is local or remote.

The pattern:

```python
async with MultiServerMCPClient({...}) as client:
    tools = client.get_tools()
    agent = create_react_agent(llm, tools=tools)
    result = await agent.ainvoke({"messages": [...]})
```

The `async with` is important: it ensures the MCP server connections are closed when the block exits. In a long-running application (a web server), you would keep the client open for the lifetime of the application and reuse it across requests.

You can mix MCP tools with native LangGraph tools in the same agent. This is useful when some tools are best implemented as MCP servers (shared across agents, written in another language) and others are best implemented inline (cheap, agent-specific, no IPC overhead).

## Worked example

An agent that consumes the filesystem and web search MCP servers from the previous chapter. Full code in [`examples/mcp_client_demo.py`](../examples/mcp_client_demo.py).

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

async def main():
    async with MultiServerMCPClient({
        "filesystem": {
            "command": "python",
            "args": ["examples/mcp_filesystem_server.py"],
            "transport": "stdio",
        },
        "web_search": {
            "command": "python",
            "args": ["examples/mcp_websearch_server.py"],
            "transport": "stdio",
            "env": {"TAVILY_API_KEY": "..."},
        },
    }) as mcp_client:
        tools = mcp_client.get_tools()
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        agent = create_react_agent(llm, tools=tools)

        result = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Search for LangGraph news and save a summary to notes.txt"
            }]
        })
        print(result["messages"][-1].content)

asyncio.run(main())
```

## Evaluation

A golden dataset of 20 requests, each requiring a tool from one of the MCP servers. The evaluator checks tool-selection accuracy and argument correctness. Compare the accuracy against the same tools implemented natively (not via MCP) - they should be equivalent, since the tool descriptions are the same.

## Production notes

In production, the MCP client is a long-lived object (not opened and closed per request, as in the example). The client manages a pool of server connections and reuses them. For SSE transport (remote servers), the client handles reconnection on network failures. For stdio transport (local servers), the client restarts the server process if it crashes. These are the production concerns that `langchain-mcp-adapters` handles for you.

The most common production issue: an MCP server becomes slow or unresponsive, and the agent blocks waiting for a tool call. The fix: set a timeout on every tool call (the client supports this) and fall back to an error message if the timeout is hit.

## Common pitfalls

- Opening and closing the client per request. Why: it works in dev. Fix: keep the client open for the application lifetime.
- Not setting tool-call timeouts. Why: it works when servers are fast. Fix: set a timeout and handle it.
- Mixing MCP and native tools without realizing the tool list is dynamic. Why: the tool list changes when servers are added or removed. Fix: re-fetch the tool list when the server configuration changes.

## Further reading

- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [LangGraph MCP integration](https://langchain-ai.github.io/langgraph/how-tos/mcp/)

## Checklist

- [ ] Use `MultiServerMCPClient` to consume two MCP servers from one agent
- [ ] Mix MCP tools with native LangGraph tools
- [ ] Set a tool-call timeout and handle the timeout case
- [ ] Measure tool-selection accuracy with MCP-sourced tools
