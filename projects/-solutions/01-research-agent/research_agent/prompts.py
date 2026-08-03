"""Prompt templates for each reasoning step in the graph.

Kept as plain f-string-friendly templates (no LangChain PromptTemplate
dependency) so they're trivial to read, tweak, and unit test.
"""

from __future__ import annotations

from typing import List

PLANNER_SYSTEM = (
    "You are a meticulous research planner. Given a research topic, you "
    "break it down into a focused set of sub-questions that, together, "
    "would let someone write a thorough, well-rounded report on the topic. "
    "Respond with ONLY a JSON array of strings, nothing else."
)


def planner_prompt(topic: str, num_questions: int = 4) -> str:
    return (
        f'Research topic: "{topic}"\n\n'
        f"Break this into exactly {num_questions} specific, non-overlapping "
        "sub-questions that a researcher should investigate to cover the "
        "topic well (e.g. background/definition, current state, key "
        "debates or trade-offs, and future outlook/implications — adapt "
        "these angles to fit the actual topic).\n\n"
        'Respond with ONLY a JSON array of strings, e.g.:\n'
        '["question one?", "question two?", "question three?"]'
    )


FOLLOW_UP_SYSTEM = (
    "You are a meticulous research planner refining an in-progress report "
    "based on identified gaps. Respond with ONLY a JSON array of strings."
)


def follow_up_prompt(topic: str, gaps: str, num_questions: int = 2) -> str:
    return (
        f'Original research topic: "{topic}"\n\n'
        f"Gaps identified in the current draft:\n{gaps}\n\n"
        f"Write exactly {num_questions} focused follow-up sub-questions "
        "that would close these gaps if researched.\n\n"
        'Respond with ONLY a JSON array of strings, e.g.:\n'
        '["follow up question one?", "follow up question two?"]'
    )


SYNTHESIZER_SYSTEM = (
    "You are a careful research analyst. You write clear, accurate, "
    "neutral prose synthesized strictly from the provided source "
    "excerpts. You never invent facts that aren't supported by the "
    "sources. You cite sources inline using bracketed numbers like [1] "
    "or [2][3], matching the numbers given to each source excerpt."
)


def synthesis_prompt(question: str, numbered_excerpts: List[str]) -> str:
    excerpts_block = "\n\n".join(numbered_excerpts) if numbered_excerpts else "(no sources found)"
    return (
        f'Sub-question: "{question}"\n\n'
        f"Source excerpts:\n{excerpts_block}\n\n"
        "Write a well-organized answer (2-4 paragraphs) to the "
        "sub-question using only information from the excerpts above. "
        "Cite the excerpt number(s) supporting each claim using bracketed "
        "numbers, e.g. 'Adoption grew sharply in 2025 [2].' If the "
        "excerpts don't contain enough information to answer well, say so "
        "plainly instead of guessing."
    )


CRITIC_SYSTEM = (
    "You are an exacting editor reviewing a research draft for "
    "completeness. Respond with ONLY a JSON object, nothing else."
)


def critique_prompt(topic: str, findings_summary: str) -> str:
    return (
        f'Research topic: "{topic}"\n\n'
        f"Current findings:\n{findings_summary}\n\n"
        "Decide whether these findings are sufficient to write a "
        "thorough, well-rounded report on the topic, or whether there are "
        "important gaps.\n\n"
        "Respond with ONLY a JSON object of the form:\n"
        '{"sufficient": true or false, "gaps": "short description of '
        'missing angles, or empty string if sufficient"}'
    )


REPORT_TITLE_SYSTEM = (
    "You write short, specific, professional report titles. Respond with "
    "ONLY the title text, nothing else — no quotes, no markdown."
)


def report_title_prompt(topic: str) -> str:
    return f'Write a concise, specific report title (under 12 words) for research on: "{topic}"'
