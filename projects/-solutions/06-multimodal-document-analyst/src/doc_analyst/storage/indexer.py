"""Indexer service.

This is the "Indexing" stage of the README architecture:
  - text embedded for vector search;
  - images captioned (via a VLM) and captions embedded;
  - tables structured as JSON (and also embedded as text).

The Indexer orchestrates: PDFIngester -> VLM captioner -> VectorStore,
and writes a row to the DocRegistry so the CLI/API can list documents.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable

from ..config import settings
from ..embeddings.vlm import get_vlm_client
from ..ingest.pdf_ingester import PDFIngester
from ..schemas import DocElement, DocSummary, ElementType
from ..storage.doc_registry import get_registry
from ..storage.vector_store import get_store, reset_store
from ..utils.logging import get_logger

log = get_logger(__name__)


class Indexer:
    def __init__(
        self,
        ingester: PDFIngester | None = None,
        vlm=None,
        store=None,
        registry=None,
    ) -> None:
        self.ingester = ingester or PDFIngester()
        self.vlm = vlm  # lazy
        self.store = store  # lazy
        self.registry = registry  # lazy

    # ------------------------------------------------------------------
    async def ingest_pdf(self, pdf_path: Path | str) -> DocSummary:
        """Ingest, caption, and index a single PDF."""
        summary, pages = self.ingester.ingest(pdf_path)

        # Caption all image elements (in parallel, capped).
        elements: list[DocElement] = []
        for p in pages:
            elements.extend(p.elements)
        image_elements = [e for e in elements if e.type == ElementType.IMAGE]

        if image_elements:
            vlm = self.vlm or get_vlm_client()
            log.info("Captioning %d images for %s", len(image_elements), summary.doc_id)
            await self._caption_in_parallel(vlm, image_elements, concurrency=4)

        # Index.
        store = self.store or get_store()
        store.index_elements(summary.doc_id, elements)

        # Register.
        registry = self.registry or get_registry()
        registry.upsert(summary)
        return summary

    # ------------------------------------------------------------------
    async def ingest_many(self, pdf_paths: Iterable[Path | str]) -> list[DocSummary]:
        out: list[DocSummary] = []
        for p in pdf_paths:
            try:
                out.append(await self.ingest_pdf(p))
            except Exception as exc:  # noqa: BLE001
                log.error("Failed to ingest %s: %s", p, exc)
        return out

    # ------------------------------------------------------------------
    def delete_doc(self, doc_id: str) -> bool:
        store = self.store or get_store()
        registry = self.registry or get_registry()
        ingester = self.ingester

        deleted = registry.delete(doc_id)
        store.delete_doc(doc_id)
        ingester.delete_cached(doc_id)
        return deleted

    # ------------------------------------------------------------------
    async def _caption_in_parallel(
        self, vlm, elements: list[DocElement], concurrency: int = 4
    ) -> None:
        sem = asyncio.Semaphore(concurrency)

        async def _one(el: DocElement) -> None:
            async with sem:
                if not el.image_path:
                    return
                try:
                    caption = await vlm.caption_image(el.image_path)
                    el.caption = caption
                    # Update the in-memory cache so subsequent loads see it.
                    self._update_cached_caption(el)
                except Exception as exc:  # noqa: BLE001
                    log.warning("caption failed for %s: %s", el.element_id, exc)

        await asyncio.gather(*[_one(e) for e in elements])

    def _update_cached_caption(self, el: DocElement) -> None:
        """Patch the ingester's JSON cache to persist the caption."""
        import json

        cache_file = self.ingester.pdf_cache_path / f"{el.doc_id}.json"
        if not cache_file.exists():
            return
        try:
            payload = json.loads(cache_file.read_text())
            for page in payload.get("pages", []):
                if page.get("page") != el.page:
                    continue
                for element in page.get("elements", []):
                    if element.get("element_index") == el.element_index:
                        element["caption"] = el.caption
                        break
            cache_file.write_text(json.dumps(payload, indent=2))
        except Exception as exc:  # noqa: BLE001
            log.warning("could not patch cache for %s: %s", el.element_id, exc)


# ----------------------------------------------------------------------
# Module-level convenience
# ----------------------------------------------------------------------
def get_indexer() -> Indexer:
    return Indexer()
