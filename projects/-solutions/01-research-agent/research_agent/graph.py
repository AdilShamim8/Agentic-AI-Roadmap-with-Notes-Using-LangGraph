"""LangGraph wiring for the research agent.

This is the "real" implementation the roadmap project is about: a
`StateGraph` with a conditional loop back to `plan` for follow-up
research rounds. It wires up exactly the same node functions used by
`engine.py`'s dependency-free runner — only the orchestration differs.

Requires: pip install langgraph
"""

from __future__ import annotations

from typing import Optional

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
from .state import ResearchState
from .tools.web_search import SearchTool


def build_graph(llm: LLMClient, search_tool: SearchTool):
    """Compile and return a runnable LangGraph app.

    Usage:
        app = build_graph(llm, search_tool)
        final_state = app.invoke(new_state(topic="..."))
    """

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise ImportError(
            "The 'langgraph' package is required for graph.py. "
            "Install it with: pip install langgraph\n"
            "(Or use research_agent.engine.run_research, which needs no "
            "graph library at all.)"
        ) from exc

    graph = StateGraph(ResearchState)

    graph.add_node("load_documents", load_documents_node)
    graph.add_node("plan", lambda state: plan_node(state, llm))
    graph.add_node("search", lambda state: search_node(state, search_tool))
    graph.add_node("synthesize", lambda state: synthesize_node(state, llm))
    graph.add_node("critique", lambda state: critique_node(state, llm))
    graph.add_node("compile_report", lambda state: compile_report_node(state, llm))

    graph.add_edge(START, "load_documents")
    graph.add_edge("load_documents", "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "synthesize")
    graph.add_edge("synthesize", "critique")
    graph.add_conditional_edges(
        "critique",
        route_after_critique,
        {"continue": "plan", "finish": "compile_report"},
    )
    graph.add_edge("compile_report", END)

    return graph.compile()
