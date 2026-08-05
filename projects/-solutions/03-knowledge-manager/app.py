"""Streamlit UI for the Personal Knowledge Manager.

Run with:  streamlit run app.py

Tabs:
- Chat      : ask questions, see answer + provenance + cited sources
- Ingest    : drag-drop files/folders, see per-file ingest log
- Graph     : explore the entity graph (streamlit-agraph visualisation)
- Notes     : Zettelkasten-style suggested links between docs
- Status    : DB stats + LangSmith/OpenAI config sanity check
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from knowledge_manager.agent.graph import ask
from knowledge_manager.config import get_settings
from knowledge_manager.ingestion.pipeline import ingest_directory
from knowledge_manager.storage import graph_store
from knowledge_manager.storage.db import get_conn, init_db
from knowledge_manager.zettelkasten import linker as zlink

st.set_page_config(
    page_title="Knowledge Manager",
    page_icon="📚",
    layout="wide",
)


# --------------------------- session helpers --------------------------------


def _init() -> None:
    init_db()
    if "chat" not in st.session_state:
        st.session_state.chat = []  # list of {role, content, provenance?, sources?}


# --------------------------- sidebar ----------------------------------------


_init()
st.sidebar.title("Knowledge Manager")
st.sidebar.caption("RAG + graph memory + multi-modal ingestion")
pages = ["Chat", "Ingest", "Graph", "Notes (Zettelkasten)", "Status"]
page = st.sidebar.radio("Navigate", pages)
st.sidebar.divider()
st.sidebar.markdown(
    f"- **chat model**: `{get_settings().openai_chat_model}`\n"
    f"- **embed model**: `{get_settings().openai_embed_model}`\n"
    f"- **db**: `{get_settings().db_path}`"
)


# --------------------------- Chat page --------------------------------------


def _render_chat():
    st.header("💬 Ask your knowledge base")
    for turn in st.session_state.chat:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn.get("provenance"):
                with st.expander(f"Provenance ({len(turn['provenance'])} citations)"):
                    for p in turn["provenance"]:
                        st.markdown(
                            f"**[{p['citation']}]** {p['title']} "
                            f"`{p['path']}`  · chunk #{p['chunk_id']}  "
                            f"· score `{p['score']:.3f}`"
                        )
            if turn.get("sources"):
                with st.expander(f"Retrieved sources ({len(turn['sources'])})"):
                    for i, s in enumerate(turn["sources"], 1):
                        cited = any(p["citation"] == i for p in turn.get("provenance", []))
                        mark = "✅" if cited else "·"
                        st.markdown(
                            f"{mark} **[{i}]** {s['title']} "
                            f"(score `{s['fused_score']:.3f}`)"
                        )
                        st.caption(s["text"][:400].replace("\n", " "))

    q = st.chat_input("Ask a question...")
    if not q:
        return
    st.session_state.chat.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        with st.spinner("Retrieving + synthesising..."):
            try:
                resp = ask(q)
            except Exception as e:
                st.error(f"Agent error: {e}")
                return
        st.markdown(resp.answer)
        st.caption(f"elapsed: {resp.elapsed_s:.2f}s · sources: {len(resp.sources)}")
        if resp.provenance:
            with st.expander(f"Provenance ({len(resp.provenance)} citations)"):
                for p in resp.provenance:
                    st.markdown(
                        f"**[{p['citation']}]** {p['title']} "
                        f"`{p['path']}`  · chunk #{p['chunk_id']}  "
                        f"· score `{p['score']:.3f}`"
                    )
        if resp.sources:
            with st.expander(f"Retrieved sources ({len(resp.sources)})"):
                for i, s in enumerate(resp.sources, 1):
                    cited = any(p["citation"] == i for p in resp.provenance)
                    mark = "✅" if cited else "·"
                    st.markdown(
                        f"{mark} **[{i}]** {s['title']} "
                        f"(fused `{s['fused_score']:.3f}` · vec `{s['vector_score']:.3f}` · "
                        f"graph `{s['graph_score']:.3f}`)"
                    )
                    if s.get("matched_entities"):
                        st.caption("entities: " + ", ".join(s["matched_entities"]))
                    st.caption(s["text"][:400].replace("\n", " "))
        st.session_state.chat.append(
            {
                "role": "assistant",
                "content": resp.answer,
                "provenance": resp.provenance,
                "sources": resp.sources,
            }
        )


# --------------------------- Ingest page ------------------------------------


def _render_ingest():
    st.header("📥 Ingest documents")
    st.caption("Drop files here (PDF, HTML, Markdown, TXT). They'll be loaded, chunked, embedded, and entity-extracted.")
    uploaded = st.file_uploader(
        "Choose files",
        type=["md", "markdown", "html", "htm", "pdf", "txt"],
        accept_multiple_files=True,
    )
    if uploaded and st.button("Ingest uploaded files", type="primary"):
        ingest_dir = get_settings().ingest_dir
        ingest_dir.mkdir(parents=True, exist_ok=True)
        for f in uploaded:
            (ingest_dir / f.name).write_bytes(f.getbuffer())
        with st.spinner("Ingesting..."):
            report = ingest_directory(ingest_dir, extract_entities=True)
        st.success(
            f"Ingested {report.n_files} files ({report.n_chunks} chunks, "
            f"{report.n_entities} entities, {report.n_relationships} relationships) "
            f"in {report.elapsed_s:.1f}s"
        )
        st.dataframe(
            [
                {
                    "path": e.get("path"),
                    "status": e.get("status"),
                    "chunks": e.get("n_chunks"),
                    "entities": e.get("n_entities"),
                    "rels": e.get("n_relationships"),
                }
                for e in report.per_file
            ],
            use_container_width=True,
        )

    st.divider()
    st.subheader("Or ingest a directory on disk")
    folder = st.text_input("Folder path", value=str(get_settings().ingest_dir))
    if st.button("Ingest folder"):
        with st.spinner("Ingesting..."):
            report = ingest_directory(folder, extract_entities=True)
        st.success(
            f"Done: {report.n_files} files, {report.n_chunks} chunks, "
            f"{report.n_entities} entities in {report.elapsed_s:.1f}s"
        )
        st.dataframe(
            [
                {
                    "path": e.get("path"),
                    "status": e.get("status"),
                    "chunks": e.get("n_chunks"),
                    "entities": e.get("n_entities"),
                }
                for e in report.per_file
            ],
            use_container_width=True,
        )


# --------------------------- Graph page -------------------------------------


def _render_graph():
    st.header("🕸️ Entity graph")
    g = graph_store.load_graph()
    st.caption(f"{g.number_of_nodes()} nodes · {g.number_of_edges()} edges")

    try:
        from streamlit_agraph import agraph, Edge, Node, Config
    except ImportError:
        st.warning("streamlit-agraph not installed; showing tables instead.")
        nodes = graph_store.all_entities(limit=200)
        st.dataframe([{"id": n.id, "name": n.name, "kind": n.kind} for n in nodes])
        return

    # Take top-N by degree to keep the visualisation readable.
    ranked = sorted(g.nodes(), key=lambda n: g.degree(n), reverse=True)[:60]
    keep = set(ranked)
    nodes = [
        Node(
            id=str(n),
            label=g.nodes[n].get("name", str(n)),
            size=10 + min(30, g.degree(n) * 2),
            title=g.nodes[n].get("kind", ""),
        )
        for n in keep
    ]
    edges = [
        Edge(
            source=str(u),
            target=str(v),
            label=g[u][v].get("predicate", ""),
            type="CURVE_SMOOTH",
        )
        for u, v in g.edges()
        if u in keep and v in keep
    ]
    cfg = Config(
        width=900,
        height=650,
        directed=True,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=True,
    )
    agraph(nodes=nodes, edges=edges, config=cfg)

    st.subheader("Entities by kind")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT kind, COUNT(*) AS n FROM entities GROUP BY kind ORDER BY n DESC"
        ).fetchall()
    cols = st.columns(len(rows) or 1)
    for col, r in zip(cols, rows):
        col.metric(label=r["kind"].title(), value=r["n"])


# --------------------------- Zettelkasten page ------------------------------


def _render_notes():
    st.header("📝 Zettelkasten — suggested note links")
    st.caption(
        "Each document is a note. Suggestions combine shared entities "
        "(Jaccard) and document embedding similarity (cosine)."
    )
    if st.button("Recompute suggested links", type="primary"):
        with st.spinner("Scanning notes..."):
            zlink.ensure_notes()
            links = zlink.suggest_links(top_k=5, min_score=0.10)
        st.success(f"Persisted {len(links)} suggested links.")

    # Always show whatever's in the DB.
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT n.id, n.title, d.path FROM notes n JOIN documents d ON d.id = n.doc_id "
            "ORDER BY n.id"
        ).fetchall()
        if not rows:
            st.info("No notes yet. Ingest some documents first.")
            return
        selected = st.selectbox(
            "Note",
            rows,
            format_func=lambda r: f"#{r['id']} · {r['title']}",
        )
        if selected:
            links = zlink.list_links(selected["id"])
            st.subheader("Suggested links")
            if not links:
                st.info("No suggestions yet — click 'Recompute' above.")
            else:
                tbl = []
                for l in links:
                    other = l.dst_note if l.src_note == selected["id"] else l.src_note
                    title_row = next((r for r in rows if r["id"] == other), None)
                    tbl.append(
                        {
                            "other_note": f"#{other} · {title_row['title'] if title_row else '?'}",
                            "score": round(l.score, 3),
                            "reason": l.reason,
                        }
                    )
                st.dataframe(tbl, use_container_width=True)


# --------------------------- Status page ------------------------------------


def _render_status():
    st.header("⚙️ Status")
    s = get_settings()
    cols = st.columns(4)
    with get_conn() as conn:
        (n_docs,) = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        (n_chunks,) = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
        (n_ent,) = conn.execute("SELECT COUNT(*) FROM entities").fetchone()
        (n_rel,) = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()
    cols[0].metric("documents", n_docs)
    cols[1].metric("chunks", n_chunks)
    cols[2].metric("entities", n_ent)
    cols[3].metric("relationships", n_rel)

    st.subheader("Config")
    st.json(
        {
            "openai_chat_model": s.openai_chat_model,
            "openai_embed_model": s.openai_embed_model,
            "openai_embed_dim": s.openai_embed_dim,
            "db_path": str(s.db_path),
            "graph_path": str(s.graph_path),
            "ingest_dir": str(s.ingest_dir),
            "langsmith_tracing": s.langsmith_tracing,
            "vector_top_k": s.vector_top_k,
            "graph_depth": s.graph_depth,
            "chunk_size": s.chunk_size,
            "chunk_overlap": s.chunk_overlap,
        }
    )

    st.subheader("Sanity check")
    ok = True
    if not s.openai_api_key or s.openai_api_key.startswith("sk-replace-me"):
        st.error("OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in.")
        ok = False
    else:
        st.success("OPENAI_API_KEY looks configured.")
    if s.langsmith_tracing and not s.langsmith_api_key:
        st.warning("LANGSMITH_TRACING=true but LANGSMITH_API_KEY is empty.")
    if n_chunks == 0:
        st.warning("No chunks indexed yet — visit the Ingest tab.")
    if ok and n_chunks > 0:
        st.success("Ready: try the Chat tab.")


# --------------------------- router -----------------------------------------

if page == "Chat":
    _render_chat()
elif page == "Ingest":
    _render_ingest()
elif page == "Graph":
    _render_graph()
elif page == "Notes (Zettelkasten)":
    _render_notes()
else:
    _render_status()
