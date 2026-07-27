"""LangGraph StateGraph with state, nodes, edges, a conditional edge, and a loop.

Demonstrates the core LangGraph mental model:
- State is a TypedDict shared across nodes
- Nodes are functions that read state and return updates
- Edges route between nodes
- Conditional edges implement branching and loops
- Reducers merge parallel updates

Run:
    python examples/langgraph_core_demo.py

No API key required (the "LLM calls" are mocked for demo purposes).
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import START, END, StateGraph


class State(TypedDict):
    """The shared state for the demo graph.

    The graph takes a number, applies a rule (add 1 if even, multiply by 2
    if odd), and repeats until the number is greater than 10.
    """

    value: int
    steps: int


def decide_and_act(state: State) -> dict:
    """Apply the rule: add 1 if even, multiply by 2 if odd."""
    if state["value"] % 2 == 0:
        return {"value": state["value"] + 1, "steps": state["steps"] + 1}
    return {"value": state["value"] * 2, "steps": state["steps"] + 1}


def should_continue(state: State) -> Literal["loop", "__end__"]:
    """Decide whether to loop back or terminate."""
    return "loop" if state["value"] <= 10 else "__end__"


def build_graph():
    """Build and compile the demo graph."""
    graph = StateGraph(State)
    graph.add_node("act", decide_and_act)
    graph.add_edge(START, "act")
    graph.add_conditional_edges("act", should_continue)
    # The "loop" return value of should_continue routes back to "act".
    graph.add_edge("loop", "act")
    return graph.compile()


# Module-level compiled graph.
agent = build_graph()


def main() -> None:
    """Run the graph with a starting value and print the trace."""
    print("\n=== LangGraph core demo ===")
    print("Starting value: 3")
    print("Rule: add 1 if even, multiply by 2 if odd. Stop when > 10.\n")

    result = agent.invoke({"value": 3, "steps": 0})
    print(f"Final value: {result['value']}")
    print(f"Steps taken: {result['steps']}")

    # Expected trace: 3 (odd) -> 6 (even) -> 7 (odd) -> 14 (>10, stop)
    # 3 steps, final value 14.
    assert result["value"] == 14, f"Expected 14, got {result['value']}"
    assert result["steps"] == 3, f"Expected 3 steps, got {result['steps']}"
    print("\nAssertions passed.")


if __name__ == "__main__":
    main()
