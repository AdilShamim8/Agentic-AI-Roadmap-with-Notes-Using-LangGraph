# Parallel workflows

Module: 02-langgraph-core
Chapter: 03-parallel-workflows
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Build a fan-out / fan-in graph where multiple nodes run in the same super-step
- Write reducers that safely merge parallel updates to the same state field
- Diagnose and fix the "last writer wins" bug
- Choose between parallel execution and sequential execution based on latency and cost

## Prerequisites

- [01 Graph, state, edges, nodes](01-graph-state-edges-nodes.md)
- [02 Sequential workflows](02-sequential-workflows.md)

## Conceptual foundation

Parallel execution in LangGraph is a consequence of the super-step model. If two nodes are both ready to execute in the same super-step (because both have incoming edges from a node that just finished), LangGraph runs them in parallel. The outputs are collected, the reducers are applied, and the merged state is passed to the next super-step. This is fan-out: one node's output triggers multiple downstream nodes. Fan-in is the reverse: multiple nodes feed into a single node that aggregates their outputs.

The critical mechanism that makes parallel execution safe is the reducer. Without a reducer, if two parallel nodes both write to the same field, LangGraph has no way to merge the updates - one would overwrite the other, and the result would be non-deterministic (whichever finished last wins). With a reducer, you specify how to merge. For a list field, `operator.add` concatenates. For a counter, a custom reducer sums. For a "max" field, a custom reducer takes the larger value.

The canonical use case for parallel workflows is multi-criteria evaluation. Given a piece of content (an essay, a code review, a support response), run three evaluators in parallel (depth, clarity, accuracy), collect their scores, and aggregate. The parallel version is 3x faster than the sequential version (assuming the LLM calls are the bottleneck, which they are). The cost is the same. The latency win is free.

## Worked example

An essay-evaluation graph: generate a topic, collect an essay, evaluate on three criteria in parallel, aggregate, decide pass or fail. Full code in [`examples/parallel_workflow_demo.py`](../examples/parallel_workflow_demo.py).

```python
from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class State(TypedDict):
    essay: str
    depth_score: int
    clarity_score: int
    accuracy_score: int
    total: int
    passed: bool

def eval_depth(state: State) -> dict:
    msg = llm.invoke(f"Rate the depth of this essay 1-10. Reply with just the number.\n{state['essay']}")
    return {"depth_score": int(msg.content.strip())}

def eval_clarity(state: State) -> dict:
    msg = llm.invoke(f"Rate the clarity 1-10. Reply with just the number.\n{state['essay']}")
    return {"clarity_score": int(msg.content.strip())}

def eval_accuracy(state: State) -> dict:
    msg = llm.invoke(f"Rate the accuracy 1-10. Reply with just the number.\n{state['essay']}")
    return {"accuracy_score": int(msg.content.strip())}

def aggregate(state: State) -> dict:
    total = state["depth_score"] + state["clarity_score"] + state["accuracy_score"]
    return {"total": total, "passed": total >= 21}

g = StateGraph(State)
g.add_node("depth", eval_depth)
g.add_node("clarity", eval_clarity)
g.add_node("accuracy", eval_accuracy)
g.add_node("agg", aggregate)
g.add_edge(START, "depth")
g.add_edge(START, "clarity")
g.add_edge(START, "accuracy")
g.add_edge("depth", "agg")
g.add_edge("clarity", "agg")
g.add_edge("accuracy", "agg")
g.add_edge("agg", END)

agent = g.compile()
result = agent.invoke({"essay": "..."})
```

The three evaluators run in parallel; `agg` runs after all three finish. The state fields `depth_score`, `clarity_score`, `accuracy_score` are each written by only one node, so no reducers are needed for them. If the three evaluators all wrote to a shared `scores` list, you would need `Annotated[list, add]`.

## Evaluation

Test that the three evaluators actually run in parallel (latency should be ~1x the slowest evaluator, not ~3x), and that the aggregation is correct.

## Production notes

In production, parallel workflows are how you keep latency acceptable as agents grow. A 5-step sequential agent at 2 seconds per step is 10 seconds; the same agent with 3 parallel steps is 6 seconds. The trade-off is cost: parallel calls all hit the LLM at once, which is fine for rate limits but means you pay for all of them even if one fails. Add per-step error handling so one failed evaluator does not sink the whole graph.

## Common pitfalls

- Forgetting reducers on shared fields. Why: the bug is non-deterministic. Fix: annotate any field that more than one parallel node writes to.
- Running independent LLM calls sequentially out of habit. Why: sequential code is easier to read. Fix: if two calls do not depend on each other, parallelize them.

## Further reading

- [LangGraph parallel execution](https://langchain-ai.github.io/langgraph/concepts/low_level/#parallel-execution)
- [Anthropic: parallelization patterns](https://www.anthropic.com/research/building-effective-agents)

## Checklist

- [ ] Build a fan-out / fan-in graph with at least 3 parallel nodes
- [ ] Write a reducer for a shared list field
- [ ] Diagnose a "last writer wins" bug
- [ ] Measure the latency improvement of parallel vs sequential execution
