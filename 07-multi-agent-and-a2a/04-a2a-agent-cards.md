# A2A agent cards

Module: 07-multi-agent-and-a2a
Chapter: 04-a2a-agent-cards
Status: beta
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Author an Agent Card that accurately advertises an agent's capabilities
- Expose a LangGraph agent as an A2A server
- Consume an A2A agent from a LangGraph client
- Use the A2A registry for discovery

## Prerequisites

- [03 A2A protocol](03-a2a-protocol.md)

## Conceptual foundation

The Agent Card is the public face of an A2A agent. It is a JSON document at `/.well-known/agent.json` that tells potential clients: who I am, what I can do, how to call me, what authentication I require. A well-authored Agent Card is the difference between an agent that gets used and one that does not.

The required fields:

- `name`: the agent's name (e.g., "research-agent").
- `description`: a one-paragraph description of what the agent does. This is what clients read to decide whether to use the agent.
- `version`: the agent's version (semantic versioning).
- `capabilities`: what the agent supports (streaming, push notifications, async tasks).
- `skills`: a list of skills the agent has. Each skill has an id, a description, and (optionally) input/output schemas.
- `endpoints`: the URLs for `tasks/send`, `tasks/get`, etc.
- `authentication`: the authentication scheme (none, API key, OAuth).

The `skills` field is the most important. It is the agent's menu. Each skill should be specific enough that a client can decide whether the agent can handle a given task. "Research" is too vague; "Research a topic using web search and return a cited summary" is specific.

## Worked example

Exposing a LangGraph research agent as an A2A server. Full code in [`examples/a2a_server_demo.py`](../examples/a2a_server_demo.py).

```python
from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

app = FastAPI()

@tool
def web_search(query: str) -> str:
    """Search the web."""
    return f"[Results for: {query}]"

llm = ChatOpenAI(model="gpt-4o", temperature=0)
research_agent = create_react_agent(llm, tools=[web_search], prompt="You are a research agent.")

AGENT_CARD = {
    "name": "research-agent",
    "description": "Researches a topic using web search and returns a cited summary.",
    "version": "1.0.0",
    "capabilities": {"streaming": False, "pushNotifications": False, "asyncTasks": True},
    "skills": [{
        "id": "research",
        "description": "Research a topic and return a summary with citations.",
        "inputSchema": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]},
        "outputSchema": {"type": "object", "properties": {"summary": {"type": "string"}, "citations": {"type": "array"}}},
    }],
    "endpoints": {"tasksSend": "/tasks/send", "tasksGet": "/tasks/get"},
    "authentication": {"schemes": ["bearer"]},
}

@app.get("/.well-known/agent.json")
def agent_card():
    return AGENT_CARD

@app.post("/tasks/send")
async def send_task(req: dict):
    topic = req["message"]["parts"][0]["text"]
    result = await research_agent.ainvoke({"messages": [{"role": "user", "content": f"Research: {topic}"}]})
    summary = result["messages"][-1].content
    return {
        "task_id": req["task_id"],
        "status": {"state": "completed"},
        "artifacts": [{"type": "text", "text": summary}],
    }
```

Consuming the agent from a LangGraph client:

```python
import httpx
from langchain_core.tools import tool

@tool
def call_research_agent(topic: str) -> str:
    """Research a topic using the remote research agent. Returns a summary."""
    # 1. Fetch the Agent Card (cached in production)
    card = httpx.get("http://localhost:8000/.well-known/agent.json").json()

    # 2. Send a task
    response = httpx.post(card["endpoints"]["tasksSend"], json={
        "task_id": f"task-{hash(topic)}",
        "message": {"role": "user", "parts": [{"type": "text", "text": topic}]},
    }, headers={"Authorization": "Bearer ..."})

    result = response.json()
    return result["artifacts"][0]["text"]
```

## Evaluation

Test that: (1) the Agent Card is served correctly, (2) a client can discover the agent and send a task, (3) the agent returns a valid artifact, (4) the client can use the agent as a tool in a larger graph.

## Production notes

In production, A2A servers are deployed like any HTTP service: behind a load balancer, with authentication, with rate limiting, with observability. The Agent Card is cached by clients (it does not change often). The task lifecycle is asynchronous for long-running tasks (the client polls or receives a webhook). Authentication is typically bearer token or OAuth.

## Common pitfalls

- Vague skill descriptions. Why: the author knows what the agent does. Fix: write specific skill descriptions; they are how clients decide.
- Not serving the Agent Card at the well-known URL. Why: it works when the URL is known. Fix: use `/.well-known/agent.json`.
- Synchronous-only for long tasks. Why: it works in dev. Fix: use async mode.

## Further reading

- [A2A specification](https://google.github.io/A2A/)
- [LangGraph A2A integration](https://langchain-ai.github.io/langgraph/how-tos/a2a/)

## Checklist

- [ ] Author an Agent Card with specific skill descriptions
- [ ] Expose a LangGraph agent as an A2A server
- [ ] Consume an A2A agent from a LangGraph client as a tool
- [ ] Use async mode for long-running tasks
