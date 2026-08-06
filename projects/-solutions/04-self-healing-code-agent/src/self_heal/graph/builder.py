"""Build the LangGraph state machine for the self-healing agent.

Topology:

    START
      ↓
    reproduce ──(already passing)──▶ END
      │
      ↓ (failing)
    diagnose ◀──────────────────────┐
      │                             │
      ↓                             │
    patch                           │
      │                             │
      ↓                             │
    verify                          │ (retry)
      │                             │
      ├──(passed)──▶ submit ──▶ END │
      │                             │
      ↓ (failed)                    │
    reflexion ──────────────────────┘
      │
      ↓ (max iterations)
    END (exhausted)
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from self_heal.graph.nodes import (
    diagnose,
    patch,
    record_iteration,
    reproduce,
    route_after_reflexion,
    route_after_verify,
    submit,
    verify,
)
from self_heal.graph.state import AgentState
from self_heal.llm.base import LLMProvider, provider_factory
from self_heal.logging import get_logger

log = get_logger(__name__)


def build_agent_graph(provider: LLMProvider | None = None):
    """Compile and return the LangGraph runnable.

    Args:
        provider: LLM backend. If None, the configured provider is built via
            `provider_factory()`.
    """
    p = provider or provider_factory()

    graph = StateGraph(AgentState)

    # Bind the provider into the LLM-using nodes via partial application so the
    # node signature stays `(state) -> state`.
    graph.add_node("reproduce", reproduce)
    graph.add_node("diagnose", partial(diagnose, provider=p))
    graph.add_node("patch", partial(patch, provider=p))
    graph.add_node("verify", verify)
    graph.add_node("reflexion", partial(_reflexion_and_record, provider=p))
    graph.add_node("submit", submit)

    graph.add_edge(START, "reproduce")

    # If the test is already passing, end.
    graph.add_conditional_edges(
        "reproduce",
        lambda s: "submit" if s.get("status") == "passed" else "diagnose",
        {"submit": "submit", "diagnose": "diagnose"},
    )

    graph.add_edge("diagnose", "patch")
    graph.add_edge("patch", "verify")

    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {"submit": "submit", "reflexion": "reflexion"},
    )

    graph.add_conditional_edges(
        "reflexion",
        route_after_reflexion,
        {"diagnose": "diagnose", "end_exhausted": END},
    )

    graph.add_edge("submit", END)

    compiled = graph.compile()
    log.debug("graph.built", provider=p.name)
    return compiled


def _reflexion_and_record(state: AgentState, provider: LLMProvider) -> AgentState:
    """Combined node: run reflexion, then record the iteration into history."""
    from self_heal.graph.nodes import reflexion

    new_state = reflexion(state, provider)
    return record_iteration(new_state)
