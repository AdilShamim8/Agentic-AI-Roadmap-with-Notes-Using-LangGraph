"""LangGraph retrieval agent.

Builds a small graph with two nodes:

    [retrieve] -> [synthesize] -> END

State is a Pydantic model so it's serialisable and typed.

The graph is exposed as `build_graph()` and the module-level helper
`ask(question, doc_ids=None)` runs the graph end-to-end.
"""
from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from ..config import settings
from ..retrieval.retriever import MultimodalRetriever
from ..retrieval.synthesizer import AnswerSynthesizer
from ..schemas import Answer, RetrievedElement
from ..utils.logging import get_logger

log = get_logger(__name__)


# ----------------------------------------------------------------------
# State
# ----------------------------------------------------------------------
class AgentState(BaseModel):
    """Mutable state passed between graph nodes."""

    question: str
    doc_ids: list[str] | None = None
    retrieved: list[RetrievedElement] = Field(default_factory=list)
    answer: Answer | None = None
    started_at: float = 0.0
    finished_at: float = 0.0

    model_config = {"arbitrary_types_allowed": True}


# ----------------------------------------------------------------------
# Nodes
# ----------------------------------------------------------------------
class RetrieveNode:
    def __init__(self, retriever: MultimodalRetriever | None = None) -> None:
        self.retriever = retriever or MultimodalRetriever()

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        hits = self.retriever.retrieve(state.question, doc_ids=state.doc_ids)
        log.info(
            "retrieve: %d hits for '%.40s'",
            len(hits),
            state.question,
        )
        return {"retrieved": hits}


class SynthesizeNode:
    def __init__(self, synthesizer: AnswerSynthesizer | None = None) -> None:
        self.synthesizer = synthesizer or AnswerSynthesizer()

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        answer = await self.synthesizer.synthesize(state.question, state.retrieved)
        return {"answer": answer, "finished_at": time.perf_counter()}


# ----------------------------------------------------------------------
# Graph builder
# ----------------------------------------------------------------------
def build_graph(
    retriever: MultimodalRetriever | None = None,
    synthesizer: AnswerSynthesizer | None = None,
):
    """Compile and return the LangGraph workflow."""
    g = StateGraph(AgentState)

    retrieve_node = RetrieveNode(retriever=retriever)
    synthesize_node = SynthesizeNode(synthesizer=synthesizer)

    g.add_node("retrieve", retrieve_node)
    g.add_node("synthesize", synthesize_node)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "synthesize")
    g.add_edge("synthesize", END)

    return g.compile()


# ----------------------------------------------------------------------
# Public entrypoint
# ----------------------------------------------------------------------
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def ask(question: str, doc_ids: list[str] | None = None) -> Answer:
    """Ask a question against the indexed corpus. Returns a structured Answer."""
    state = AgentState(question=question, doc_ids=doc_ids, started_at=time.perf_counter())
    graph = get_graph()
    final = await graph.ainvoke(state)
    return final["answer"]
