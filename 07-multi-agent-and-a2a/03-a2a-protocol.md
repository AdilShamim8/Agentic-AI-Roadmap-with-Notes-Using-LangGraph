# A2A protocol

Module: 07-multi-agent-and-a2a
Chapter: 03-a2a-protocol
Status: beta
Last reviewed: 2026-07-27
Estimated time: 3 hours

## Learning objectives

- Explain the A2A protocol (Agent-to-Agent, announced by Google in 2025)
- Describe the Agent Card (the JSON manifest that advertises an agent's capabilities)
- Describe the task lifecycle (submitted, working, input-required, completed, failed)
- Build a minimal A2A server and client by hand (without the SDK) to understand the protocol

## Prerequisites

- [02 Agent handoffs](02-agent-handoffs.md)

## Conceptual foundation

The Agent-to-Agent (A2A) protocol is to agents what MCP is to tools: an open protocol that decouples agent authoring from agent framework. A2A was announced by Google in 2025 and by mid-2026 was being adopted by every major agent framework. The promise: an agent built with LangGraph can call an agent built with OpenAI's Agents SDK, which can call an agent built with CrewAI, all speaking the same protocol.

The protocol is HTTP-based, with JSON payloads. The core concepts:

1. Agent Card. A JSON document hosted at a well-known URL (typically `/.well-known/agent.json`) that advertises the agent's capabilities, endpoints, and authentication requirements. The Agent Card is how agents discover each other.

2. Task. The unit of work in A2A. A client sends a task to an agent; the agent works on it and returns a result. Tasks have a lifecycle: `submitted` (received), `working` (in progress), `input-required` (agent needs more input from the client), `completed` (done), `failed` (error), `canceled` (client canceled).

3. Message. A message in a task, from either the client or the agent. Messages have a role (`user` or `agent`) and a list of parts (text, file, data).

4. Part. A piece of a message. Text parts are the most common; file parts carry binary data; data parts carry structured JSON.

5. Artifact. The output of a task. A task can produce multiple artifacts (e.g., a report text and a chart image).

The lifecycle of a typical A2A interaction:

1. The client fetches the agent's Agent Card from `/.well-known/agent.json`.
2. The client sends a `tasks/send` request with the task input.
3. The agent starts working and returns a `working` status.
4. (Optional) The agent sends an `input-required` status, asking for clarification. The client responds with another `tasks/send`.
5. The agent completes and returns a `completed` status with artifacts.

A2A supports both synchronous (the request blocks until the task completes) and asynchronous (the request returns immediately, the client polls or receives webhooks) modes. For long-running tasks, asynchronous is required.

Why A2A matters: it is the interop layer that makes multi-framework agent systems possible. Without A2A, an agent built with framework X can only call agents built with framework X. With A2A, an agent built with any framework can call agents built with any other framework. This is the same decoupling that HTTP achieved for web services, and it will have the same effect on the agent ecosystem.

## Worked example

A minimal A2A server (FastAPI) and client (httpx), without the SDK, to show the protocol. Full code in [`examples/a2a_from_scratch_demo.py`](../examples/a2a_from_scratch_demo.py).

```python
# Server (FastAPI)
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

AGENT_CARD = {
    "name": "echo-agent",
    "description": "Echoes the input back. Useful for testing.",
    "version": "0.1.0",
    "capabilities": {"streaming": False, "pushNotifications": False},
    "skills": [{"id": "echo", "description": "Echoes the input."}],
}

@app.get("/.well-known/agent.json")
def agent_card():
    return AGENT_CARD

class TaskRequest(BaseModel):
    task_id: str
    message: str

@app.post("/tasks/send")
def send_task(req: TaskRequest):
    # Echo: return the input as the artifact
    return {
        "task_id": req.task_id,
        "status": {"state": "completed"},
        "artifacts": [{"type": "text", "text": f"Echo: {req.message}"}],
    }

# Client (httpx)
import httpx

def call_a2a_agent(base_url: str, message: str):
    # 1. Fetch the Agent Card
    card = httpx.get(f"{base_url}/.well-known/agent.json").json()
    print(f"Agent: {card['name']} - {card['description']}")

    # 2. Send a task
    response = httpx.post(f"{base_url}/tasks/send", json={
        "task_id": "task-001",
        "message": message,
    })
    result = response.json()
    print(f"Status: {result['status']['state']}")
    print(f"Artifact: {result['artifacts'][0]['text']}")

# call_a2a_agent("http://localhost:8000", "Hello, A2A!")
```

In production, you would use the A2A SDK (`a2a-python`), which handles the protocol plumbing, authentication, streaming, and push notifications.

## Evaluation

Test the server by: (1) fetching the Agent Card, (2) sending a task, (3) verifying the artifact. The eval is a set of HTTP fixtures.

## Production notes

In production, A2A servers are typically deployed as HTTP services (behind a load balancer, with authentication, with rate limiting). The Agent Card is served at a well-known URL. The client discovers the agent, sends tasks, and receives artifacts. The same patterns as any HTTP API apply: authentication, rate limiting, observability, versioning.

The main production risk: A2A is new (2025-2026), and the spec is evolving. Pin the protocol version your server and client use. Do not assume the spec is stable yet.

## Common pitfalls

- Confusing A2A with MCP. Why: they sound similar. Fix: MCP is for tools (functions); A2A is for agents (which may use tools).
- Not serving the Agent Card at the well-known URL. Why: it works when the client knows the URL. Fix: use `/.well-known/agent.json`; that is how discovery works.
- Synchronous-only for long-running tasks. Why: it works in dev. Fix: use async mode for tasks that take more than a few seconds.

## Further reading

- [A2A specification](https://google.github.io/A2A/)
- [google/A2A on GitHub](https://github.com/google/A2A)
- [A2A Python SDK](https://github.com/a2aproject/a2a-python)

## Checklist

- [ ] Explain the A2A protocol and how it differs from MCP
- [ ] Describe the Agent Card and the task lifecycle
- [ ] Build a minimal A2A server and client by hand
- [ ] Discover an agent by fetching its Agent Card
