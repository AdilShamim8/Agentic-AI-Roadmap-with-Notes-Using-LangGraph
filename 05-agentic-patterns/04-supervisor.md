# Supervisor

Module: 05-agentic-patterns
Chapter: 04-supervisor
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement the supervisor pattern: one LLM routes to N specialist agents
- Use `langgraph-supervisor` for the standard implementation
- Diagnose supervisor failure modes (over-routing, under-routing, infinite handoffs)
- Choose between supervisor and swarm based on task structure

## Prerequisites

- [01 ReAct](01-react.md)

## Conceptual foundation

The supervisor pattern is the most common multi-agent architecture. One LLM - the supervisor - looks at the user's request and decides which specialist agent should handle it. The specialist does its work and returns the result to the supervisor. The supervisor either routes to another specialist, responds to the user, or declares the task complete.

The supervisor is a router, not a doer. It does not call tools itself; it delegates to specialists who do. This separation is what makes the pattern scale: each specialist has a small tool list (better selection accuracy), and the supervisor's only job is to pick the right specialist (a simpler decision than doing the work).

The components:

1. Supervisor. An LLM call that takes the conversation and the list of specialists. Returns the name of the next specialist, or "FINISH".

2. Specialists. Each is an agent (typically ReAct) with tools specific to its domain. A researcher specialist has search tools; a writer specialist has a save-to-file tool; a code specialist has a code-execution tool.

3. Handoff. When the supervisor routes to a specialist, the specialist's output is added to the conversation and the supervisor is re-invoked. The supervisor sees the specialist's output and decides what to do next.

The pattern handles multi-step tasks (research, then analyze, then write) and tasks that require multiple skills (a question that needs both a calculation and a search). It fails when the supervisor routes back and forth between specialists without making progress - the "infinite handoff" problem. The fix is a max-handoff count.

## Worked example

A supervisor with three specialists: researcher, analyst, writer. Full code in [`examples/supervisor_demo.py`](../examples/supervisor_demo.py).

```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

llm = ChatOpenAI(model="gpt-4o", temperature=0)

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"[Results for: {query}]"

@tool
def analyze_data(data: str) -> str:
    """Analyze data and extract insights."""
    return f"[Analysis of: {data}]"

@tool
def write_report(content: str) -> str:
    """Format content as a report."""
    return f"# Report\n\n{content}"

researcher = create_react_agent(llm, tools=[search_web], prompt="You are a research specialist.")
analyst = create_react_agent(llm, tools=[analyze_data], prompt="You are a data analyst.")
writer = create_react_agent(llm, tools=[write_report], prompt="You are a technical writer.")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    next: str

def supervisor(state: State) -> dict:
    msg = llm.invoke([
        {"role": "system", "content": "Route to 'researcher', 'analyst', 'writer', or 'FINISH'. Reply with one word."},
        *state["messages"],
    ])
    return {"next": msg.content.strip()}

def route(state: State) -> Literal["researcher", "analyst", "writer", "__end__"]:
    return "__end__" if state["next"] == "FINISH" else state["next"]

g = StateGraph(State)
g.add_node("supervisor", supervisor)
g.add_node("researcher", lambda s: researcher.invoke(s))
g.add_node("analyst", lambda s: analyst.invoke(s))
g.add_node("writer", lambda s: writer.invoke(s))
g.add_edge(START, "supervisor")
g.add_conditional_edges("supervisor", route)
for s in ["researcher", "analyst", "writer"]:
    g.add_edge(s, "supervisor")

agent = g.compile()
```

## Evaluation

A golden dataset of 10 multi-step tasks. The evaluator checks: (1) the final output is correct, (2) the supervisor routed to the right specialists in the right order, (3) the agent did not exceed 10 handoffs.

## Production notes

In production, the supervisor's prompt is the highest-leverage tuning point. The supervisor needs to know each specialist's capabilities (a one-line description of each) and the overall task structure. Tune the supervisor's prompt with examples of correct routing. Track the average handoff count and alert if it drifts upward.

The `langgraph-supervisor` library provides a pre-built implementation. Use it rather than rolling your own, unless you need custom routing logic.

## Common pitfalls

- Specialists with overlapping capabilities. Why: the supervisor cannot distinguish them. Fix: give each specialist a clearly distinct capability.
- No max-handoff count. Why: it works in dev. Fix: cap at 10.
- The supervisor doing work itself. Why: it feels faster. Fix: the supervisor only routes; it never calls tools.

## Further reading

- [langgraph-supervisor](https://github.com/langchain-ai/langgraph-supervisor-py)
- [LangGraph multi-agent guide](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)

## Checklist

- [ ] Implement a supervisor with 3+ specialist agents
- [ ] Cap handoffs at 10
- [ ] Give each specialist a clearly distinct capability
- [ ] Track the average handoff count
