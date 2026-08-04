"""
Builds the LangGraph graph:

                          +------------------+
                          |      intake      |  sentiment + id extraction
                          +------------------+
                                    |
                                    v
                          +------------------+
                          |     supervisor   |  keyword-based routing
                          +------------------+
                                    |
             +---------+-----------+-----------+---------+
             v         v           v           v         v
        billing_ai  technical_ai order_ai  general_ai  escalation
             |         |           |           |            |
             +---------+-----------+-----------+            |
                                    v                        |
                              +-----------+                  |
                              |  reviewer |                  |
                              +-----------+                  |
                               |         |                   |
                            (ok)      (needs escalation)      |
                               v         v                   v
                              END    escalation ------------> END

A `MemorySaver` checkpointer gives every conversation ("thread_id") its own
persisted state, so multi-turn conversations remember prior customer_id,
category, etc. without the caller having to resend history manually.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app import agents
from app.state import AgentState


def build_graph(checkpointer: MemorySaver | None = None):
    graph = StateGraph(AgentState)

    graph.add_node("intake", agents.intake)
    graph.add_node("supervisor", agents.supervisor)
    graph.add_node("billing_agent", agents.billing_agent)
    graph.add_node("technical_agent", agents.technical_agent)
    graph.add_node("order_agent", agents.order_agent)
    graph.add_node("general_agent", agents.general_agent)
    graph.add_node("escalation", agents.escalation)
    graph.add_node("reviewer", agents.reviewer)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        agents.route_after_supervisor,
        {
            "billing": "billing_agent",
            "technical": "technical_agent",
            "order": "order_agent",
            "general": "general_agent",
            "escalation": "escalation",
        },
    )

    for specialist in ("billing_agent", "technical_agent", "order_agent", "general_agent"):
        graph.add_edge(specialist, "reviewer")

    graph.add_conditional_edges(
        "reviewer",
        agents.route_after_reviewer,
        {"escalation": "escalation", "end": END},
    )

    graph.add_edge("escalation", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())


def default_initial_state() -> dict:
    """Fields the caller doesn't need to set explicitly - LangGraph fills in `messages` per-turn."""
    return {
        "customer_id": None,
        "category": None,
        "sentiment": "neutral",
        "resolved": False,
        "needs_escalation": False,
        "ticket_id": None,
    }
