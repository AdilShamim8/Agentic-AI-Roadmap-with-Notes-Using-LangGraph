# Map-reduce

Module: 05-agentic-patterns
Chapter: 07-map-reduce
Status: stable
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Implement map-reduce: fan out a task across N items, process each in parallel, aggregate the results
- Use LangGraph's parallel execution to implement the "map" phase
- Choose an aggregation strategy (concatenation, voting, summarization, best-of)
- Diagnose map-reduce failure modes (one slow item blocks aggregation, aggregation loses information)

## Prerequisites

- [03 Parallel workflows](../02-langgraph-core/03-parallel-workflows.md)
- [01 ReAct](01-react.md)

## Conceptual foundation

Map-reduce is the pattern for batch processing. You have N items (N documents to summarize, N emails to classify, N code files to review). You "map" by processing each item independently (often in parallel), then "reduce" by aggregating the results.

In LangGraph, the map phase is implemented with parallel execution: a node fans out to N copies of a worker (or N invocations of the same worker), each processes one item, and a reducer merges the results. The reduce phase is a single node that takes the merged results and produces the final output.

The four aggregation strategies:

1. Concatenation. The results are concatenated into a list. Use when each result is independent (e.g., N classifications become a list of labels).

2. Voting. The results are votes, and the majority wins. Use when the workers might disagree (e.g., 5 classifiers vote on the label, the majority is the answer).

3. Summarization. The results are summarized into a single output. Use when the results are too long to concatenate (e.g., N document summaries are summarized into one meta-summary).

4. Best-of. The results are scored, and the best one is selected. Use when quality varies (e.g., 3 code patches are generated, tests are run, the one that passes is selected).

Map-reduce is the right pattern when the items are independent. If the items depend on each other (processing item 2 requires the result of item 1), map-reduce is wrong - use a sequential workflow.

## Worked example

A map-reduce agent that summarizes N documents and produces a meta-summary. Full code in [`examples/map_reduce_demo.py`](../examples/map_reduce_demo.py).

```python
from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class State(TypedDict):
    documents: list[str]
    summaries: Annotated[list[str], add]
    meta_summary: str

def make_summarizer(doc: str):
    def summarize(state: State) -> dict:
        msg = llm.invoke(f"Summarize in 2 sentences:\n{doc}")
        return {"summaries": [msg.content]}
    return summarize

def meta_summarize(state: State) -> dict:
    msg = llm.invoke(f"Combine these summaries into one:\n" + "\n".join(state["summaries"]))
    return {"meta_summary": msg.content}

g = StateGraph(State)
# Fan out: one summarizer per document (in a real graph, use Send for dynamic fan-out)
docs = ["doc1 text", "doc2 text", "doc3 text"]
for i, doc in enumerate(docs):
    g.add_node(f"summarize_{i}", make_summarizer(doc))
    g.add_edge(START, f"summarize_{i}")
    g.add_edge(f"summarize_{i}", "meta")
g.add_node("meta", meta_summarize)
g.add_edge("meta", END)

agent = g.compile()
```

In production, use `Send` for dynamic fan-out (when the number of items is not known at graph-definition time).

## Evaluation

A golden dataset of 5 batches of documents. The evaluator checks: (1) the meta-summary mentions key points from all documents, (2) the latency is approximately the slowest summarizer, not the sum.

## Production notes

In production, the main risk is a single slow item blocking the aggregation. If 9 items process in 2 seconds and 1 takes 30 seconds, the whole batch takes 30 seconds. The fix: set a per-item timeout and proceed with partial results if the timeout is hit. The second risk: aggregation losing information. The meta-summary might drop a key point from one document. The fix: have the aggregator cite which summaries it drew from.

## Common pitfalls

- Sequential instead of parallel map. Why: it is easier to write. Fix: use parallel execution; the latency win is large.
- No per-item timeout. Why: it works when all items are fast. Fix: set a timeout and handle it.
- Aggregation that loses information. Why: the meta-summary is shorter than the input. Fix: have the aggregator cite sources.

## Further reading

- [LangGraph map-reduce with Send](https://langchain-ai.github.io/langgraph/how-tos/map-reduce/)
- [Anthropic: orchestrator-workers pattern](https://www.anthropic.com/research/building-effective-agents)

## Checklist

- [ ] Implement a map-reduce agent with parallel map and a single reduce
- [ ] Use `Send` for dynamic fan-out
- [ ] Set a per-item timeout
- [ ] Choose an aggregation strategy based on the result type
