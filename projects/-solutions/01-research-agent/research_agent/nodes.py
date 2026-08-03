"""The five reasoning steps of the research agent, as plain functions.

Every node has the signature `(state, ...deps) -> state` and mutates the
state dict in place (then returns it, which is what LangGraph expects
from a node function). Because dependencies (the LLM client, the search
tool) are passed in as plain arguments rather than pulled from globals
or a LangChain wrapper, every node can be unit tested in isolation with
`FakeLLM` / `FakeSearch` — no network, no API key, no LangGraph
installation required.

Graph shape (see graph.py / engine.py for the wiring):

    load_documents -> plan -> search -> synthesize -> critique
                                ^                         |
                                |     (continue)           |
                                +-------------------------+
                                            | (finish)
                                            v
                                      compile_report
"""

from __future__ import annotations

from typing import List

from .llm import LLMClient
from .prompts import (
    CRITIC_SYSTEM,
    FOLLOW_UP_SYSTEM,
    PLANNER_SYSTEM,
    REPORT_TITLE_SYSTEM,
    SYNTHESIZER_SYSTEM,
    critique_prompt,
    follow_up_prompt,
    planner_prompt,
    report_title_prompt,
    synthesis_prompt,
)
from .report import build_numbered_excerpts, compile_markdown_report, findings_summary
from .state import Finding, ResearchState, log_event
from .tools.documents import load_local_documents
from .tools.web_search import SearchTool
from .utils import safe_json_parse

DEFAULT_SUB_QUESTIONS = 4
DEFAULT_FOLLOW_UPS = 2


def load_documents_node(state: ResearchState) -> ResearchState:
    """Runs once, before the research loop starts."""

    paths = state.get("local_document_paths", [])
    docs = load_local_documents(paths) if paths else []
    state["local_documents"] = docs
    log_event(state, f"Loaded {len(docs)} local document(s) from {len(paths)} path(s).")
    return state


def plan_node(state: ResearchState, llm: LLMClient) -> ResearchState:
    """Produce the sub-questions to research this round.

    Round 0 breaks the topic down from scratch. Later rounds consume the
    follow-up questions the critique step generated.
    """

    topic = state["topic"]
    follow_ups = state.get("follow_up_questions") or []

    if follow_ups:
        state["iteration"] = state.get("iteration", 0) + 1
        state["sub_questions"] = follow_ups
        state["follow_up_questions"] = []
        log_event(state, f"Iteration {state['iteration']}: planning follow-up questions {follow_ups}")
        return state

    raw = llm.generate(planner_prompt(topic, DEFAULT_SUB_QUESTIONS), system=PLANNER_SYSTEM)
    parsed = safe_json_parse(raw)
    questions = [q for q in parsed if isinstance(q, str) and q.strip()] if isinstance(parsed, list) else []
    if not questions:
        questions = [topic]

    state["sub_questions"] = questions
    log_event(state, f"Iteration 0: planned {len(questions)} sub-question(s).")
    return state


def search_node(state: ResearchState, search_tool: SearchTool) -> ResearchState:
    """Run a web search for each pending sub-question."""

    max_results = state.get("max_results_per_query", 4)
    search_results = state.setdefault("search_results", {})

    for question in state.get("sub_questions", []):
        if question in search_results:
            continue  # already searched (defensive; shouldn't normally happen)
        try:
            hits = search_tool.search(question, max_results=max_results)
        except Exception as exc:  # a flaky network call should not kill the run
            log_event(state, f"Search failed for '{question}': {exc}")
            hits = []
        search_results[question] = hits
        log_event(state, f"Found {len(hits)} result(s) for: {question}")

    return state


def synthesize_node(state: ResearchState, llm: LLMClient) -> ResearchState:
    """Turn search results (+ local documents) into a cited answer for
    each pending sub-question."""

    findings = state.setdefault("findings", {})
    local_documents = state.get("local_documents", [])

    for question in state.get("sub_questions", []):
        if question in findings:
            continue
        web_hits = state.get("search_results", {}).get(question, [])
        combined = list(web_hits) + list(local_documents)
        excerpts = build_numbered_excerpts(state, combined)
        citation_ids = _extract_leading_ids(excerpts)

        answer = llm.generate(synthesis_prompt(question, excerpts), system=SYNTHESIZER_SYSTEM)
        findings[question] = Finding(question=question, answer=answer, citation_ids=citation_ids)
        log_event(state, f"Synthesized answer for: {question}")

    return state


def critique_node(state: ResearchState, llm: LLMClient) -> ResearchState:
    """Decide whether the findings so far are sufficient, and if not,
    propose follow-up sub-questions to close the gaps."""

    topic = state["topic"]
    summary = findings_summary(state)

    raw = llm.generate(critique_prompt(topic, summary), system=CRITIC_SYSTEM)
    parsed = safe_json_parse(raw)
    if not isinstance(parsed, dict):
        parsed = {"sufficient": True, "gaps": ""}

    is_sufficient = bool(parsed.get("sufficient", True))
    gaps = str(parsed.get("gaps", "") or "")

    state["is_sufficient"] = is_sufficient
    state["critique_notes"] = gaps

    if is_sufficient or not gaps.strip():
        state["follow_up_questions"] = []
        log_event(state, "Critique: findings are sufficient.")
        return state

    raw_follow_ups = llm.generate(
        follow_up_prompt(topic, gaps, DEFAULT_FOLLOW_UPS), system=FOLLOW_UP_SYSTEM
    )
    parsed_follow_ups = safe_json_parse(raw_follow_ups)
    follow_ups = (
        [q for q in parsed_follow_ups if isinstance(q, str) and q.strip()]
        if isinstance(parsed_follow_ups, list)
        else []
    )
    state["follow_up_questions"] = follow_ups
    log_event(state, f"Critique: gaps found ({gaps!r}); proposed {len(follow_ups)} follow-up(s).")
    return state


def route_after_critique(state: ResearchState) -> str:
    """Pure routing function — decides whether to loop back to `plan`
    or move on to `compile_report`. Never mutates state."""

    if state.get("is_sufficient", True):
        return "finish"
    if not state.get("follow_up_questions"):
        return "finish"
    if state.get("iteration", 0) + 1 >= state.get("max_iterations", 1):
        return "finish"
    return "continue"


def compile_report_node(state: ResearchState, llm: LLMClient | None = None) -> ResearchState:
    """Generate a title (if an LLM is available) and assemble the final
    Markdown report."""

    title = ""
    if llm is not None:
        try:
            title = llm.generate(report_title_prompt(state["topic"]), system=REPORT_TITLE_SYSTEM).strip()
        except Exception as exc:
            log_event(state, f"Title generation failed, using default: {exc}")
            title = ""

    state["report"] = compile_markdown_report(state, title)
    log_event(state, "Report compiled.")
    return state


def _extract_leading_ids(excerpts: List[str]) -> List[int]:
    """Pull the "[3]" style ids back out of formatted excerpt strings."""

    ids = []
    for excerpt in excerpts:
        if excerpt.startswith("["):
            end = excerpt.find("]")
            if end > 1:
                try:
                    ids.append(int(excerpt[1:end]))
                except ValueError:
                    pass
    return ids
