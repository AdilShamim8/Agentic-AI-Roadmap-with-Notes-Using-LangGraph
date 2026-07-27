# LangGraph Studio

Module: 03-agents-in-practice
Chapter: 06-langgraph-studio
Status: stable
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Run LangGraph Studio locally and load a graph for visual inspection
- Step through node execution and inspect state at each step
- Use Studio to diagnose routing failures and tool-call loops
- Export a Studio trace as a shareable artifact for code review

## Prerequisites

- [01 Conversational agents](01-conversational-agents.md)
- [02 Persistence and memory](02-persistence-and-memory.md)

## Conceptual foundation

LangGraph Studio is a visual IDE for LangGraph agents. It renders your graph as a node-and-edge diagram, lets you invoke it with custom inputs, and lets you step through execution node by node, inspecting the state at each step. For debugging, it is dramatically faster than adding print statements or reading LangSmith traces. For code review, the exported trace is a shareable artifact that shows exactly what an agent did on a given input.

Studio connects to your local LangGraph dev server, which runs your graph in a hot-reloading environment. You edit your Python code, Studio reloads, and you can re-invoke the graph with the same input to see how the change affected behavior. This tight loop is what makes agent development tolerable.

The three uses of Studio:

1. Topology inspection. See the graph rendered as a diagram. This is the fastest way to verify that your edges and conditional edges are what you think they are. Misnamed edges and missing conditional branches are obvious in the diagram.

2. Step-through debugging. Invoke the graph, then step forward one node at a time. After each step, inspect the full state. This is how you find the node that produced the wrong value - you see exactly where the state went off the rails.

3. Trace export. After a run, export the trace as a JSON file or a shareable URL. This is the artifact you attach to a bug report or a PR review. It is far more useful than a stack trace because it shows the entire execution, not just the failure point.

## Worked example

There is no code in this chapter - Studio is a tool, not a library. The workflow:

1. Install Studio: `pip install langgraph-cli` and download the desktop app from the LangGraph website.
2. In your project root, create a `langgraph.json` that points to your graph:

```json
{
  "graphs": {
    "agent": "./examples/conversational_agent_demo.py:agent"
  }
}
```

3. Run `langgraph dev` from the project root. This starts the dev server.
4. Open Studio. It connects to the dev server and renders your graph.
5. Click any node to see its code. Click any edge to see its routing logic.
6. Click "Invoke" to run the graph with a custom input. The graph runs and you see the execution trace.
7. Click "Step" to advance one node at a time. Inspect the state after each step.

## Evaluation

No eval. Studio is a development tool, not a production component.

## Production notes

Studio is for development. In production, you use LangSmith for tracing (which gives you the same step-by-step view, but for production traffic rather than dev invocations). The two tools share a conceptual model: a trace is a tree of node executions, each with input state, output state, and duration. If you learn to read a Studio trace, you can read a LangSmith trace.

## Common pitfalls

- Not using Studio. Why: it feels like extra setup. Fix: spend 30 minutes setting it up; it pays for itself the first time you debug a routing failure.
- Treating Studio as a production tool. Why: it is convenient. Fix: use LangSmith for production tracing.

## Further reading

- [LangGraph Studio](https://github.com/langchain-ai/langgraph-studio)
- [LangGraph CLI](https://langchain-ai.github.io/langgraph/cloud/reference/cli/)

## Checklist

- [ ] Install and run LangGraph Studio locally
- [ ] Load a graph and inspect its topology
- [ ] Step through a node-by-node execution and inspect state at each step
- [ ] Export a trace and share it in a code review
