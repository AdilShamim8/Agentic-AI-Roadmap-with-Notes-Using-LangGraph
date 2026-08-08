"""Tests for the AnswerSynthesizer."""
from __future__ import annotations

import asyncio
import json

import pytest

from doc_analyst.embeddings.vlm import VLMClient
from doc_analyst.retrieval.synthesizer import AnswerSynthesizer
from doc_analyst.schemas import DocElement, ElementType, RetrievedElement


class _StubVLM(VLMClient):
    """Returns a canned JSON answer regardless of input."""

    provider = "zai"  # type: ignore[assignment]

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def caption_image(self, image_path, prompt=None):
        return "stub caption"

    async def chat(self, messages, *, json_mode=False):
        return json.dumps(self.payload)


def _make_element(idx: int, text: str) -> DocElement:
    return DocElement(
        element_id=f"doc-test::p1::e{idx}",
        doc_id="doc-test",
        page=1,
        element_index=idx,
        type=ElementType.TEXT,
        text=text,
    )


def test_synthesize_parses_json_and_maps_citations() -> None:
    elements = [
        RetrievedElement(
            element=_make_element(0, "Revenue in 2024 was USD 102 million."),
            score=0.9,
            source="text",  # type: ignore[arg-type]
        ),
        RetrievedElement(
            element=_make_element(1, "Revenue grew 16% year-over-year."),
            score=0.8,
            source="text",  # type: ignore[arg-type]
        ),
    ]
    payload = {
        "summary": "Revenue in 2024 was USD 102 million, up 16% YoY.",
        "blocks": [
            {
                "claim": "Revenue in 2024 was USD 102 million.",
                "citations": ["doc-test::p1::e0"],
            },
            {
                "claim": "Revenue grew 16% year-over-year.",
                "citations": ["doc-test::p1::e1"],
            },
        ],
        "confidence": 0.9,
    }
    synth = AnswerSynthesizer(llm=_StubVLM(payload))
    answer = asyncio.run(synth.synthesize("What was revenue in 2024?", elements))

    assert answer.question == "What was revenue in 2024?"
    assert "102" in answer.summary
    assert len(answer.blocks) == 2
    assert answer.blocks[0].citations[0].element_index == 0
    assert answer.blocks[1].citations[0].element_index == 1
    assert len(answer.citations) == 2
    assert 0.0 <= answer.confidence <= 1.0


def test_synthesize_fallback_on_bad_json() -> None:
    """If the LLM returns garbage, the synthesizer should fall back to top-1."""

    class _BadVLM(_StubVLM):
        async def chat(self, messages, *, json_mode=False):
            return "not json at all"

    elements = [
        RetrievedElement(
            element=_make_element(0, "Only relevant text we have."),
            score=0.5,
            source="text",  # type: ignore[arg-type]
        ),
    ]
    synth = AnswerSynthesizer(llm=_BadVLM({"summary": "", "blocks": [], "confidence": 0}))
    answer = asyncio.run(synth.synthesize("question?", elements))
    # Should have at least one block (from fallback).
    assert answer.blocks
    assert answer.blocks[0].citations
    assert answer.blocks[0].citations[0].element_index == 0


def test_synthesize_empty_retrieval_returns_empty_answer() -> None:
    synth = AnswerSynthesizer(llm=_StubVLM({"summary": "", "blocks": []}))
    answer = asyncio.run(synth.synthesize("?", []))
    assert answer.blocks == []
    assert answer.citations == []
