"""Tests for the VectorStore."""
from __future__ import annotations

from pathlib import Path

from doc_analyst.ingest.pdf_ingester import PDFIngester
from doc_analyst.schemas import DocElement, ElementType
from doc_analyst.storage.vector_store import get_store


def test_index_and_search_text(samples_dir: Path) -> None:
    ingester = PDFIngester()
    summary, pages = ingester.ingest(samples_dir / "financial_report.pdf")
    store = get_store()
    elements = [e for p in pages for e in p.elements if e.type == ElementType.TEXT]
    store.index_elements(summary.doc_id, elements)

    # A query that should hit the financial text.
    hits = store.search_text("revenue 2024")
    assert hits, "no text hits"
    top_el, score = hits[0]
    assert score >= 0.0
    assert top_el.doc_id == summary.doc_id


def test_delete_doc(samples_dir: Path) -> None:
    ingester = PDFIngester()
    summary, pages = ingester.ingest(samples_dir / "financial_report.pdf")
    store = get_store()
    elements = [e for p in pages for e in p.elements]
    store.index_elements(summary.doc_id, elements)

    before = store.count_for_doc(summary.doc_id)
    assert before["text"] > 0

    store.delete_doc(summary.doc_id)
    after = store.count_for_doc(summary.doc_id)
    assert after["text"] == 0


def test_index_caption(samples_dir: Path) -> None:
    """A manually-built image element with a caption should be retrievable."""
    ingester = PDFIngester()
    summary, _ = ingester.ingest(samples_dir / "financial_report.pdf")

    fake = DocElement(
        element_id=f"{summary.doc_id}::p1::e99",
        doc_id=summary.doc_id,
        page=1,
        element_index=99,
        type=ElementType.IMAGE,
        caption="A bar chart showing revenue increasing from 42 in 2020 to 102 in 2024.",
        image_path=None,
    )
    store = get_store()
    store.update_caption(fake)
    hits = store.search_captions("revenue chart")
    assert hits
    assert any(h[0].element_id == fake.element_id for h in hits)
