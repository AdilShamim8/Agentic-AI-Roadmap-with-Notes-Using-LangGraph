# Sequential workflows

Module: 02-langgraph-core
Chapter: 02-sequential-workflows
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Build a linear LangGraph pipeline (node A then B then C) with proper state threading
- Choose between a chain, a StateGraph, and the Functional API for a linear problem
- Add a gate (validation check) between steps with a conditional edge
- Test a sequential workflow with a golden dataset and a rule-based evaluator

## Prerequisites

- [01 Graph, state, edges, nodes](01-graph-state-edges-nodes.md)

## Conceptual foundation

A sequential workflow is the simplest graph: node A produces output, node B consumes it and produces output, node C consumes that and produces the final result. No branching, no loops. You might wonder why you would use a StateGraph for this instead of a LangChain chain or just three function calls. The answer is that you usually should not - a sequential workflow is the case where chains are appropriate. But there are three reasons to use a StateGraph even for a linear pipeline:

1. You expect to add branching or looping later. Starting with a StateGraph means the topology change is incremental, not a rewrite.
2. You need checkpointing between steps. A StateGraph with a checkpointer can resume from any step if a later step fails; a chain cannot.
3. You need observability per step. LangGraph's tracing shows each node as a separate span, which makes debugging easier than tracing through a chain.

The pattern for a sequential workflow with a gate (a validation check between steps) is common. Node A produces output, a validator checks it, and if validation fails the graph routes back to A (a loop) or to an error handler. The gate is just a conditional edge.

## Worked example

A prompt-chaining workflow: take a topic, generate an outline, generate an essay from the outline, then critique the essay. Each step is an LLM call. The full code is in [`examples/sequential_workflow_demo.py`](../examples/sequential_workflow_demo.py).

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class State(TypedDict):
    topic: str
    outline: str
    essay: str
    critique: str

def gen_outline(state: State) -> dict:
    msg = llm.invoke(f"Generate a 5-point outline for an essay on: {state['topic']}")
    return {"outline": msg.content}

def gen_essay(state: State) -> dict:
    msg = llm.invoke(f"Write a 300-word essay following this outline:\n{state['outline']}")
    return {"essay": msg.content}

def critique(state: State) -> dict:
    msg = llm.invoke(f"Critique this essay in 3 bullets:\n{state['essay']}")
    return {"critique": msg.content}

g = StateGraph(State)
g.add_node("outline", gen_outline)
g.add_node("essay", gen_essay)
g.add_node("critique", critique)
g.add_edge(START, "outline")
g.add_edge("outline", "essay")
g.add_edge("essay", "critique")
g.add_edge("critique", END)

agent = g.compile()
result = agent.invoke({"topic": "the future of agentic AI"})
```

## Evaluation

A golden dataset of 10 topics. The evaluator checks that the essay is between 250 and 400 words, that the critique has at least 3 bullets, and that the essay mentions the topic. See [`examples/sequential_workflow_demo.py`](../examples/sequential_workflow_demo.py) for the eval implementation.

## Production notes

In production, the failure mode of a sequential workflow is cascading errors. The outline is slightly off, the essay inherits the error, the critique critiques the wrong thing. The defenses: validate each step's output (does the outline have 5 points? does the essay mention the topic?), and add a retry on validation failure. The gate pattern (conditional edge back to the generator) is the cleanest way to express this.

## Common pitfalls

- Not validating intermediate steps. Why: it works in dev. Fix: add a validator after each LLM call.
- Using a StateGraph when a chain would do. Why: StateGraph feels more "serious." Fix: if you have no branching and no checkpointing, use a chain.

## Further reading

- [LangGraph StateGraph](https://langchain-ai.github.io/langgraph/concepts/low_level/)
- [Anthropic: prompt chaining](https://www.anthropic.com/research/building-effective-agents)

## Checklist

- [ ] Build a 3-node sequential StateGraph with proper state threading
- [ ] Add a validation gate between two nodes with a conditional edge
- [ ] Test the workflow with a golden dataset
- [ ] Decide between a chain and a StateGraph for a linear problem
