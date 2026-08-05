"""Tests for the storage layer (SQLite + sqlite-vec + NetworkX).

The `isolated_storage` fixture in conftest.py redirects the DB to a per-test
temp path and runs `init_db` before each test, so we can just call the
storage functions directly.
"""
from __future__ import annotations

from knowledge_manager.storage import graph_store, vector_store
from knowledge_manager.storage.db import get_conn, init_db, wipe


def _insert_doc(conn, path: str, title: str, kind: str = "md") -> int:
    cur = conn.execute(
        "INSERT INTO documents(path, title, kind, content_hash) VALUES (?, ?, ?, ?)",
        (path, title, kind, "abc123"),
    )
    return cur.lastrowid


def _insert_chunk(conn, doc_id: int, position: int, text: str) -> int:
    cur = conn.execute(
        "INSERT INTO chunks(doc_id, position, text, char_start, char_end) VALUES (?, ?, ?, ?, ?)",
        (doc_id, position, text, 0, len(text)),
    )
    return cur.lastrowid


def test_init_creates_tables() -> None:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r["name"] for r in rows}
    assert {"documents", "chunks", "entities", "relationships", "vec_chunks"} <= names


def test_document_roundtrip() -> None:
    with get_conn() as conn:
        did = _insert_doc(conn, "/tmp/foo.md", "Foo")
        row = conn.execute("SELECT * FROM documents WHERE id=?", (did,)).fetchone()
    assert row["title"] == "Foo"
    assert row["kind"] == "md"


def test_vector_upsert_and_search() -> None:
    with get_conn() as conn:
        did = _insert_doc(conn, "/tmp/v.md", "V Doc")
        c1 = _insert_chunk(conn, did, 0, "alpha beta")
        c2 = _insert_chunk(conn, did, 1, "gamma delta")
    # Two 4-dim embeddings: c1 ~ [1,0,0,0], c2 ~ [0,1,0,0]
    vector_store.upsert_many(
        [
            (c1, [1.0, 0.0, 0.0, 0.0]),
            (c2, [0.0, 1.0, 0.0, 0.0]),
        ]
    )
    # Query near c1
    hits = vector_store.search([0.9, 0.1, 0.0, 0.0], top_k=2)
    assert len(hits) == 2
    assert hits[0].chunk_id == c1
    assert hits[0].score > hits[1].score


def test_vector_count() -> None:
    with get_conn() as conn:
        did = _insert_doc(conn, "/tmp/c.md", "C")
        c1 = _insert_chunk(conn, did, 0, "x")
    vector_store.upsert_many([(c1, [1.0, 0.0, 0.0, 0.0])])
    assert vector_store.count_vectors() == 1


def test_graph_add_entity_and_neighbor() -> None:
    with get_conn() as conn:
        did = _insert_doc(conn, "/tmp/e.md", "E")
        conn.execute(
            "INSERT INTO entities(name, kind, doc_id) VALUES (?, ?, ?)",
            ("Alan Turing", "person", did),
        )
        conn.execute(
            "INSERT INTO entities(name, kind, doc_id) VALUES (?, ?, ?)",
            ("Bletchley Park", "place", did),
        )
        conn.execute(
            "INSERT INTO relationships(src_entity, dst_entity, predicate, doc_id) VALUES (?, ?, ?, ?)",
            (1, 2, "worked_at", did),
        )

    g = graph_store.rebuild_graph()
    assert g.number_of_nodes() == 2
    assert g.number_of_edges() == 1
    assert g[1][2]["predicate"] == "worked_at"

    nodes, edges = graph_store.neighbors(1, depth=1)
    node_ids = {n.id for n in nodes}
    assert 1 in node_ids and 2 in node_ids
    assert any(e.predicate == "worked_at" for e in edges)


def test_wipe_clears_all() -> None:
    with get_conn() as conn:
        _insert_doc(conn, "/tmp/w.md", "W")
    wipe()
    with get_conn() as conn:
        (n,) = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
    assert n == 0
