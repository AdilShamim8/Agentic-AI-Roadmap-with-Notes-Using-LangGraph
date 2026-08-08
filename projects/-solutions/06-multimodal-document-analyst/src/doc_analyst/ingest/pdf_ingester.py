"""PDF ingestion: layout-aware per-page extraction of text, images, and tables.

This module is the "Ingestion" stage of the project README's architecture:

    Ingestion: PDF parsed per-page, with layout-aware extraction
    separating text, images, and tables.

We use PyMuPDF (`fitz`) because it is fast, dependency-light, and exposes
both the text blocks and the rendered raster for each page (the latter is
used as a fallback for OCR/scanned pages — see stretch goal).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import fitz  # PyMuPDF
from PIL import Image

from ..config import settings
from ..schemas import DocElement, DocPage, DocSummary, ElementType
from ..utils.hashing import file_sha256, short_id
from ..utils.logging import get_logger
from .table_detector import detect_tables

log = get_logger(__name__)


class PDFIngester:
    """Extract per-page elements (text / image / table) from a PDF."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or settings.data_dir
        self.page_images_dir = settings.page_images_path
        self.page_images_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_cache_path = settings.pdf_cache_path
        self.pdf_cache_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def ingest(self, pdf_path: Path | str) -> tuple[DocSummary, list[DocPage]]:
        """Ingest a PDF.

        Returns the summary plus a list of all `DocPage` objects.
        Side effects:
          - Renders each page to PNG (used by the UI for cited thumbnails).
          - Extracts embedded images to PNG (so the VLM can caption them).
          - Writes a JSON dump to `pdf_cache_path/<doc_id>.json`.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        doc_id = short_id(file_sha256(pdf_path), prefix="doc-")
        log.info("Ingesting %s as %s", pdf_path.name, doc_id)

        doc = fitz.open(pdf_path)
        pages: list[DocPage] = []
        n_text = n_images = n_tables = 0

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_no = page_idx + 1
            elements: list[DocElement] = []

            # 1) Render page to PNG (always — used by UI + as OCR fallback).
            page_png = self._render_page(doc_id, page, page_no)

            # 2) Extract tables first so we can mask their bboxes when
            #    reading text blocks (avoids duplicate-text contamination).
            tables = detect_tables(page)
            table_bboxes = self._table_bboxes(page, tables)
            for t_idx, table in enumerate(tables):
                # Use the rectangle's bbox as the element's bbox.
                bbox = table_bboxes[t_idx] if t_idx < len(table_bboxes) else None
                el_id = f"{doc_id}::p{page_no}::e{len(elements)}"
                elements.append(
                    DocElement(
                        element_id=el_id,
                        doc_id=doc_id,
                        page=page_no,
                        element_index=len(elements),
                        type=ElementType.TABLE,
                        text=self._table_to_text(table),
                        table=table,
                        bbox=bbox,
                        meta={"rows": len(table), "cols": len(table[0]) if table else 0},
                    )
                )
                n_tables += 1

            # 3) Extract text blocks (skipping ones that overlap a table).
            for b in page.get_text("blocks"):
                x0, y0, x1, y1 = b[:4]
                text = b[4].strip()
                if not text:
                    continue
                if self._overlaps_any((x0, y0, x1, y1), table_bboxes, tol=4.0):
                    continue
                el_id = f"{doc_id}::p{page_no}::e{len(elements)}"
                elements.append(
                    DocElement(
                        element_id=el_id,
                        doc_id=doc_id,
                        page=page_no,
                        element_index=len(elements),
                        type=ElementType.TEXT,
                        text=text,
                        bbox=(x0, y0, x1, y1),
                    )
                )
                n_text += 1

            # 4) Extract embedded images.
            for img_index, info in enumerate(page.get_image_info(xrefs=True)):
                bbox = info.get("bbox")
                try:
                    xref = info.get("xref")
                    if xref is None:
                        continue
                    img_bytes = doc.extract_image(xref)["image"]
                except Exception as exc:  # noqa: BLE001
                    log.debug("skip image %s on page %s: %s", img_index, page_no, exc)
                    continue
                img_path = self.page_images_dir / f"{doc_id}_p{page_no}_img{img_index}.png"
                self._write_png(img_bytes, img_path)
                el_id = f"{doc_id}::p{page_no}::e{len(elements)}"
                elements.append(
                    DocElement(
                        element_id=el_id,
                        doc_id=doc_id,
                        page=page_no,
                        element_index=len(elements),
                        type=ElementType.IMAGE,
                        image_path=str(img_path),
                        bbox=tuple(bbox) if bbox else None,
                    )
                )
                n_images += 1

            pages.append(
                DocPage(
                    doc_id=doc_id,
                    page=page_no,
                    width=page.rect.width,
                    height=page.rect.height,
                    elements=elements,
                    page_image_path=page_png,
                )
            )

        doc.close()

        summary = DocSummary(
            doc_id=doc_id,
            source=str(pdf_path),
            n_pages=len(pages),
            n_elements=sum(len(p.elements) for p in pages),
            n_text=n_text,
            n_images=n_images,
            n_tables=n_tables,
            ingested_at=datetime.now(timezone.utc).isoformat(),
        )

        # Cache to disk so the API/UI can list documents without re-parsing.
        cache_file = self.pdf_cache_path / f"{doc_id}.json"
        cache_file.write_text(
            json.dumps(
                {
                    "summary": summary.model_dump(mode="json"),
                    "pages": [p.model_dump(mode="json") for p in pages],
                },
                indent=2,
            )
        )
        log.info(
            "Ingested %s: %d pages, %d elements (%d text / %d images / %d tables)",
            doc_id,
            summary.n_pages,
            summary.n_elements,
            n_text,
            n_images,
            n_tables,
        )
        return summary, pages

    # ------------------------------------------------------------------
    # Iterators / loaders
    # ------------------------------------------------------------------
    def iter_elements(self, pages: list[DocPage]) -> Iterator[DocElement]:
        for p in pages:
            yield from p.elements

    def load_cached(self, doc_id: str) -> tuple[DocSummary, list[DocPage]] | None:
        cache_file = self.pdf_cache_path / f"{doc_id}.json"
        if not cache_file.exists():
            return None
        payload = json.loads(cache_file.read_text())
        return (
            DocSummary(**payload["summary"]),
            [DocPage(**p) for p in payload["pages"]],
        )

    def list_cached(self) -> list[DocSummary]:
        out: list[DocSummary] = []
        for f in sorted(self.pdf_cache_path.glob("*.json")):
            try:
                payload = json.loads(f.read_text())
                out.append(DocSummary(**payload["summary"]))
            except Exception as exc:  # noqa: BLE001
                log.warning("could not read cache %s: %s", f, exc)
        return out

    def delete_cached(self, doc_id: str) -> bool:
        cache_file = self.pdf_cache_path / f"{doc_id}.json"
        existed = cache_file.exists()
        cache_file.unlink(missing_ok=True)
        # Also remove rendered PNGs.
        for png in self.page_images_dir.glob(f"{doc_id}_*"):
            png.unlink(missing_ok=True)
        return existed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _render_page(self, doc_id: str, page, page_no: int, zoom: float = 2.0) -> str:
        """Render the page to a PNG file and return its path."""
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out = self.page_images_dir / f"{doc_id}_p{page_no}.png"
        pix.save(str(out))
        return str(out)

    @staticmethod
    def _table_bboxes(page, tables: list[list[list[str]]]) -> list[tuple[float, float, float, float] | None]:
        """Best-effort: return the bbox of each detected table on the page.

        The line-grid detector already knows the x/y coords of each table;
        we recover the bbox by re-running the detector and reading the
        outermost coords. If the page was rasterised (no vector lines),
        fall back to None bboxes.
        """
        from .table_detector import _gather_lines, _find_grids  # local import

        lines = _gather_lines(page)
        grids = _find_grids(lines)
        out: list[tuple[float, float, float, float] | None] = []
        for i, table in enumerate(tables):
            if i < len(grids):
                x_coords, y_coords = grids[i]
                out.append((x_coords[0], y_coords[0], x_coords[-1], y_coords[-1]))
            else:
                out.append(None)
        # Pad if the detector found fewer grids than we have tables.
        while len(out) < len(tables):
            out.append(None)
        return out

    @staticmethod
    def _overlaps_any(
        bbox: tuple[float, float, float, float],
        others: list[tuple[float, float, float, float] | None],
        tol: float = 4.0,
    ) -> bool:
        x0, y0, x1, y1 = bbox
        for o in others:
            if o is None:
                continue
            ox0, oy0, ox1, oy1 = o
            # IoU-style: if our bbox is mostly inside `o`, skip.
            ix0 = max(x0, ox0)
            iy0 = max(y0, oy0)
            ix1 = min(x1, ox1)
            iy1 = min(y1, oy1)
            if ix0 < ix1 - tol and iy0 < iy1 - tol:
                our_area = max(1.0, (x1 - x0) * (y1 - y0))
                inter_area = (ix1 - ix0) * (iy1 - iy0)
                if inter_area / our_area > 0.5:
                    return True
        return False

    @staticmethod
    def _table_to_text(table: list[list[str]]) -> str:
        """Render a table as a Markdown-ish string for embedding."""
        if not table:
            return ""
        lines = []
        for row in table:
            lines.append(" | ".join(cell.replace("\n", " ").strip() for cell in row))
        return "\n".join(lines)

    @staticmethod
    def _write_png(img_bytes: bytes, dest: Path) -> None:
        # PyMuPDF returns PNG/JPEG/etc. depending on the source. Convert to
        # PNG via PIL for uniform handling.
        import io

        try:
            Image.open(io.BytesIO(img_bytes)).save(dest, format="PNG")
        except Exception:  # noqa: BLE001
            dest.write_bytes(img_bytes)
