# Persistence and memory

Module: 03-agents-in-practice
Chapter: 02-persistence-and-memory
Status: stable
Last reviewed: 2026-07-27
Estimated time: 3 hours

## Learning objectives

- Choose between `MemorySaver`, `SqliteSaver`, and `PostgresSaver` based on deployment needs
- Use thread IDs to scope conversations
- Use the `Store` API for cross-thread, long-term memory
- Diagnose and fix the three persistence failure modes (lost state on restart, cross-thread leakage, memory bloat)

## Prerequisites

- [01 Conversational agents](01-conversational-agents.md)

## Conceptual foundation

Persistence in LangGraph has two layers: checkpointing and the Store. They serve different purposes and you need both for a production agent.

Checkpointing is short-term persistence. Every node execution saves the current state to a checkpointer, keyed by thread ID. If the agent is interrupted (by a crash, by `interrupt()`, by a human pause), the checkpointer allows the agent to resume from the last completed node. Checkpointing is what makes agents durable. The three checkpointers:

- `MemorySaver` - in-memory only. Lost on process restart. Use for dev and tests.
- `SqliteSaver` - SQLite file on disk. Survives restarts. Use for single-instance production.
- `PostgresSaver` - Postgres database. Survives restarts, supports multiple instances. Use for production with more than one worker.

The Store is long-term persistence. It is a key-value store that is not scoped to a thread. You use it to remember things across conversations: user preferences, facts learned about the user, long-term project context. The Store is the foundation of "memory" in the colloquial sense - the thing that makes an agent feel like it knows you.

The pattern for using the Store: after each conversation, a "memory extraction" node runs that pulls facts from the conversation and writes them to the Store under the user's ID. On the next conversation, a "memory retrieval" node reads the Store and injects relevant facts into the system prompt. This is the simplest form of long-term memory and it is surprisingly effective.

The three persistence failure modes:

1. Lost state on restart. Symptom: the agent forgets the conversation when the server restarts. Cause: using `MemorySaver` in production. Fix: use `PostgresSaver`.

2. Cross-thread leakage. Symptom: user A's conversation bleeds into user B's. Cause: reusing thread IDs across users. Fix: thread IDs must be unique per user-session; use `f"{user_id}-{session_id}"`.

3. Memory bloat. Symptom: the Store grows unboundedly, retrieval becomes slow. Cause: never pruning. Fix: implement a memory-pruning step that removes stale or low-importance memories.

## Worked example

A conversational agent with Postgres checkpointing and Store-based long-term memory. Full code in [`examples/persistence_demo.py`](../examples/persistence_demo.py).

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from psycopg import Connection

# Production: use a real Postgres connection
# conn = Connection("postgresql://user:pass@localhost:5432/agentic")
# checkpointer = PostgresSaver(conn)
# For dev: in-memory
checkpointer = PostgresSaver.from_conn_string("postgresql://user:pass@localhost:5432/agentic")  # or MemorySaver() for dev
store = InMemoryStore()  # production: use a real store backend

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def get_user_memories(user_id: str) -> str:
    items = store.get(namespace=("memories", user_id), key="facts")
    if not items or not items.value:
        return ""
    return "\n".join(f"- {fact}" for fact in items.value)

def save_user_memory(user_id: str, fact: str) -> None:
    items = store.get(namespace=("memories", user_id), key="facts")
    facts = items.value if items else []
    facts.append(fact)
    store.put(namespace=("memories", user_id), key="facts", value=facts)

# In a real agent, you would add nodes that call these functions.
# For brevity, this example shows only the persistence layer.
```

## Evaluation

Test that: (1) a conversation resumed with the same thread ID has the prior context, (2) a conversation with a different thread ID does not, (3) facts saved to the Store are retrievable in a later conversation.

## Production notes

In production, Postgres checkpointing is the default. The schema is managed by LangGraph; you just provide the connection. The Store in production should also be backed by Postgres (or another durable store) - `InMemoryStore` is for dev only. The memory-extraction and memory-retrieval nodes should be cheap (small LLM calls or rule-based) to avoid adding latency to every turn.

## Common pitfalls

- Using `MemorySaver` in production. Why: it works in dev. Fix: always use PostgresSaver for production.
- Reusing thread IDs across users. Why: it works in single-user dev. Fix: thread IDs are per-user-session.
- Not pruning the Store. Why: it works for the first 1000 users. Fix: implement a pruning job.

## Further reading

- [LangGraph checkpointers](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph Store API](https://langchain-ai.github.io/langgraph/concepts/memory/)

## Checklist

- [ ] Configure a PostgresSaver for a production agent
- [ ] Use thread IDs scoped to user-session
- [ ] Implement memory extraction and retrieval with the Store
- [ ] Add a pruning step for stale memories
