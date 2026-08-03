"""A minimal, dependency-free orchestrator.

This runs the exact same node functions as `graph.py`'s LangGraph
wiring, in a plain Python loop. Two reasons this exists alongside the
LangGraph version:

1. It works even if `langgraph` isn't installed yet, so `pip install -r
   requirements.txt` failing on one package doesn't block you from
   trying the agent.
2. It's what the test suite uses to verify the *actual research logic*
   end-to-end without needing a real LLM, a real search API, or
   LangGraph itself — only `FakeLLM` / `FakeSearch`.

`graph.py` is the "real" / recommended way to run this project, since
learning LangGraph's state-graph model is the point of this exercise —
this module is the training-wheels version.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from .llm import LLMClient
from .nodes import (
    compile_report_node,
    critique_node,
    load_documents_node,
    plan_node,
    route_after_critique,
    search_node,
    synthesize_node,
)
from .state import ResearchState, new_state
from .tools.web_search import SearchTool

StepCallback = Callable[[str, ResearchState], None]


def run_research(
    topic: str,
    llm: LLMClient,
    search_tool: SearchTool,
    local_document_paths: Optional[List[str]] = None,
    max_results_per_query: int = 4,
    max_iterations: int = 2,
    on_step: Optional[StepCallback] = None,
) -> ResearchState:
    """Run the full plan -> search -> synthesize -> critique -> (loop or
    finish) -> compile pipeline and return the final state.

    `on_step(node_name, state)` is called after every node if provided —
    handy for CLI progress output.
    """

    state = new_state(
        topic=topic,
        local_document_paths=local_document_paths,
        max_results_per_query=max_results_per_query,
        max_iterations=max(1, max_iterations),
    )

    def step(name: str, fn) -> None:
        fn()
        if on_step:
            on_step(name, state)

    step("load_documents", lambda: load_documents_node(state))

    # Hard safety cap in addition to route_after_critique's own check,
    # so a bug can never spin this loop forever.
    for _ in range(max(1, max_iterations) + 1):
        step("plan", lambda: plan_node(state, llm))
        step("search", lambda: search_node(state, search_tool))
        step("synthesize", lambda: synthesize_node(state, llm))
        step("critique", lambda: critique_node(state, llm))

        if route_after_critique(state) == "finish":
            break

    step("compile_report", lambda: compile_report_node(state, llm))
    return state
