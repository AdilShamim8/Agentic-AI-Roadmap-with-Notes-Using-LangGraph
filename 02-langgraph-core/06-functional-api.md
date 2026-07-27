# Functional API

Module: 02-langgraph-core
Chapter: 06-functional-api
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Write an agent with `@entrypoint` and `@task` decorators
- Explain the difference between the Functional API and StateGraph
- Choose between the two APIs based on problem shape
- Use `interrupt()` and `Command(resume=...)` in the Functional API

## Prerequisites

- [01 Graph, state, edges, nodes](01-graph-state-edges-nodes.md)
- [02 Sequential workflows](02-sequential-workflows.md)
- [05 Iterative workflows](05-iterative-workflows.md)

## Conceptual foundation

The Functional API is LangGraph's second API surface, introduced in 2025. It does not use StateGraph; instead, you write ordinary Python functions decorated with `@entrypoint` (the top-level function that orchestrates) and `@task` (a unit of work that is checkpointed and can be retried). The result looks like ordinary Python code - loops, conditionals, try/except - but with the same persistence, interrupt, and tracing guarantees as StateGraph.

The Functional API is better for:

- Linear and checkpoint-heavy workflows where the topology is simple
- Workflows where the control flow is naturally expressed as Python (loops, early returns, exceptions) rather than as a graph
- Rapid prototyping, because the syntax is more familiar to Python developers

StateGraph is better for:

- Multi-agent systems with complex topology (supervisor with N specialists, each of which is itself a graph)
- Workflows where the topology itself is the documentation (the graph reads like a flowchart)
- Cases where you need to inspect or modify the graph structure at runtime

The decision rule: if your workflow reads naturally as a Python function with a loop, use the Functional API. If it reads naturally as a flowchart with conditional branches and parallel paths, use StateGraph. Both produce the same runtime guarantees; the difference is ergonomics.

The key features of the Functional API:

- `@task` makes a function checkpointed. If the entrypoint is interrupted (by `interrupt()`, by a process crash, by a human pause), completed tasks are not re-run on resume. This is the durability guarantee.
- `@entrypoint` makes a function the top-level orchestrator. It accepts a `checkpointer` argument for persistence. The entrypoint can call tasks, call LLMs directly, call `interrupt()`, and return a final value.
- `interrupt()` pauses the entrypoint and returns control to the caller. The caller can resume with `Command(resume=value)`, and the `interrupt()` call returns the resumed value.

## Worked example

The same research-agent pattern from [02 Sequential workflows](02-sequential-workflows.md), expressed with the Functional API. Full code in [`examples/functional_api_demo.py`](../examples/functional_api_demo.py).

```python
from langgraph.func import entrypoint, task
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

@task
def research(topic: str) -> str:
    return llm.invoke(f"Research this topic: {topic}").content

@task
def summarize(text: str) -> str:
    return llm.invoke(f"Summarize:\n{text}").content

@entrypoint(checkpointer=MemorySaver())
def research_agent(topic: str) -> str:
    raw = research(topic).result()
    summary = summarize(raw).result()
    # Demonstrate interrupt: ask for human approval before returning
    approved = interrupt({"summary": summary, "question": "Approve this summary?"})
    if not approved:
        return "Summary rejected by reviewer."
    return summary

# First invocation: runs until the interrupt, returns the interrupt payload
config = {"configurable": {"thread_id": "demo-1"}}
result = research_agent.invoke("agentic AI in 2026", config=config)
print(result)  # the interrupt payload

# Resume with approval
result = research_agent.invoke(Command(resume=True), config=config)
print(result)  # the summary
```

The same logic as a StateGraph would require explicit nodes for `research`, `summarize`, and `interrupt`, plus edges between them. The Functional API expresses it as ordinary Python, which is more readable for a linear flow like this.

## Evaluation

The eval for a Functional API agent is the same as for a StateGraph agent: a golden dataset, an evaluator, a pass threshold. The runtime guarantees are identical; only the authoring syntax differs.

## Production notes

In production, the Functional API has one significant advantage: it is easier to test. A `@task` is just a Python function, so you can call it directly in a unit test without invoking the entrypoint. This makes test-driven development of agent components much more natural than with StateGraph, where each node is a function that takes state and returns state, which is harder to test in isolation.

The main risk: because the Functional API looks like ordinary Python, it is easy to write code that is not actually checkpointed. A `@task` is checkpointed; a plain function called inside a `@task` is not. If you do expensive work in a plain function and the entrypoint crashes, the work is lost. The rule: any expensive operation (LLM call, API call, file write) should be inside a `@task`.

## Common pitfalls

- Doing expensive work outside a `@task`. Why: the code looks fine. Fix: wrap every LLM call, API call, and file write in a `@task`.
- Using the Functional API for complex multi-agent topology. Why: it works for simple cases. Fix: switch to StateGraph when the topology has more than 3 agents or complex parallelism.
- Forgetting that `interrupt()` returns the resumed value. Why: it looks like a statement, not an expression. Fix: `value = interrupt(payload)` captures the resumed value.

## Further reading

- [LangGraph Functional API](https://langchain-ai.github.io/langgraph/concepts/functional_api/)
- [LangGraph `@entrypoint` and `@task`](https://langchain-ai.github.io/langgraph/how-tos/use_function_api/)

## Checklist

- [ ] Write an agent with `@entrypoint` and at least two `@task` functions
- [ ] Use `interrupt()` and `Command(resume=...)` in a Functional API agent
- [ ] Choose between the Functional API and StateGraph for a given problem, with reasons
- [ ] Wrap every expensive operation in a `@task`
