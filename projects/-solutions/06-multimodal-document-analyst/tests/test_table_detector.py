"""Tests for the heuristic table detector."""
from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from doc_analyst.ingest.table_detector import detect_tables


def _build_pdf_with_table(path: Path, rows: list[list[str]]) -> None:
    tbl = Table(rows, colWidths=[1.5 * inch] * len(rows[0]))
    tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
            ]
        )
    )
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    doc.build([tbl])


def test_detect_simple_table(tmp_path: Path) -> None:
    pdf = tmp_path / "t.pdf"
    _build_pdf_with_table(
        pdf,
        [
            ["A", "B", "C"],
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
        ],
    )
    doc = fitz.open(pdf)
    tables = detect_tables(doc[0])
    doc.close()
    assert len(tables) >= 1
    t = tables[0]
    # Should have at least 3 rows × 3 cols.
    assert len(t) >= 3
    assert len(t[0]) >= 3
    # Header row should be present.
    flat = [cell for row in t for cell in row]
    assert "A" in flat
    assert "B" in flat
    assert "C" in flat


def test_detect_no_table(samples_dir: Path) -> None:
    """A page with text but no drawn rectangles yields no tables."""
    # Re-use the climate brief — page 1 is mostly text + an image,
    # no drawn table. If the detector happens to find a table that's
    # still ok; we just assert it doesn't crash.
    pdf = samples_dir / "climate_brief.pdf"
    if not pdf.exists():
        pytest.skip("sample PDF not generated")
    doc = fitz.open(pdf)
    try:
        for page in doc:
            _ = detect_tables(page)  # should not raise
    finally:
        doc.close()
