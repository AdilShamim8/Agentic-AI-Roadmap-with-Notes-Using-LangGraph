"""SQLite-backed metadata store for ingested documents.

ChromaDB holds the per-element vectors, but we also want a small,
queryable registry of "what documents have we ingested?" — that goes in
SQLite. Keeping it separate avoids coupling the doc registry to the
vector store.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from ..config import settings
from ..schemas import DocSummary


class DocRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.sqlite_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id        TEXT PRIMARY KEY,
                    source        TEXT NOT NULL,
                    n_pages       INTEGER NOT NULL,
                    n_elements    INTEGER NOT NULL,
                    n_text        INTEGER NOT NULL,
                    n_images      INTEGER NOT NULL,
                    n_tables      INTEGER NOT NULL,
                    ingested_at   TEXT NOT NULL
                )
                """
            )

    # ------------------------------------------------------------------
    def upsert(self, summary: DocSummary) -> None:
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO documents(doc_id, source, n_pages, n_elements,
                                      n_text, n_images, n_tables, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    source=excluded.source,
                    n_pages=excluded.n_pages,
                    n_elements=excluded.n_elements,
                    n_text=excluded.n_text,
                    n_images=excluded.n_images,
                    n_tables=excluded.n_tables,
                    ingested_at=excluded.ingested_at
                """,
                (
                    summary.doc_id,
                    summary.source,
                    summary.n_pages,
                    summary.n_elements,
                    summary.n_text,
                    summary.n_images,
                    summary.n_tables,
                    summary.ingested_at,
                ),
            )

    def list(self) -> list[DocSummary]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM documents ORDER BY ingested_at DESC").fetchall()
        return [DocSummary(**dict(r)) for r in rows]

    def get(self, doc_id: str) -> DocSummary | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
            ).fetchone()
        return DocSummary(**dict(row)) if row else None

    def delete(self, doc_id: str) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            return cur.rowcount > 0


# ----------------------------------------------------------------------
_registry: DocRegistry | None = None


def get_registry() -> DocRegistry:
    global _registry
    if _registry is None:
        _registry = DocRegistry()
    return _registry


def reset_registry() -> None:
    global _registry
    _registry = None
