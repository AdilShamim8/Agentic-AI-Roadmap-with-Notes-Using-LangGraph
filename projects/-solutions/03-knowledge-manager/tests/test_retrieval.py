"""Tests for the retrieval + agent glue (without calling OpenAI)."""
from __future__ import annotations

from knowledge_manager.storage import vector_store
from knowledge_manager.storage.db import get_conn


def _seed_db():
    """Build a small DB with 3 docs and 3 chunks; deterministic embeddings."""
    docs = [
        ("/tmp/d1.md", "Turing", "md"),
        ("/tmp/d2.md", "Enigma", "md"),
        ("/tmp/d3.md", "Bletchley", "md"),
    ]
    chunks = [
        (1, 0, "Alan Turing worked at Bletchley Park."),
        (2, 0, "The Enigma machine was cracked at Bletchley."),
        (3, 0, "Bletchley Park is in Milton Keynes."),
    ]
    embeddings = [
        [1.0, 0.0, 0.0, 0.0],  # doc 1 -> "turing" axis
        [0.0, 1.0, 0.0, 0.0],  # doc 2 -> "enigma" axis
        [0.0, 0.0, 1.0, 0.0],  # doc 3 -> "bletchley" axis
    ]
    with get_conn() as conn:
        for path, title, kind in docs:
            conn.execute(
                "INSERT INTO documents(path, title, kind, content_hash) VALUES (?, ?, ?, ?)",
                (path, title, kind, "h"),
            )
        chunk_ids = []
        for did, pos, text in chunks:
            cur = conn.execute(
                "INSERT INTO chunks(doc_id, position, text, char_start, char_end) VALUES (?, ?, ?, ?, ?)",
                (did, pos, text, 0, len(text)),
            )
            chunk_ids.append(cur.lastrowid)
    vector_store.upsert_many(list(zip(chunk_ids, embeddings)))
    return chunk_ids


def test_vector_search_returns_relevant_chunk() -> None:
    chunk_ids = _seed_db()
    # Query close to doc 1
    hits = vector_store.search([0.95, 0.05, 0.0, 0.0], top_k=3)
    assert len(hits) == 3
    assert hits[0].chunk_id == chunk_ids[0]
    assert "Turing" in hits[0].text


def test_agent_state_typechecks() -> None:
    """Smoke test: the AgentState TypedDict exists and has expected keys."""
    from knowledge_manager.agent.graph import AgentState

    keys = set(AgentState.__annotations__.keys())
    assert "question" in keys
    assert "sources" in keys
    assert "answer" in keys
    assert "provenance" in keys


def test_zettelkasten_persists_links() -> None:
    """Zettelkasten linker should write rows to note_links."""
    from knowledge_manager.zettelkasten import linker as zlink

    # Two docs, each with one chunk + one shared entity.
    # Insert docs + chunks first, CLOSE the connection, then upsert vectors
    # (vector_store opens its own connection — SQLite locks if both are open).
    with get_conn() as conn:
        for i, (path, title) in enumerate([("/tmp/a.md", "A"), ("/tmp/b.md", "B")], start=1):
            conn.execute(
                "INSERT INTO documents(path, title, kind, content_hash) VALUES (?, ?, ?, ?)",
                (path, title, "md", f"h{i}"),
            )
            conn.execute(
                "INSERT INTO chunks(doc_id, position, text, char_start, char_end) VALUES (?, ?, ?, ?, ?)",
                (i, 0, f"doc {i} text", 0, 9),
            )

    # Now insert entities + mentions in a fresh connection.
    with get_conn() as conn:
        for i in range(1, 3):
            conn.execute(
                "INSERT INTO entities(name, kind, doc_id) VALUES (?, ?, ?)",
                ("SharedConcept", "concept", i),
            )
            conn.execute(
                "INSERT INTO entity_mentions(chunk_id, entity_id) VALUES (?, ?)",
                (i, i),
            )

    # Upsert embeddings (vector_store manages its own connection).
    vecs = {1: [1.0, 0.0, 0.0, 0.0], 2: [0.95, 0.05, 0.0, 0.0]}
    vector_store.upsert_many(list(vecs.items()))

    # Stash embedding blobs into chunks for the linker's centroid computation.
    with get_conn() as conn:
        for cid, vec in vecs.items():
            conn.execute(
                "UPDATE chunks SET embedding = ? WHERE id = ?",
                (vector_store._pack_embedding(vec), cid),
            )

    zlink.ensure_notes()
    links = zlink.suggest_links(top_k=5, min_score=0.05)
    assert len(links) >= 2  # bidirectional
    pairs = {(l.src_note, l.dst_note) for l in links}
    assert (1, 2) in pairs or (2, 1) in pairs
