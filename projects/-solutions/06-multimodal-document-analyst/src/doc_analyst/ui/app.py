"""Streamlit web UI for the Multimodal Document Analyst.

Run with: `streamlit run src/doc_analyst/ui/app.py` or `doc-analyst web`.

The UI lets you:
  - Drag-and-drop one or more PDFs to ingest.
  - Browse ingested documents and their pages.
  - Ask a question and get a structured answer with element-level
    citations. Each citation is clickable and shows the corresponding
    page thumbnail with the cited element highlighted.
"""
from __future__ import annotations

import asyncio
import io
import os
import sys
from pathlib import Path

import httpx
import streamlit as st

# When launched via `streamlit run src/doc_analyst/ui/app.py`, the package
# isn't on sys.path; fix that.
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from doc_analyst.config import settings  # noqa: E402

# ----------------------------------------------------------------------
# Configuration / session state
# ----------------------------------------------------------------------
API_BASE = os.environ.get("DOC_ANALYST_API", f"http://localhost:{settings.api_port}")


@st.cache_data(show_spinner=False)
def _http_get(path: str):
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=60.0)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _http_post(path: str, **kwargs):
    try:
        r = httpx.post(f"{API_BASE}{path}", timeout=300.0, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _http_delete(path: str):
    try:
        r = httpx.delete(f"{API_BASE}{path}", timeout=60.0)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


# ----------------------------------------------------------------------
# Page header
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Multimodal Document Analyst",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Multimodal Document Analyst")
st.caption(
    "Ingest PDFs (text + images + tables) and ask questions with element-level citations. "
    f"Backend: `{API_BASE}`"
)

# ----------------------------------------------------------------------
# Sidebar: backend status
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("Backend")
    health = _http_get("/health")
    if "error" in health:
        st.error(f"API not reachable: {health['error']}")
        st.caption(
            "Start it with:\n```\npython -m doc_analyst.cli serve\n# or\ndoc-analyst serve\n```"
        )
    else:
        st.success("API reachable")
        st.json(health)

    st.divider()
    st.header("Documents")
    docs = _http_get("/documents")
    if isinstance(docs, list):
        st.caption(f"{len(docs)} document(s) ingested")
        for d in docs:
            with st.expander(f"{d['doc_id']} — {Path(d['source']).name}"):
                st.json(d)
                if st.button("Delete", key=f"del_{d['doc_id']}"):
                    _http_delete(f"/documents/{d['doc_id']}")
                    st.rerun()
    if st.button("Clear all", type="secondary"):
        if st.checkbox("I'm sure", key="sure_clear"):
            _http_post("/clear")
            st.rerun()


# ----------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------
tab_ingest, tab_ask, tab_browse = st.tabs(["Ingest", "Ask", "Browse"])


# --- Ingest ---------------------------------------------------------
with tab_ingest:
    st.subheader("Ingest PDFs")
    files = st.file_uploader(
        "Drop PDFs here",
        type=["pdf"],
        accept_multiple_files=True,
    )
    if files and st.button("Ingest", type="primary"):
        with st.spinner("Ingesting… (VLM captioning may take a minute per image)"):
            files_data = [("files", (f.name, f.getvalue(), "application/pdf")) for f in files]
            res = _http_post("/ingest_many", files=files_data)
        if "error" in res:
            st.error(res["error"])
        else:
            for s in res.get("summaries", []):
                st.success(
                    f"Ingested **{s['doc_id']}** "
                    f"({s['n_pages']} pages, {s['n_elements']} elements)"
                )
            for f in res.get("failed", []):
                st.error(f"Failed {f['file']}: {f['error']}")


# --- Ask ------------------------------------------------------------
with tab_ask:
    st.subheader("Ask a question")
    q = st.text_input("Question", placeholder="e.g. What is the revenue trend in 2023?")
    restrict = st.multiselect(
        "Restrict to documents",
        options=[d["doc_id"] for d in docs] if isinstance(docs, list) else [],
    )
    if st.button("Ask", type="primary", disabled=not q) and q:
        with st.spinner("Retrieving and synthesizing…"):
            payload = {"question": q, "doc_ids": restrict or None}
            res = _http_post("/ask", json=payload)
        if "error" in res:
            st.error(res["error"])
        else:
            ans = res["answer"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Confidence", f"{ans['confidence']:.0%}")
            col2.metric("Latency (ms)", f"{ans['latency_ms']:.0f}")
            col3.metric("Citations", len(ans["citations"]))
            st.markdown("### Summary")
            st.write(ans["summary"])
            st.markdown("### Claims")
            for i, blk in enumerate(ans["blocks"], 1):
                st.markdown(f"**{i}.** {blk['claim']}")
                for c in blk["citations"]:
                    snippet = c.get("snippet", "")
                    if snippet:
                        snippet = snippet[:160] + ("..." if len(snippet) > 160 else "")
                    label = (
                        f"[{c['doc_id']} · p{c['page']} · e{c['element_index']}] "
                        f"({c['element_type']}/{c['source']})"
                    )
                    with st.expander(f"Citation: {label}"):
                        st.caption(snippet)
                        url = (
                            f"{API_BASE}/citations/{c['doc_id']}/page/{c['page']}/image"
                        )
                        st.image(url, caption=f"page {c['page']}")
                        if c["element_type"] == "image":
                            url_el = (
                                f"{API_BASE}/citations/{c['doc_id']}/page/{c['page']}"
                                f"/element/{c['element_index']}/image"
                            )
                            st.image(url_el, caption=f"element e{c['element_index']}")


# --- Browse ---------------------------------------------------------
with tab_browse:
    st.subheader("Browse documents")
    if isinstance(docs, list) and docs:
        choice = st.selectbox(
            "Document",
            options=[d["doc_id"] for d in docs],
            format_func=lambda did: f"{did} — {next((Path(d['source']).name for d in docs if d['doc_id']==did), '')}",
        )
        if choice:
            detail = _http_get(f"/documents/{choice}")
            if "error" not in detail:
                pages = detail.get("pages", [])
                page_no = st.selectbox(
                    "Page", options=[p["page"] for p in pages] or [1]
                )
                page_obj = next((p for p in pages if p["page"] == page_no), None)
                if page_obj:
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if page_obj.get("page_image_url"):
                            st.image(f"{API_BASE}{page_obj['page_image_url']}")
                    with c2:
                        for el in page_obj.get("elements", []):
                            etype = el["type"]
                            with st.expander(
                                f"e{el['element_index']} — {etype} "
                                f"(bbox={el.get('bbox')})"
                            ):
                                if etype == "text":
                                    st.write(el["text"])
                                elif etype == "table":
                                    tbl = el.get("table") or []
                                    if tbl:
                                        st.table(tbl)
                                elif etype == "image":
                                    if el.get("caption"):
                                        st.caption(el["caption"])
                                    if el.get("image_path"):
                                        url = (
                                            f"{API_BASE}/citations/{choice}/page/{page_no}"
                                            f"/element/{el['element_index']}/image"
                                        )
                                        st.image(url)
            else:
                st.error(detail["error"])
    else:
        st.info("No documents yet — ingest one in the Ingest tab.")
