# Tool discovery and registries

Module: 04-tools-and-mcp
Chapter: 05-tool-discovery-and-registries
Status: beta
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement dynamic tool loading (the tool list is determined at runtime)
- Build a tool registry that MCP servers register with and agents query
- Handle tool versioning (multiple versions of the same tool, backward compatibility)
- Reason about the trajectory of tool registries (the "npm for MCP" pattern)

## Prerequisites

- [04 MCP client in LangGraph](04-mcp-client-in-langgraph.md)

## Conceptual foundation

Dynamic tool loading is the pattern where the tool list is not fixed at agent-creation time but is determined at runtime based on context. The simplest form: an admin user sees more tools than a regular user. A more advanced form: the agent queries a tool registry at runtime, finds tools relevant to the current task, and loads only those. The most advanced form: the agent uses a "tool discovery" tool that searches a registry and returns tool descriptions, then the agent decides which to load.

The tool registry is the infrastructure that makes dynamic loading work. A registry is a service that MCP servers register with (publishing their tool list) and agents query (retrieving tool lists filtered by capability, version, or namespace). The registry is to MCP servers what npm is to JavaScript packages: a catalog with metadata, versioning, and discovery.

In 2026, tool registries are emerging but not yet standardized. The MCP specification does not include a registry protocol; the community is converging on a few patterns:

1. Static registry. A JSON file listing available MCP servers and their capabilities. The agent reads the file at startup and connects to the relevant servers. Simple, but requires manual updates.

2. Directory service. A running service that MCP servers register with (heartbeat-style) and agents query. More complex, but supports dynamic addition and removal of servers.

3. Federated discovery. Agents discover servers via DNS, mDNS, or a gossip protocol. Used in multi-agent systems where agents are deployed across a network.

Tool versioning is the hard part. When a tool's schema changes, agents that depend on the old schema break. The patterns:

- Semantic versioning. Tools have a major.minor.patch version. Breaking schema changes are major version bumps. Agents request a specific major version.
- Capability negotiation. The agent and server negotiate which features they support at `initialize` time. The agent falls back gracefully if a feature is missing.
- Multiple versions. The registry hosts multiple versions of the same tool. Agents request the version they were tested against.

## Worked example

A static-registry implementation: a JSON file listing MCP servers, an agent that reads the registry and loads relevant tools. Full code in [`examples/tool_registry_demo.py`](../examples/tool_registry_demo.py).

```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "python",
      "args": ["examples/mcp_filesystem_server.py"],
      "transport": "stdio",
      "capabilities": ["read_file", "list_directory"],
      "version": "1.0.0"
    },
    {
      "name": "web_search",
      "command": "python",
      "args": ["examples/mcp_websearch_server.py"],
      "transport": "stdio",
      "capabilities": ["search"],
      "version": "1.2.0"
    }
  ]
}
```

```python
import json
from langchain_mcp_adapters.client import MultiServerMCPClient

async def load_tools_for_capabilities(capabilities: list[str]):
    registry = json.load(open("tool_registry.json"))
    needed = {c for c in capabilities}
    servers = {}
    for s in registry["servers"]:
        if needed & set(s["capabilities"]):
            servers[s["name"]] = {
                "command": s["command"],
                "args": s["args"],
                "transport": s["transport"],
            }
    client = MultiServerMCPClient(servers)
    await client.__aenter__()
    return client.get_tools(), client
```

## Evaluation

Test that: (1) the registry correctly filters servers by capability, (2) the agent loads only the requested tools, (3) version mismatches produce a clear error.

## Production notes

In production, the registry becomes a critical piece of infrastructure. If the registry is down, agents cannot discover tools. The patterns: cache the registry locally (agents fall back to the cache if the registry is unavailable), run the registry in high-availability mode (multiple replicas, a load balancer), and monitor registry health as part of agent uptime.

## Common pitfalls

- Hardcoding the server list in the agent. Why: it works in dev. Fix: use a registry; it decouples agent deployment from tool deployment.
- Not versioning tools. Why: it works when there is one agent. Fix: version from day one; the cost of adding it later is much higher.
- Not handling registry downtime. Why: the registry is "always up" in dev. Fix: cache locally and degrade gracefully.

## Further reading

- [MCP specification](https://spec.modelcontextprotocol.io/)
- [MCP servers registry](https://github.com/modelcontextprotocol/servers)

## Checklist

- [ ] Implement a static tool registry as a JSON file
- [ ] Build an agent that loads tools dynamically based on requested capabilities
- [ ] Add versioning to the registry and handle version mismatches
- [ ] Cache the registry locally and handle registry downtime
