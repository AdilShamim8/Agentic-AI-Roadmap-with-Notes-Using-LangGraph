"""ChromaDB-backed vector store.

Two collections are kept:
  - `doc_text`: one row per TEXT or TABLE element. For tables we embed the
    Markdown-ish serialisation produced by the ingester.
  - `doc_captions`: one row per IMAGE element, embedding the VLM caption.

Each row's `metadata` carries the doc_id, page, element_index, element_type,
and a snippet — enough to rebuild a `Citation` later without re-reading the
PDF.
"""
from __future__ import annotations

import json
from typing import Any, Iterable

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import settings
from ..schemas import Citation, DocElement, DocSummary, ElementType
from ..utils.logging import get_logger
from ..embeddings.embeddings import get_embedding_client

log = get_logger(__name__)


class VectorStore:
    """Persistent vector store wrapping ChromaDB."""

    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(
            path=str(settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
        self._embed_fn = None
        # Try to use the SentenceTransformer embedding function (all-MiniLM-L6-v2).
        # If the `sentence-transformers` package isn't installed, fall back to
        # ChromaDB's bundled ONNX-based default embedder (same model, no extra
        # deps). Either way the embedding dimension is 384.
        try:
            from chromadb.utils import embedding_functions  # type: ignore

            self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.embedding_model
            )
            # Smoke-test that the import actually works.
            _ = self._embed_fn(["ping"])[0]
        except Exception as exc:  # noqa: BLE001
            log.info(
                "SentenceTransformer unavailable (%s); "
                "using ChromaDB bundled ONNX default embedder.",
                str(exc)[:80],
            )
            self._embed_fn = None  # None => Chroma uses its bundled default

        self._text_col = self._client.get_or_create_collection(
            name=settings.chroma_text_collection,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        self._caption_col = self._client.get_or_create_collection(
            name=settings.chroma_caption_collection,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def index_elements(self, doc_id: str, elements: Iterable[DocElement]) -> None:
        """Upsert text/table/image elements into the appropriate collections."""
        text_ids: list[str] = []
        text_docs: list[str] = []
        text_meta: list[dict[str, Any]] = []
        cap_ids: list[str] = []
        cap_docs: list[str] = []
        cap_meta: list[dict[str, Any]] = []

        for el in elements:
            if el.type == ElementType.TEXT and el.text.strip():
                text_ids.append(el.element_id)
                text_docs.append(el.text)
                text_meta.append(self._meta_for(el, snippet=el.text[:200]))
            elif el.type == ElementType.TABLE and el.text.strip():
                text_ids.append(el.element_id)
                text_docs.append(el.text)
                text_meta.append(self._meta_for(el, snippet=el.text[:200]))
            elif el.type == ElementType.IMAGE:
                # Image elements need a caption to be embeddable.
                # If the ingester hasn't run the VLM yet (caption is None),
                # this element is silently skipped. The indexer module is
                # responsible for captioning before calling index_elements.
                if el.caption:
                    cap_ids.append(el.element_id)
                    cap_docs.append(el.caption)
                    cap_meta.append(self._meta_for(el, snippet=el.caption[:200]))

        if text_ids:
            self._text_col.upsert(ids=text_ids, documents=text_docs, metadatas=text_meta)
        if cap_ids:
            self._caption_col.upsert(ids=cap_ids, documents=cap_docs, metadatas=cap_meta)
        log.info(
            "Indexed %s: %d text/table rows, %d caption rows",
            doc_id,
            len(text_ids),
            len(cap_ids),
        )

    def update_caption(self, element: DocElement) -> None:
        """Add or update a single image element's caption row."""
        if element.type != ElementType.IMAGE or not element.caption:
            return
        self._caption_col.upsert(
            ids=[element.element_id],
            documents=[element.caption],
            metadatas=[self._meta_for(element, snippet=element.caption[:200])],
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def search_text(self, query: str, k: int | None = None, doc_ids: list[str] | None = None) -> list[tuple[DocElement, float]]:
        return self._search(self._text_col, query, k or settings.top_k_text, doc_ids)

    def search_captions(self, query: str, k: int | None = None, doc_ids: list[str] | None = None) -> list[tuple[DocElement, float]]:
        return self._search(self._caption_col, query, k or settings.top_k_captions, doc_ids)

    def _search(
        self,
        collection,
        query: str,
        k: int,
        doc_ids: list[str] | None,
    ) -> list[tuple[DocElement, float]]:
        if not query.strip():
            return []
        where: dict[str, Any] | None = None
        if doc_ids:
            where = {"doc_id": {"$in": list(doc_ids)}}
        try:
            res = collection.query(query_texts=[query], n_results=k, where=where)
        except Exception as exc:  # noqa: BLE001
            log.warning("vector query failed: %s", exc)
            return []
        out: list[tuple[DocElement, float]] = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for i, _id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            doc_text = docs[i] if i < len(docs) else ""
            dist = float(dists[i]) if i < len(dists) else 1.0
            score = max(0.0, 1.0 - dist)  # cosine distance -> similarity
            el = self._element_from_meta(meta, doc_text)
            out.append((el, score))
        return out

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete_doc(self, doc_id: str) -> None:
        for col in (self._text_col, self._caption_col):
            try:
                col.delete(where={"doc_id": doc_id})
            except Exception as exc:  # noqa: BLE001
                log.warning("delete failed for %s in %s: %s", doc_id, col.name, exc)

    def count_for_doc(self, doc_id: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for name, col in (("text", self._text_col), ("captions", self._caption_col)):
            try:
                got = col.get(where={"doc_id": doc_id})
                out[name] = len(got.get("ids", []))
            except Exception as exc:  # noqa: BLE001
                log.warning("count failed: %s", exc)
                out[name] = -1
        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _meta_for(el: DocElement, snippet: str) -> dict[str, Any]:
        return {
            "doc_id": el.doc_id,
            "page": el.page,
            "element_index": el.element_index,
            "element_type": el.type.value,
            "snippet": snippet,
            "bbox": json.dumps(list(el.bbox)) if el.bbox else None,
            "image_path": el.image_path,
            "caption": el.caption,
        }

    @staticmethod
    def _element_from_meta(meta: dict[str, Any], doc_text: str) -> DocElement:
        bbox_raw = meta.get("bbox")
        bbox = None
        if bbox_raw:
            try:
                bbox = tuple(json.loads(bbox_raw))
            except Exception:  # noqa: BLE001
                bbox = None
        return DocElement(
            element_id=f"{meta.get('doc_id')}::p{meta.get('page')}::e{meta.get('element_index')}",
            doc_id=meta.get("doc_id", ""),
            page=int(meta.get("page", 0)),
            element_index=int(meta.get("element_index", 0)),
            type=ElementType(meta.get("element_type", "text")),
            text=doc_text,
            image_path=meta.get("image_path"),
            caption=meta.get("caption"),
            bbox=bbox,
        )

    def to_citation(self, el: DocElement, source: str) -> Citation:
        snippet = el.caption if (el.type == ElementType.IMAGE and el.caption) else (
            el.text[:200] if el.text else ""
        )
        return Citation(
            doc_id=el.doc_id,
            page=el.page,
            element_index=el.element_index,
            element_type=el.type,
            snippet=snippet,
            source=source,  # type: ignore[arg-type]
        )


# ----------------------------------------------------------------------
# Module-level singleton
# ----------------------------------------------------------------------
_store: VectorStore | None = None


def get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def reset_store() -> None:
    """For tests / CLI `clear`."""
    global _store
    _store = None
