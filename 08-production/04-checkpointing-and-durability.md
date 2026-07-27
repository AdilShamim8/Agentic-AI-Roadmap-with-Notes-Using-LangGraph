# Checkpointing and durability

Module: 08-production
Chapter: 04-checkpointing-and-durability
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Configure PostgresSaver for durable checkpointing
- Resume an agent after a process crash
- Reason about the durability guarantees (what is saved, when, and what can still be lost)
- Implement idempotent tool calls so retries do not cause duplicate side effects

## Prerequisites

- [02 Docker deployment](02-docker-deployment.md)

## Conceptual foundation

Checkpointing is what makes an agent durable. After every node execution, LangGraph saves the current state to the checkpointer. If the agent is interrupted (by a crash, by `interrupt()`, by a human pause), the checkpointer allows the agent to resume from the last completed node.

The durability guarantees:

1. State is saved after every node. If a node completes, its state updates are persisted. If the next node fails, the agent can resume from the saved state.

2. In-flight node execution is not saved. If a node is mid-execution when the process crashes, the work done in that node is lost. The agent resumes by re-running the node from the beginning.

3. Tool calls within a node are not idempotent by default. If a node calls `issue_refund` and the process crashes before the node completes, the refund was issued but the state was not saved. On resume, the node re-runs, and the refund is issued again. This is the duplicate-side-effect problem.

The duplicate-side-effect problem is the hardest part of durable agent execution. The solutions:

1. Idempotent tools. The tool itself handles duplicate calls safely. For `issue_refund`, this means the refund API accepts an idempotency key and returns the original result if called twice with the same key. Most modern APIs support this.

2. At-least-once with deduplication. The agent logs every tool call with a unique ID. On resume, it checks the log and skips already-completed calls. This requires the agent to use a transactional log.

3. Two-phase commit. The agent prepares the tool call (saves the intent), executes it, and confirms (saves the result). On resume, if the intent is saved but the result is not, the agent re-executes. This is complex and rarely worth it.

For most agents, idempotent tools are the right answer. Work with the tool's API to ensure idempotency (use idempotency keys, check current state before acting, etc.).

## Worked example

Configuring PostgresSaver and resuming after a crash. Full code in [`examples/durability_demo.py`](../examples/durability_demo.py).

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from psycopg import Connection

@tool
def issue_refund(order_id: str, amount: float, idempotency_key: str) -> str:
    """Issue a refund. The idempotency_key prevents duplicate refunds on retry."""
    # In production, call the refund API with the idempotency key
    return f"Refund of ${amount} for {order_id} processed (key: {idempotency_key})"

conn = Connection("postgresql://postgres:postgres@localhost:5432/langgraph")
checkpointer = PostgresSaver(conn)
checkpointer.setup()  # creates the schema if it does not exist

llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent = create_react_agent(llm, tools=[issue_refund], checkpointer=checkpointer)

config = {"configurable": {"thread_id": "user-001"}}
result = agent.invoke({"messages": [{"role": "user", "content": "Refund order ACME-123 for $50"}]}, config=config)

# If the process crashes here, the agent can resume:
# result = agent.invoke({"messages": []}, config=config)
# The checkpointer restores the state, and the agent continues.
```

## Evaluation

Test that: (1) the agent's state survives a process restart, (2) resuming with the same thread_id continues the conversation, (3) idempotent tools do not produce duplicate side effects on resume.

## Production notes

In production, the PostgresSaver schema grows over time (every node execution adds a row). Implement a retention policy: keep checkpoints for 30 days, then delete. For long-running agents (hours to days), this is essential - a single agent's checkpoints can occupy megabytes.

The most common production failure: a non-idempotent tool called in a node that crashes mid-execution. The refund is issued twice; the user is charged twice (or refunded twice). The fix: every tool with side effects must be idempotent. This is non-negotiable for production agents.

## Common pitfalls

- Using MemorySaver in production. Why: it works in dev. Fix: use PostgresSaver.
- Non-idempotent side-effecting tools. Why: "crashes are rare." Fix: make every side-effecting tool idempotent.
- Not implementing checkpoint retention. Why: the schema is small at first. Fix: implement retention from day one.

## Further reading

- [LangGraph checkpointers](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [PostgresSaver](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres.PostgresSaver)

## Checklist

- [ ] Configure PostgresSaver for a production agent
- [ ] Test that state survives a process restart
- [ ] Make every side-effecting tool idempotent (use idempotency keys)
- [ ] Implement a checkpoint retention policy
