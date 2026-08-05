"""Pytest configuration: redirect the project's storage paths to a per-test
temp directory so tests don't pollute the real `data/db/knowledge.db`.

Every test that touches the storage layer gets an isolated SQLite DB at
`tmp_path / "test.db"` and a graph pickle at `tmp_path / "graph.pkl"`.
We achieve this by monkey-patching `get_settings()` (which is `lru_cache`d
in `knowledge_manager.config`) to return a Settings instance whose paths
point at the test temp dir.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from knowledge_manager import config
from knowledge_manager.storage import db as db_mod
from knowledge_manager.storage import graph_store, vector_store


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Redirect DB + graph paths to tmp_path for the duration of each test."""
    db_path = tmp_path / "test.db"
    graph_path = tmp_path / "graph.pkl"
    ingest_dir = tmp_path / "ingest"

    # Build a fake Settings-like object that the storage modules will accept.
    # We can't easily rebuild the real Settings (it has env-var binding), so
    # we monkey-patch the attributes on the cached instance.
    settings = config.get_settings()
    monkeypatch.setattr(settings, "db_path", db_path, raising=False)
    monkeypatch.setattr(settings, "graph_path", graph_path, raising=False)
    monkeypatch.setattr(settings, "ingest_dir", ingest_dir, raising=False)
    monkeypatch.setattr(settings, "openai_embed_dim", 4, raising=False)

    # Make sure the dirs exist.
    db_path.parent.mkdir(parents=True, exist_ok=True)
    ingest_dir.mkdir(parents=True, exist_ok=True)

    # Initialise the schema so every test starts with an empty DB.
    db_mod.init_db(db_path)
    yield tmp_path
