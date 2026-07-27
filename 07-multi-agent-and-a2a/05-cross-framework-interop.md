# Cross-framework interop

Module: 07-multi-agent-and-a2a
Chapter: 05-cross-framework-interop
Status: beta
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Expose a LangGraph agent as an A2A server consumable by OpenAI Agents SDK and CrewAI
- Consume an OpenAI Agents SDK agent from LangGraph via A2A
- Consume a CrewAI agent from LangGraph via A2A
- Diagnose interop failures (schema mismatch, authentication, version skew)

## Prerequisites

- [04 A2A agent cards](04-a2a-agent-cards.md)

## Conceptual foundation

The promise of A2A is that an agent built with any framework can call agents built with any other framework. This chapter makes that promise concrete by showing the three interop paths:

1. LangGraph consuming OpenAI Agents SDK. The OpenAI agent is wrapped as an A2A server (using the `a2a-openai` adapter), and the LangGraph agent calls it via an A2A client tool.

2. LangGraph consuming CrewAI. The CrewAI crew is wrapped as an A2A server (using the `a2a-crewai` adapter), and the LangGraph agent calls it.

3. OpenAI Agents SDK consuming LangGraph. The LangGraph agent is wrapped as an A2A server (using the `a2a-langgraph` adapter), and the OpenAI agent calls it.

The pattern in all three cases: the "server" framework has an adapter that exposes its agents as A2A servers, and the "client" framework has a tool that calls A2A servers. The decoupling is at the protocol level; the adapters are thin.

The interop failures:

1. Schema mismatch. The server's skill input schema does not match what the client sends. Fix: validate the input against the schema before sending; use JSON Schema on both sides.

2. Authentication. The server requires auth the client does not provide. Fix: include the auth scheme in the Agent Card; the client reads it and authenticates.

3. Version skew. The server runs A2A v1.0, the client runs A2A v1.1. Fix: negotiate the version at handshake; fall back gracefully.

4. Latency. Cross-framework calls are HTTP, which adds latency. Fix: use streaming for long tasks; cache Agent Cards.

## Worked example

A LangGraph supervisor that delegates to an OpenAI Agents SDK agent and a CrewAI agent, both consumed via A2A. Full code in [`examples/cross_framework_demo.py`](../examples/cross_framework_demo.py).

```python
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import httpx

llm = ChatOpenAI(model="gpt-4o", temperature=0)

@tool
def call_openai_agent(task: str) -> str:
    """Delegate a coding task to the OpenAI coding agent (via A2A)."""
    response = httpx.post("http://localhost:8001/tasks/send", json={
        "task_id": f"task-{hash(task)}",
        "message": {"role": "user", "parts": [{"type": "text", "text": task}]},
    })
    return response.json()["artifacts"][0]["text"]

@tool
def call_crewai_agent(task: str) -> str:
    """Delegate a research task to the CrewAI research crew (via A2A)."""
    response = httpx.post("http://localhost:8002/tasks/send", json={
        "task_id": f"task-{hash(task)}",
        "message": {"role": "user", "parts": [{"type": "text", "text": task}]},
    })
    return response.json()["artifacts"][0]["text"]

from langgraph.prebuilt import create_react_agent

supervisor = create_react_agent(llm, tools=[call_openai_agent, call_crewai_agent],
    prompt="You coordinate a coding agent and a research agent. Delegate appropriately.")
```

## Evaluation

Test that: (1) the LangGraph supervisor can discover and call both remote agents, (2) the remote agents return valid artifacts, (3) the supervisor routes to the right agent based on the task.

## Production notes

In production, cross-framework interop is most valuable in organizations that have multiple teams using different frameworks. Team A built their agents with LangGraph; Team B built theirs with OpenAI's SDK; Team C uses CrewAI. A2A lets them compose without forcing a framework choice. The main production risk: the adapters are maintained by the community and may lag the framework versions. Pin adapter versions and test on every framework upgrade.

## Common pitfalls

- Not validating input schemas. Why: it works when both sides are correct. Fix: validate; schema mismatch is the most common interop failure.
- Not handling auth. Why: dev servers have no auth. Fix: include auth in the Agent Card; the client must read it.
- Assuming low latency. Why: dev servers are local. Fix: cross-framework calls are HTTP; account for the latency.

## Further reading

- [A2A adapters](https://github.com/a2aproject)
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [CrewAI](https://github.com/crewAIInc/crewAI)

## Checklist

- [ ] Expose a LangGraph agent as an A2A server
- [ ] Consume an OpenAI Agents SDK agent from LangGraph via A2A
- [ ] Consume a CrewAI agent from LangGraph via A2A
- [ ] Diagnose and fix a schema mismatch
