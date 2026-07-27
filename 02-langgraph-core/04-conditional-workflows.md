# Conditional workflows

Module: 02-langgraph-core
Chapter: 04-conditional-workflows
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Use `add_conditional_edges` to route based on state
- Build a router pattern (classify input, route to one of N specialists)
- Combine conditional edges with loops for self-correction
- Diagnose routing failures (wrong route, infinite loop, dead end)

## Prerequisites

- [01 Graph, state, edges, nodes](01-graph-state-edges-nodes.md)
- [02 Sequential workflows](02-sequential-workflows.md)

## Conceptual foundation

A conditional edge is a function that reads the state and returns the name of the next node to execute. This is the mechanism that makes LangGraph a graph rather than a chain. With conditional edges, you can build routers (one input, multiple possible destinations), loops (route back to an earlier node), and termination conditions (route to `END` when done).

The router pattern is the most common conditional workflow. A classifier node reads the user's input, determines the intent, and routes to one of N specialist nodes. Each specialist handles one intent. After the specialist finishes, the graph either returns to the router (for multi-turn) or ends. This pattern is the backbone of most production support agents.

The self-correction pattern combines conditional edges with loops. A generator node produces output, a critic node evaluates it, and a conditional edge routes back to the generator if the critic rejects. This is the simplest form of reflexion, and it is surprisingly effective: a single retry with the critic's feedback fixes a large fraction of LLM failures.

The four routing failure modes:

1. Wrong route. The classifier picks the wrong specialist. Fix: improve the classifier prompt, add few-shot examples of correct routing, fall back to a generalist if confidence is low.

2. Infinite loop. The conditional edge routes back to an earlier node, but the termination condition is never met. Fix: add a max-iteration counter to the state and route to `END` when it exceeds the limit.

3. Dead end. The conditional edge routes to a node that does not exist (typo, renamed node). Fix: `graph.compile()` catches this at compile time, but dynamic routing (returning a string from the conditional function) can still produce it at runtime. Always return `END` as a default.

4. Routing oscillation. The graph bounces between two nodes without making progress. Fix: add state that tracks how many times each node has been visited and route to `END` if a node is visited more than N times.

## Worked example

A support router: classify a message as refund, bug, or feature_request, route to the right specialist, and respond. Full code in [`examples/conditional_workflow_demo.py`](../examples/conditional_workflow_demo.py).

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class State(TypedDict):
    message: str
    intent: str
    response: str

def classify(state: State) -> dict:
    msg = llm.invoke(
        f"Classify this customer message as 'refund', 'bug', or 'feature_request'. "
        f"Reply with just the label.\n\n{state['message']}"
    )
    return {"intent": msg.content.strip().lower()}

def handle_refund(state: State) -> dict:
    msg = llm.invoke(f"Write a refund response to: {state['message']}")
    return {"response": msg.content}

def handle_bug(state: State) -> dict:
    msg = llm.invoke(f"Write a bug-report response to: {state['message']}")
    return {"response": msg.content}

def handle_feature(state: State) -> dict:
    msg = llm.invoke(f"Write a feature-request response to: {state['message']}")
    return {"response": msg.content}

def route(state: State) -> Literal["refund", "bug", "feature", "__end__"]:
    return {"refund": "refund", "bug": "bug", "feature_request": "feature"}.get(
        state["intent"], "__end__"
    )

g = StateGraph(State)
g.add_node("classify", classify)
g.add_node("refund", handle_refund)
g.add_node("bug", handle_bug)
g.add_node("feature", handle_feature)
g.add_edge(START, "classify")
g.add_conditional_edges("classify", route)
g.add_edge("refund", END)
g.add_edge("bug", END)
g.add_edge("feature", END)

agent = g.compile()
result = agent.invoke({"message": "I want my money back"})
```

## Evaluation

A golden dataset of 20 messages with labeled intents. The evaluator checks that the routed intent matches the label and that the response is non-empty.

## Production notes

In production, routers fail when intents overlap or when the classifier is not confident. The defense is a confidence threshold: if the classifier's top intent has low confidence (or if the classifier returns a low logprob on the intent label), fall back to a generalist or ask the user for clarification. Do not let a 50-percent-confidence router send a refund request to the bug specialist.

## Common pitfalls

- Not having a default route. Why: it works in dev when all test cases route cleanly. Fix: always return `END` (or a fallback node) from the conditional function.
- Not capping iterations. Why: loops are useful but dangerous. Fix: add an iteration counter to the state.
- Routing on the full message instead of a structured intent. Why: it feels more flexible. Fix: have the classifier output a structured label, then route on the label - this is debuggable and evaluable.

## Further reading

- [LangGraph conditional edges](https://langchain-ai.github.io/langgraph/concepts/low_level/#conditional-edges)
- [Anthropic: routing workflows](https://www.anthropic.com/research/building-effective-agents)

## Checklist

- [ ] Build a router that classifies input and routes to one of 3+ specialists
- [ ] Add a max-iteration counter to prevent infinite loops
- [ ] Diagnose a routing failure as wrong-route, infinite-loop, dead-end, or oscillation
- [ ] Add a confidence threshold and a fallback route
