"""Stub asker + retriever for environments without an OpenAI key.

Used by `eval/run_eval.py --stub` so the harness can run end-to-end without
making LLM calls. The stub uses BM25-style token overlap (no embeddings, no
LLM) and produces empty provenance — enough to verify the data plumbing
without burning tokens.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from time import perf_counter
from typing import Iterable

from knowledge_manager.storage.db import get_conn


_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


@dataclass
class _StubHit:
    chunk_id: int
    doc_id: int
    text: str
    title: str
    path: str
    position: int
    score: float


def _bm25_retrieve(question: str, top_k: int = 5) -> list[_StubHit]:
    """Cheap BM25-style retrieval: tokenise the question, score each chunk
    by the count of question tokens it contains, normalised by chunk length.
    """
    q_tokens = set(_tokenize(question))
    if not q_tokens:
        return []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT c.id, c.doc_id, c.text, c.position, d.title, d.path "
            "FROM chunks c JOIN documents d ON d.id = c.doc_id"
        ).fetchall()
    scored: list[_StubHit] = []
    for r in rows:
        chunk_tokens = _tokenize(r["text"])
        if not chunk_tokens:
            continue
        overlap = sum(1 for t in chunk_tokens if t in q_tokens)
        if overlap == 0:
            continue
        score = overlap / (len(chunk_tokens) ** 0.5)  # TF normalised by sqrt(doc len)
        scored.append(
            _StubHit(
                chunk_id=r["id"],
                doc_id=r["doc_id"],
                text=r["text"],
                title=r["title"],
                path=r["path"],
                position=r["position"],
                score=score,
            )
        )
    scored.sort(key=lambda h: h.score, reverse=True)
    return scored[:top_k]


@dataclass
class _StubResp:
    question: str
    answer: str
    sources: list[dict] = field(default_factory=list)
    provenance: list[dict] = field(default_factory=list)
    elapsed_s: float = 0.0


def stub_retriever(question: str, top_k: int = 5):
    """Drop-in replacement for `hybrid.search` that doesn't call the LLM."""
    return _bm25_retrieve(question, top_k=top_k)


def stub_ask(question: str):
    t0 = perf_counter()
    hits = _bm25_retrieve(question, top_k=5)
    if not hits:
        return _StubResp(question=question, answer="(no sources)", elapsed_s=perf_counter() - t0)
    answer = "Stub answer — top source: " + hits[0].title
    sources = [
        {
            "chunk_id": h.chunk_id,
            "doc_id": h.doc_id,
            "text": h.text,
            "title": h.title,
            "path": h.path,
            "position": h.position,
            "fused_score": h.score,
            "vector_score": h.score,
            "graph_score": 0.0,
            "matched_entities": [],
        }
        for h in hits
    ]
    return _StubResp(
        question=question,
        answer=answer,
        sources=sources,
        provenance=[
            {
                "citation": 1,
                "chunk_id": hits[0].chunk_id,
                "doc_id": hits[0].doc_id,
                "title": hits[0].title,
                "path": hits[0].path,
                "position": hits[0].position,
                "score": hits[0].score,
            }
        ],
        elapsed_s=perf_counter() - t0,
    )

