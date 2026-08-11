"""Sample summarizer agent — extracts bullet points from long text."""
import asyncio
import re
from typing import Any


def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


async def handle(input_text: str) -> str:
    """Summarize text into 3-5 bullet points.

    This is a heuristic summarizer — in production you'd call an LLM.
    """
    await asyncio.sleep(0.05)

    sentences = _split_sentences(input_text)
    if len(sentences) <= 3:
        return f"[Summarizer] Text is already short ({len(sentences)} sentence(s)):\n\n" + \
               "\n".join(f"- {s}" for s in sentences)

    # Heuristic: pick first sentence, longest sentence, and sentence with
    # the most "keyword" capitalization as bullets.
    first = sentences[0]
    longest = max(sentences, key=len)
    candidates = [s for s in sentences if s != first and s != longest]

    # Pick a sentence in the middle for the third bullet
    middle_idx = len(candidates) // 2
    middle = candidates[middle_idx] if candidates else longest

    bullets = [first, middle, longest][:3]

    summary = "\n".join(f"- {b}" for b in bullets)
    return f"[Summarizer] Summary of {len(sentences)} sentences:\n\n{summary}"
