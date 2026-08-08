"""Smoke-test the PDF ingester."""
from __future__ import annotations

from pathlib import Path

import pytest

from doc_analyst.ingest.pdf_ingester import PDFIngester
from doc_analyst.schemas import ElementType


def test_ingest_financial_report(samples_dir: Path) -> None:
    pdf = samples_dir / "financial_report.pdf"
    if not pdf.exists():
        pytest.skip("sample PDF not generated")

    ingester = PDFIngester()
    summary, pages = ingester.ingest(pdf)

    assert summary.doc_id.startswith("doc-")
    assert summary.n_pages >= 2  # at least 2 pages (we add a PageBreak)
    assert summary.n_text > 0
    assert summary.n_images > 0  # the bar chart
    assert summary.n_tables > 0  # the segment-breakdown table

    # Cache round-trip.
    cached = ingester.load_cached(summary.doc_id)
    assert cached is not None
    c_summary, c_pages = cached
    assert c_summary.doc_id == summary.doc_id
    assert c_summary.n_elements == summary.n_elements
    assert len(c_pages) == len(pages)

    # Element ids are unique within a doc.
    all_ids = [e.element_id for p in pages for e in p.elements]
    assert len(all_ids) == len(set(all_ids))

    # Every page has a PNG.
    for p in pages:
        assert Path(p.page_image_path).exists()


def test_ingest_idempotent(samples_dir: Path) -> None:
    """Re-ingesting the same PDF yields the same doc_id."""
    ingester = PDFIngester()
    s1, _ = ingester.ingest(samples_dir / "financial_report.pdf")
    s2, _ = ingester.ingest(samples_dir / "financial_report.pdf")
    assert s1.doc_id == s2.doc_id


def test_ingest_table_extraction(samples_dir: Path) -> None:
    """Tables should be detected and their cells readable."""
    ingester = PDFIngester()
    summary, pages = ingester.ingest(samples_dir / "financial_report.pdf")
    tables = [
        e for p in pages for e in p.elements if e.type == ElementType.TABLE
    ]
    assert tables, "no tables detected"
    # The financial report has a "Segment breakdown" table; first row
    # should be the header.
    t = tables[0]
    assert t.table is not None
    assert "Segment" in t.table[0][0]
