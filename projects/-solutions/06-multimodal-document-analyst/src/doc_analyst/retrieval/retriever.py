"""Multimodal retriever.

The README architecture calls for "multimodal retrieval - vector search
on text and captions, plus structured queries on tables". We implement
exactly that:

  - `retrieve_text(query)`  -> top-K text blocks from `doc_text`
  - `retrieve_captions(query)` -> top-K image captions from `doc_captions`
  - `retrieve_tables(query)`  -> top-K table rows (served from `doc_text`,
    filtered to `element_type=table`)

The retriever also de-duplicates and merges results into a single
`RetrievedElement` list ordered by score.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..config import settings
from ..schemas import DocElement, ElementType, RetrievedElement
from ..storage.vector_store import VectorStore, get_store
from ..utils.logging import get_logger

log = get_logger(__name__)


class MultimodalRetriever:
    def __init__(self, store: VectorStore | None = None) -> None:
        self.store = store or get_store()

    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        *,
        doc_ids: list[str] | None = None,
        k_text: int | None = None,
        k_captions: int | None = None,
    ) -> list[RetrievedElement]:
        """Run text + caption + table retrieval and merge by element_id."""
        k_text = k_text or settings.top_k_text
        k_captions = k_captions or settings.top_k_captions

        text_hits = self.store.search_text(query, k=k_text, doc_ids=doc_ids)
        cap_hits = self.store.search_captions(query, k=k_captions, doc_ids=doc_ids)

        # Split text hits into text vs table.
        merged: dict[str, RetrievedElement] = {}
        for el, score in text_hits:
            source = "table" if el.type == ElementType.TABLE else "text"
            existing = merged.get(el.element_id)
            if existing is None or score > existing.score:
                merged[el.element_id] = RetrievedElement(element=el, score=score, source=source)  # type: ignore[arg-type]
        for el, score in cap_hits:
            existing = merged.get(el.element_id)
            if existing is None or score > existing.score:
                merged[el.element_id] = RetrievedElement(element=el, score=score, source="caption")  # type: ignore[arg-type]

        return sorted(merged.values(), key=lambda r: r.score, reverse=True)

    # ------------------------------------------------------------------
    def retrieve_tables_only(
        self,
        query: str,
        *,
        doc_ids: list[str] | None = None,
        k: int | None = None,
    ) -> list[RetrievedElement]:
        """Structured query for tables — kept as a separate method since
        the agent may want to handle tables differently (e.g. emit a
        Markdown snippet in the answer).
        """
        k = k or settings.top_k_tables
        text_hits = self.store.search_text(query, k=k * 2, doc_ids=doc_ids)
        out: list[RetrievedElement] = []
        for el, score in text_hits:
            if el.type == ElementType.TABLE:
                out.append(RetrievedElement(element=el, score=score, source="table"))  # type: ignore[arg-type]
        return out[:k]
