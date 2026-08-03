"""Citation bookkeeping and final Markdown report assembly.

Source de-duplication lives here rather than scattered across nodes:
every time a search hit or local document is turned into a numbered
citation, it goes through `register_source`, which guarantees the same
URL always maps to the same footnote number, no matter which
sub-question it showed up under.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

from .state import Finding, ResearchState, SearchResult, Source
from .utils import normalize_url, truncate


def register_source(state: ResearchState, title: str, url: str, source_type: str = "web") -> int:
    """Return the citation id for `url`, creating one if it's new."""

    url_map = state.setdefault("source_url_to_id", {})
    sources = state.setdefault("sources", [])

    key = normalize_url(url) if url else f"untitled:{title}"
    if key in url_map:
        return url_map[key]

    new_id = len(sources) + 1
    sources.append(Source(id=new_id, title=title or url or f"Source {new_id}", url=url, source_type=source_type))
    url_map[key] = new_id
    return new_id


def build_numbered_excerpts(
    state: ResearchState, results: List[SearchResult], max_chars: int = 1200
) -> List[str]:
    """Register each result as a citation and format it as a numbered
    excerpt block ready to drop into the synthesis prompt."""

    excerpts = []
    for result in results:
        source_id = register_source(state, result.title, result.url, result.source_type)
        body = result.content or result.snippet
        excerpts.append(f"[{source_id}] {result.title}\n{truncate(body, max_chars)}")
    return excerpts


def compile_markdown_report(state: ResearchState, title: str = "") -> str:
    """Assemble the final Markdown report from accumulated findings."""

    topic = state.get("topic", "Untitled research")
    title = title.strip() or f"Research Report: {topic}"
    findings: dict[str, Finding] = state.get("findings", {})
    sources: List[Source] = state.get("sources", [])
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    iterations = state.get("iteration", 0) + 1

    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"*Generated {generated_at} · {iterations} research iteration(s) · "
                 f"{len(findings)} sub-question(s) · {len(sources)} source(s)*")
    lines.append("")
    lines.append("## Table of Contents")
    for i, question in enumerate(findings.keys(), start=1):
        lines.append(f"{i}. [{question}](#{_anchor(question)})")
    lines.append(f"{len(findings) + 1}. [References](#references)")
    lines.append("")

    for question, finding in findings.items():
        lines.append(f"## {question}")
        lines.append("")
        lines.append(finding.answer.strip())
        lines.append("")

    lines.append("## References")
    lines.append("")
    if sources:
        for source in sources:
            if source.url.startswith("file://"):
                lines.append(f"{source.id}. {source.title} *(local document)*")
            else:
                lines.append(f"{source.id}. [{source.title}]({source.url})")
    else:
        lines.append("*No sources were collected during this run.*")
    lines.append("")

    return "\n".join(lines)


def _anchor(question: str) -> str:
    """Approximate the GitHub-flavored Markdown anchor for a heading."""

    import re

    anchor = question.strip().lower()
    anchor = re.sub(r"[^\w\s-]", "", anchor)
    anchor = re.sub(r"\s+", "-", anchor)
    return anchor


def findings_summary(state: ResearchState) -> str:
    """A compact plain-text summary of findings so far, used as input to
    the critique step (kept short to save tokens)."""

    findings: dict[str, Finding] = state.get("findings", {})
    parts = []
    for question, finding in findings.items():
        parts.append(f"Q: {question}\nA: {truncate(finding.answer, 500)}")
    return "\n\n".join(parts) if parts else "(no findings yet)"
