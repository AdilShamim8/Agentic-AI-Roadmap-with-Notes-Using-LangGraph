# Graph, state, edges, nodes

Module: 02-langgraph-core
Chapter: 01-graph-state-edges-nodes
Status: stable
Last reviewed: 2026-07-27
Estimated time: 3 hours

## Learning objectives

By the end of this chapter, you will be able to:

- Define a LangGraph StateGraph with a TypedDict state, nodes, edges, and conditional edges
- Explain the execution model: super-steps, parallel node execution within a step, message passing between steps
- Write reducers that safely merge state updates from parallel nodes
- Compile a graph, invoke it, and inspect the state at every step

## Prerequisites

- [01 Foundations](../01-foundations/)

## Conceptual foundation

LangGraph's core abstraction is the StateGraph. A StateGraph is a directed graph where each node is a Python function that reads part of the state and returns a partial state update, and each edge is a routing decision. The graph has a single shared state object that flows through it; nodes do not pass arguments to each other directly, they read and write the shared state. This is the single most important mental model: LangGraph is a state machine powered by LLMs.

The state is defined as a TypedDict (or a Pydantic model, or a dataclass). Each field has a type and, optionally, a reducer. A reducer is a function that defines how to merge updates to that field from multiple nodes in the same super-step. Without reducers, parallel updates to the same field would conflict and the last writer would win, which is rarely what you want. With reducers, you can specify that a list field should be concatenated (`add_messages` is the canonical example), that a counter should be incremented, or that a value should be replaced.

The execution model is "super-steps." When you invoke a graph, LangGraph runs all nodes that are ready to execute in parallel (within a single super-step), collects their state updates, applies the reducers, and then moves to the next super-step based on the edges. This continues until no nodes are ready (the graph halts) or a max-super-step limit is hit. The super-step model is what makes parallel execution safe: within a step, nodes cannot see each other's updates, so the order of execution within a step does not matter.

Nodes are Python functions. They take the state as an argument and return a dict (or a partial state object) with the fields to update. A node does not return the full state - it returns only the updates. This is important for two reasons: it makes parallel updates composable (two nodes can update different fields of the same state without conflict), and it makes checkpointing efficient (LangGraph only stores the diff, not the full state, at each step).

Edges are the routing. A normal edge from node A to node B means "after A finishes, run B." A conditional edge from node A is a function that returns the name of the next node based on the state. Conditional edges are how you implement branching, loops, and termination. The conditional function reads the state and returns a string (the name of the next node) or `END` (to terminate).

Compilation is the step that validates the graph and prepares it for execution. `graph.compile()` checks that all nodes referenced in edges exist, that the state schema is consistent, and that there are no unreachable nodes. It returns a compiled graph that you can invoke. Compilation is also where you attach a checkpointer (for persistence), a store (for cross-thread memory), and interrupt configurations (for human-in-the-loop).

The single most common mistake when learning LangGraph: treating it like a chain. A chain is "do A, then B, then C." A graph is "do A, and based on what A produced, do B or C, and based on that, maybe loop back to A." The graph mental model is more powerful but requires you to think about routing, not just sequencing. If you find yourself writing a graph with no conditional edges and no cycles, you probably wanted a chain.

## Worked example

Here is a complete, minimal StateGraph that demonstrates state, nodes, edges, a conditional edge, and a loop. The task: take a number, decide whether to add 1 or multiply by 2, do it, and repeat until the number is greater than 10.

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    value: int
    steps: int

def decide_and_act(state: State) -> dict:
    # In a real agent, this would be an LLM call.
    if state["value"] % 2 == 0:
        return {"value": state["value"] + 1, "steps": state["steps"] + 1}
    else:
        return {"value": state["value"] * 2, "steps": state["steps"] + 1}

def should_continue(state: State) -> Literal["loop", "__end__"]:
    return "loop" if state["value"] <= 10 else "__end__"

graph = StateGraph(State)
graph.add_node("act", decide_and_act)
graph.add_edge(START, "act")
graph.add_conditional_edges("act", should_continue)
graph.add_edge("loop", "act")  # this edge is taken when should_continue returns "loop"

