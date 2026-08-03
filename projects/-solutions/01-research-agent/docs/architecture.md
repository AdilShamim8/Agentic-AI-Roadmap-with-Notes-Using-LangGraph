# Architecture

## Graph shape

```
                         ┌───────────────────┐
                         │  load_documents    │  (runs once)
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                  ┌─────▶│       plan         │
                  │      └─────────┬─────────┘
                  │                │
                  │                ▼
                  │      ┌───────────────────┐
                  │      │       search       │
                  │      └─────────┬─────────┘
                  │                │
                  │                ▼
                  │      ┌───────────────────┐
                  │      │     synthesize      │
                  │      └─────────┬─────────┘
                  │                │
                  │                ▼
                  │      ┌───────────────────┐
                  │      │      critique       │
                  │      └─────────┬─────────┘
                  │                │
        "continue"│         ┌──────┴──────┐
                  └─────────┤ route_after │
                            │  critique   │
                            └──────┬──────┘
                                   │ "finish"
                                   ▼
                         ┌───────────────────┐
                         │  compile_report     │
                         └───────────────────┘
```

`route_after_critique` is the only conditional edge. It loops back to
`plan` when the critique step found real gaps **and** the iteration
budget (`MAX_ITERATIONS`) hasn't been used up yet; otherwise it moves on
to `compile_report`.

## Why two runners (`engine.py` and `graph.py`)?

The five node functions in `nodes.py` (`load_documents_node`,
`plan_node`, `search_node`, `synthesize_node`, `critique_node`,
`compile_report_node`) are plain Python functions with the signature
`(state, *deps) -> state`. They don't import LangGraph and don't know
anything about how they're being called.

- **`graph.py`** wires those functions into a real `langgraph.graph.StateGraph`
  with a conditional edge. This is the "real" implementation — the point
  of this project is to practice building an agentic loop in LangGraph.
- **`engine.py`** runs the exact same functions in a plain Python
  `for` loop with the same routing logic, with no LangGraph dependency
  at all.

Two consequences of that split:

1. **The whole test suite runs without LangGraph installed.** Every test
   in `tests/` uses `FakeLLM` and `FakeSearch` and calls into
   `engine.py` or the node functions directly — there's no mock of
   LangGraph's internals to keep in sync, because LangGraph is never on
   the critical path being tested. Only the *routing logic itself*
   (`route_after_critique`, and how `plan_node` consumes follow-up
   questions) is under test, and it's identical in both runners since
   they call the same functions.
2. **The CLI and the Streamlit app both default to LangGraph but fall
   back automatically** if it isn't installed yet, so a partial
   `pip install` failure doesn't block you from trying the agent.

## Why an explicit `LLMClient` / `SearchTool` protocol instead of LangChain wrappers

Both are tiny structural interfaces:

```python
class LLMClient(Protocol):
    def generate(self, prompt: str, system: str | None = None) -> str: ...

class SearchTool(Protocol):
    def search(self, query: str, max_results: int = 4) -> list[SearchResult]: ...
```

Nodes depend only on these shapes, not on `langchain_openai.ChatOpenAI`
or any specific SDK. That means:

- Swapping providers (`anthropic` ↔ `openai` ↔ local `ollama`) never
  touches `nodes.py`.
- Tests use `FakeLLM(responder_fn)` / `FakeSearch(responder_fn)` — no
  network calls, no API keys, fully deterministic.
- The dependency footprint per-provider is small: you only need the SDK
  for the provider you actually chose.

## Citation handling

Every search hit or local document chunk that gets shown to the LLM is
first registered through `report.register_source()`, which:

1. Normalizes the URL (strips fragments, tracking params, trailing
   slashes) so the same page found twice — once via search, once
   because it's referenced in another sub-question's results — collapses
   to a **single** citation number instead of two.
2. Assigns the next sequential integer id the first time a URL is seen,
   and reuses it on every subsequent reference.

The synthesis prompt tells the model to cite using those exact bracketed
numbers (`[1]`, `[2][3]`), and `compile_markdown_report()` renders the
`## References` section directly from the same registry — so citation
numbers in the body always match the reference list, by construction,
rather than by post-hoc reconciliation.

## Reflection loop

After each synthesis pass, `critique_node` asks the LLM whether the
findings so far are sufficient to answer the original topic. If not, it
asks the LLM for a small number of follow-up sub-questions targeting the
identified gaps. `plan_node` consumes those follow-ups on the next round
instead of re-planning from scratch, and increments `state["iteration"]`.

Two independent safety nets prevent an infinite loop even if a model
insists nothing is ever "sufficient":

- `route_after_critique` refuses to continue once
  `iteration + 1 >= max_iterations`.
- `engine.py`'s outer loop is additionally bounded to
  `max_iterations + 1` passes regardless of what routing decides.

## Local documents

`load_documents_node` runs exactly once, before the loop starts, and
loads every path in `local_document_paths` (`.txt`, `.md`, `.pdf`) into
`state["local_documents"]`. `synthesize_node` appends those documents to
the web search results for **every** sub-question (not just one),
since a user-provided document is usually relevant to the whole topic,
not a single angle of it.
