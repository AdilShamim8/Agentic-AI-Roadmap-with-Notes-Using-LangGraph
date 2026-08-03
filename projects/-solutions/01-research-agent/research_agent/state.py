"""Typed state shared across every node in the research graph.

Keeping this in one place means every node — whether it's driven by
LangGraph or by the dependency-free `engine.py` runner — agrees on the
exact same shape of data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


@dataclass
class SearchResult:
    """A single hit returned by a search tool."""

    title: str
    url: str
    snippet: str
    content: str = ""  # populated later by the fetch step, may stay empty
    source_type: str = "web"  # "web" | "local_document"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "content": self.content,
            "source_type": self.source_type,
        }


@dataclass
class Source:
    """A deduplicated, numbered reference used in the final report."""

    id: int
    title: str
    url: str
    source_type: str = "web"


@dataclass
class Finding:
    """The synthesized answer to a single sub-question, with citations."""

    question: str
    answer: str
    citation_ids: List[int] = field(default_factory=list)


class ResearchState(TypedDict, total=False):
    """The full state object that flows through the graph.

    `total=False` because different nodes populate different keys over
    the course of a run — nothing is required to exist from the start
    except `topic`.
    """

    # Input
    topic: str
    local_document_paths: List[str]
    max_results_per_query: int
    max_iterations: int

    # Working state
    iteration: int
    sub_questions: List[str]
    local_documents: List[SearchResult]
    search_results: Dict[str, List[SearchResult]]
    findings: Dict[str, Finding]
    sources: List[Source]
    source_url_to_id: Dict[str, int]

    # Reflection / control flow
    is_sufficient: bool
    follow_up_questions: List[str]
    critique_notes: str

    # Output
    report: str
    log: List[str]


def new_state(
    topic: str,
    local_document_paths: Optional[List[str]] = None,
    max_results_per_query: int = 4,
    max_iterations: int = 2,
) -> ResearchState:
    """Build a fresh, empty state for a new research run."""

    return ResearchState(
        topic=topic,
        local_document_paths=local_document_paths or [],
        max_results_per_query=max_results_per_query,
        max_iterations=max_iterations,
        iteration=0,
        sub_questions=[],
        local_documents=[],
        search_results={},
        findings={},
        sources=[],
        source_url_to_id={},
        is_sufficient=False,
        follow_up_questions=[],
        critique_notes="",
        report="",
        log=[],
    )


def log_event(state: ResearchState, message: str) -> None:
    """Append a human-readable trace line. Mutates state in place."""

    state.setdefault("log", []).append(message)