compiled = graph.compile()

result = compiled.invoke({"value": 3, "steps": 0})
print(result)  # {'value': 12, 'steps': 3}
```

Run this and trace the execution: 3 (odd) -> 6 (even) -> 7 (odd) -> 14 (>10, stop). Three steps. The state at each step is persisted by the checkpointer (if you attach one) and can be inspected.

For parallel execution with reducers, here is a minimal example showing how to safely merge updates from two nodes running in the same super-step:

```python
from typing import Annotated
from operator import add

class State(TypedDict):
    results: Annotated[list, add]  # concatenate lists from parallel nodes

def node_a(state: State) -> dict:
    return {"results": ["a"]}

def node_b(state: State) -> dict:
    return {"results": ["b"]}

def aggregate(state: State) -> dict:
    return {"results": ["aggregated"] + state["results"]}

graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_node("agg", aggregate)
graph.add_edge(START, "a")  # a and b run in parallel
graph.add_edge(START, "b")
graph.add_edge("a", "agg")
graph.add_edge("b", "agg")
graph.add_edge("agg", END)

compiled = graph.compile()
result = compiled.invoke({"results": []})
print(result)  # {'results': ['aggregated', 'a', 'b']}
```

The `Annotated[list, add]` tells LangGraph to use `operator.add` (list concatenation) to merge updates to `results`. Without it, the two parallel updates would conflict and one would overwrite the other.

## Evaluation

The eval for this chapter measures two things: does the graph produce the correct final state, and does the graph halt in the expected number of steps. A minimal test:

```python
def test_loop_terminates():
    result = compiled.invoke({"value": 3, "steps": 0})
    assert result["value"] > 10
    assert result["steps"] == 3

def test_parallel_merge():
    result = compiled.invoke({"results": []})
    assert sorted(result["results"]) == ["a", "aggregated", "b"]
```

See [`examples/langgraph_core_demo.py`](../examples/langgraph_core_demo.py) for the full runnable code and tests.

## Production notes

In production, the StateGraph model has three implications:

1. State is the contract between nodes. If a node expects a field to be present, it must be set by an earlier node (or by the initial state). Document the state schema carefully - it is the API of your graph.

2. Reducers are not optional for parallel nodes. If two nodes write to the same field without a reducer, you have a race condition. Always annotate fields that parallel nodes touch with a reducer.

3. The graph topology is the documentation. A well-named StateGraph with explicit edges reads like a flowchart. A graph with cryptic node names and dynamic edge routing reads like spaghetti. Name nodes as verbs (`classify`, `retrieve`, `synthesize`), name edges as decisions (`route_by_intent`), and the graph will be self-documenting.

The most common production failure: a node assumes a field is set but an earlier node conditionally skipped setting it. The fix is to either always set the field (with a default) or to make the conditional node set a sentinel value (`None`) that downstream nodes check.

## Common pitfalls

- Treating StateGraph like a chain. Why: chains are more familiar. Fix: use conditional edges and loops; if you have neither, use a chain.
- Forgetting reducers on parallel-updated fields. Why: the bug only manifests under parallel execution. Fix: annotate every field that more than one node might write to.
- Returning the full state from a node instead of just the updates. Why: it feels more explicit. Fix: return only the fields you changed; this makes checkpointing efficient and parallel updates composable.
- Naming nodes as nouns. Why: it reads naturally. Fix: name nodes as verbs (`classify`, not `classifier`) - the node is an action.

## Further reading

- [LangGraph StateGraph documentation](https://langchain-ai.github.io/langgraph/concepts/low_level/)
- [LangGraph reducers](https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers)
- [LangGraph execution model](https://langchain-ai.github.io/langgraph/concepts/langgraph_runtime/)

## Checklist

You understand this chapter if you can:

- [ ] Define a StateGraph with a TypedDict state, at least three nodes, a conditional edge, and a loop
- [ ] Explain what a super-step is and why parallel nodes within a step cannot see each other's updates
- [ ] Write a reducer for a list field that concatenates updates from parallel nodes
- [ ] Diagnose a graph that does not halt by inspecting the conditional edge logic
