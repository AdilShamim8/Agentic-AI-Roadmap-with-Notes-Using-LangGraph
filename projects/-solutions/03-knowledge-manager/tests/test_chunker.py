"""Tests for the chunker."""
from __future__ import annotations

from knowledge_manager.ingestion.chunker import chunk_text


def test_empty_text() -> None:
    assert chunk_text("") == []


def test_short_text_returns_single_chunk() -> None:
    out = chunk_text("hello world", chunk_size=800, chunk_overlap=120)
    assert len(out) == 1
    assert out[0].text == "hello world"
    assert out[0].position == 0


def test_long_text_is_split() -> None:
    text = ("alpha beta gamma delta. " * 200).strip()  # ~5k chars
    chunks = chunk_text(text, chunk_size=400, chunk_overlap=40)
    assert len(chunks) >= 10
    # Every chunk should be <= chunk_size (modulo overlap slack)
    for c in chunks:
        assert len(c.text) <= 500


def test_chunk_positions_are_unique_and_ordered() -> None:
    text = "sentence one. " * 200
    chunks = chunk_text(text, chunk_size=300, chunk_overlap=30)
    positions = [c.position for c in chunks]
    assert positions == sorted(positions)
    assert len(positions) == len(set(positions))
