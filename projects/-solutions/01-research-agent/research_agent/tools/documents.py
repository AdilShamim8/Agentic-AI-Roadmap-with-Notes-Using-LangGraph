"""Load local documents (.txt, .md, .pdf) so the agent can research from
files the user already has, not just the live web — this is the "and
documents" half of the project brief.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from ..state import SearchResult


def load_local_documents(paths: List[str], max_chars_per_doc: int = 8000) -> List[SearchResult]:
    """Read each path and wrap its text as a SearchResult so it flows
    through the exact same synthesis pipeline as web results."""

    results: List[SearchResult] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if not path.exists():
            continue

        suffix = path.suffix.lower()
        try:
            if suffix == ".pdf":
                text = _read_pdf(path)
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        text = text.strip()
        if not text:
            continue

        results.append(
            SearchResult(
                title=path.name,
                url=f"file://{path.resolve()}",
                snippet=text[:280].replace("\n", " "),
                content=text[:max_chars_per_doc],
                source_type="local_document",
            )
        )
    return results


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)
