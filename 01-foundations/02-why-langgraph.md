# Why LangGraph

Module: 01-foundations
Chapter: 02-why-langgraph
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

By the end of this chapter, you will be able to:

- Explain what LangChain chains cannot do that LangGraph can
- Describe the four capabilities LangGraph adds (state, cycles, checkpointing, HITL)
- Choose between LangChain chains, LangGraph StateGraph, and the LangGraph Functional API for a given problem
- Migrate an existing LangChain chain to LangGraph without rewriting the world

## Prerequisites

- [01 What is agentic AI](01-what-is-agentic-ai.md)

## Conceptual foundation

LangChain shipped in late 2022 and became the default LLM framework within a year. Its core abstraction was the chain: a directed acyclic graph of prompt-LLM-output steps, composed with LCEL (the LangChain Expression Language). Chains were a big improvement over raw API calls because they standardized prompt composition, output parsing, and tool calling. But chains have a structural limitation that becomes obvious the moment you try to build anything agentic: they are acyclic. A chain runs from start to finish, with no way to loop back.

This matters because every agent pattern is a loop. ReAct is a loop: reason, act, observe, decide whether to act again. Reflexion is a loop: generate, critique, regenerate. Plan-and-execute is a loop: plan, execute, observe, replan. A framework that cannot express loops cannot express agents. Workarounds exist - you can build a loop by recursively calling a chain - but the workarounds hide the loop from the framework, which means the framework cannot help you with the things loops need: state management, termination conditions, checkpointing, and human-in-the-loop interrupts.

LangGraph was built to fix this. Its core abstraction is the StateGraph: a directed graph (cycles allowed) where each node is a function that reads and updates a shared state, and each edge is a routing decision. The graph is explicit - you can see the entire control flow by reading the graph definition. State is explicit - you define a TypedDict or Pydantic model, and every node reads and writes to it. Cycles are explicit - you add an edge from a node back to an earlier node, and you add a termination condition to break the cycle.

The four capabilities LangGraph adds over plain LangChain:

1. State. In a chain, state is implicit: it lives in the messages list and in whatever local variables each step returns. In LangGraph, state is a first-class object that every node reads and writes. This sounds minor; it is not. Explicit state is what makes agents debuggable. When something goes wrong, you can inspect the state at every step and see exactly what each node received and produced.

2. Cycles. LangGraph allows edges from a node back to an earlier node, with conditional termination. This is what makes ReAct, reflexion, and plan-and-execute expressible as graphs rather than as recursive Python functions.

3. Checkpointing. LangGraph persists state to a checkpointer (in-memory, SQLite, Postgres) after every node execution. This means an agent can be paused and resumed, can survive a process crash, and can be rewound to any prior state. For production agents that run for minutes or hours, checkpointing is not optional.

4. Human-in-the-loop. LangGraph's `interrupt()` function pauses the agent at a designated node, returns control to the caller, and waits for a `Command(resume=...)` to continue. This is how you build approval workflows: the agent proposes an action, interrupts, a human approves or rejects, the agent continues or stops.

In 2026, LangGraph also has a second API surface: the Functional API, exposed via `@entrypoint` and `@task` decorators. The Functional API does not use StateGraph; instead, you write ordinary Python functions, and LangGraph handles checkpointing and interrupts behind the scenes. The Functional API is better for linear and checkpoint-heavy workflows. StateGraph is better for multi-agent and complex-topology workflows. You will learn both in module 02.

The decision rule:

- If your problem is a fixed sequence of LLM calls with no looping, use a LangChain chain (or just call the LLM directly - LCEL is optional).
- If your problem has loops, branching, or needs checkpointing, use LangGraph.
- If your problem is linear but needs checkpointing or interrupts, use the Functional API.
- If your problem has complex topology (multiple agents, parallel branches, conditional fan-out), use StateGraph.

## Worked example

No code in this chapter - it is conceptual. The first LangGraph code you will write is in [02 LangGraph core](../02-langgraph-core/). But to make the difference concrete, here is the same task expressed as a chain, as a StateGraph, and as a Functional API entrypoint. The task: take a question, decide whether to search the web, search if needed, and answer.

As a chain (pseudo-LCEL):

```python
chain = (
    {"question": RunnablePassthrough()}
    | decide_search_prompt
    | llm
    | StrOutputParser()
    | maybe_search  # branch on the LLM output, but no loop back
)
```

This works for the simple case but breaks the moment you want the agent to search, read the results, decide whether to search again, and answer. The chain has no way to express that loop.

As a StateGraph:

```python
graph = StateGraph(State)
graph.add_node("decide", decide_node)
graph.add_node("search", search_node)
graph.add_node("answer", answer_node)
graph.add_edge(START, "decide")
graph.add_conditional_edges("decide", route_decision)  # -> "search" or "answer"
graph.add_edge("search", "decide")  # loop back
graph.add_edge("answer", END)
```

The loop is explicit. The state is explicit. The checkpointer can persist every step.

As a Functional API entrypoint:

```python
@entrypoint(checkpointer=MemorySaver())
def research(question: str) -> str:
    history = []
    while True:
        decision = decide(question, history).result()
        if decision == "answer":
            return answer(question, history).result()
        result = search(decision.query).result()
        history.append(result)
```

Same logic, more Pythonic syntax. Use this when the topology is simple and you want the loop to look like a loop.

## Evaluation

No eval for this chapter - it is conceptual. The checklist below is the self-test.

## Production notes

The choice between chain, StateGraph, and Functional API is reversible but expensive to reverse. Migrating a chain to a StateGraph is a rewrite. Migrating a StateGraph to a Functional API is also a rewrite. Pick correctly the first time using the decision rule above.

In production, the most common regret is using a chain for something that turned out to need a loop. The team builds a chain, the chain works for the demo, then a stakeholder asks "what if the answer is wrong, can it try again?" and the chain has no way to express that. The fix is to start with a StateGraph for anything that might need a loop, even if the first version is linear. A StateGraph with no cycles is just a chain with extra syntax - the syntax is there when you need it.

## Common pitfalls

- Using a chain because it is simpler, then hitting a loop requirement later. Why: chains feel faster to build. Fix: if there is any chance the problem needs a loop, use a StateGraph from the start.
- Using a StateGraph for a problem that is genuinely linear. Why: StateGraph feels more "serious." Fix: if the graph has no cycles and no conditional edges, use a chain or the Functional API.
- Treating the Functional API as "LangGraph lite." Why: it looks like ordinary Python. Fix: the Functional API has the same checkpointing and interrupt semantics as StateGraph - use it when the topology is simple, not when you want to avoid learning StateGraph.

## Further reading

- [LangGraph documentation](https://langchain-ai.github.io/langgraph/) - the official reference
- [LangGraph Functional API](https://langchain-ai.github.io/langgraph/concepts/functional_api/) - the `@entrypoint` / `@task` guide
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) - the essay that motivated the chain-vs-workflow-vs-agent distinction

## Checklist

You understand this chapter if you can:

- [ ] Name the four capabilities LangGraph adds over plain LangChain
- [ ] Given a problem, choose between a chain, a StateGraph, and the Functional API
- [ ] Explain why a chain cannot express ReAct
- [ ] Explain what checkpointing buys you in production
