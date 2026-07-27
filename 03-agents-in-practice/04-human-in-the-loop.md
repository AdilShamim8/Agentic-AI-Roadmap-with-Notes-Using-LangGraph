# Human-in-the-loop

Module: 03-agents-in-practice
Chapter: 04-human-in-the-loop
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Use `interrupt()` to pause an agent and `Command(resume=...)` to continue
- Build an approval workflow (agent proposes, human approves, agent executes)
- Implement review-and-edit (agent proposes, human edits, agent uses the edited version)
- Choose between HITL and autonomous execution based on action risk

## Prerequisites

- [01 Conversational agents](01-conversational-agents.md)
- [02 Persistence and memory](02-persistence-and-memory.md)

## Conceptual foundation

Human-in-the-loop (HITL) is the pattern where an agent pauses mid-execution to ask a human for input. The two main forms:

1. Approval. The agent proposes an action ("I will refund $50 to order ABC123. Approve?"). The human says yes or no. The agent executes or cancels.

2. Review-and-edit. The agent produces output (an email draft, a code patch). The human edits it. The agent uses the edited version.

Both are implemented with `interrupt()`. The `interrupt()` function pauses the agent, returns a payload to the caller (the application code that invoked the agent), and waits. The caller gets the payload, displays it to the human, collects the human's response, and resumes the agent with `Command(resume=response)`. The `interrupt()` call returns the resumed value, and the agent continues.

The key insight: `interrupt()` is a normal Python expression that returns a value. The agent code looks like:

```python
approved = interrupt({"action": "refund", "amount": 50, "order_id": "ABC123"})
if not approved:
    return "Refund cancelled."
# ... execute the refund ...
```

The agent author writes the agent as if `interrupt()` were a synchronous function that returns the human's response. The infrastructure (the checkpointer) handles the persistence that makes the pause and resume work.

HITL is essential for any action with side effects that cannot be undone. Refunds, email sends, database writes, file deletions - these all warrant approval. The cost of HITL is latency (the agent waits for a human, which can take minutes to hours) and throughput (a human can only approve so many actions per hour). The trade-off: low-risk actions run autonomously, high-risk actions require approval.

## Worked example

A refund agent that requires human approval for refunds over $50. Full code in [`examples/hitl_demo.py`](../examples/hitl_demo.py).

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class State(TypedDict):
    messages: list
    refund_amount: float
    approved: bool

def parse_refund(state: State) -> dict:
    # In production, the LLM extracts the refund amount from the conversation.
    return {"refund_amount": 75.0}  # demo value

def maybe_approve(state: State) -> dict:
    if state["refund_amount"] <= 50:
        return {"approved": True}
    # Pause and ask the human
    approved = interrupt({
        "action": "refund",
        "amount": state["refund_amount"],
        "reason": "Amount exceeds $50 threshold; requires human approval."
    })
    return {"approved": approved}

def execute(state: State) -> dict:
    if state["approved"]:
        return {"messages": [{"role": "assistant", "content": f"Refund of ${state['refund_amount']} processed."}]}
    return {"messages": [{"role": "assistant", "content": "Refund cancelled by reviewer."}]}

g = StateGraph(State)
g.add_node("parse", parse_refund)
g.add_node("approve", maybe_approve)
g.add_node("execute", execute)
g.add_edge(START, "parse")
g.add_edge("parse", "approve")
g.add_edge("approve", "execute")
g.add_edge("execute", END)

agent = g.compile(checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "refund-001"}}

# First invoke: runs until the interrupt, returns the interrupt payload
result = agent.invoke({"messages": [], "refund_amount": 0, "approved": False}, config=config)
# result contains the interrupt payload - display this to the human

# Human approves
result = agent.invoke(Command(resume=True), config=config)
print(result["messages"][-1]["content"])  # "Refund of $75.0 processed."
```

## Evaluation

Test that: (1) refunds under $50 do not interrupt, (2) refunds over $50 interrupt and resume correctly on approval, (3) the agent correctly reports cancellation when the human rejects.

## Production notes

In production, HITL introduces a new failure mode: the agent is paused indefinitely. The human might be asleep, on vacation, or have left the company. The defenses: (1) set a timeout on the interrupt (the caller resumes with `Command(resume=False)` after N hours), (2) have a fallback approver, (3) monitor the queue of pending approvals and alert if it grows. The second production concern is UX: the approval UI must show enough context (the conversation, the proposed action, the risk level) for the human to make a good decision quickly.

## Common pitfalls

- Using HITL for low-risk actions. Why: it feels safer. Fix: only use HITL for actions that cannot be undone.
- Not setting a timeout on interrupts. Why: it works in dev when the human is responsive. Fix: set a timeout and a fallback.
- Not giving the human enough context. Why: the developer knows what the action is. Fix: the approval payload should include the conversation context, the proposed action, and the risk level.

## Further reading

- [LangGraph HITL](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [LangGraph `interrupt()`](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/dynamic_breakpoints/)

## Checklist

- [ ] Build an approval workflow with `interrupt()` and `Command(resume=...)`
- [ ] Implement a risk-threshold gate (low-risk autonomous, high-risk approval)
- [ ] Set a timeout on interrupts with a fallback
- [ ] Design an approval payload that gives the human enough context
