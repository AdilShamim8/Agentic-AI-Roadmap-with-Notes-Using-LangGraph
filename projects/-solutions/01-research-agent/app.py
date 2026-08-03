"""Optional Streamlit UI for the Research Agent.

Run with:  streamlit run app.py
Requires:  pip install -r requirements-ui.txt
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from research_agent.config import load_settings
from research_agent.llm import build_llm
from research_agent.tools.web_search import build_search_tool_from_env

st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="centered")

settings = load_settings()

st.title("🔎 Research Agent")
st.caption("Plans sub-questions, searches the web (and your documents), and writes a cited report.")

with st.sidebar:
    st.header("Settings")
    provider = st.selectbox(
        "LLM provider",
        ["anthropic", "openai", "ollama"],
        index=["anthropic", "openai", "ollama"].index(settings.llm_provider)
        if settings.llm_provider in ("anthropic", "openai", "ollama")
        else 0,
    )
    max_results = st.slider("Search results per sub-question", 1, 10, settings.max_results_per_query)
    max_iterations = st.slider("Max refinement rounds", 1, 4, settings.max_iterations)
    uploaded_files = st.file_uploader(
        "Local documents to include (.txt, .md, .pdf)", accept_multiple_files=True
    )

topic = st.text_input("Research topic", placeholder="e.g. The impact of quantum computing on cryptography")
run_clicked = st.button("Run research", type="primary", disabled=not topic)

if run_clicked and topic:
    doc_paths = []
    if uploaded_files:
        tmp_dir = Path(tempfile.mkdtemp())
        for f in uploaded_files:
            path = tmp_dir / f.name
            path.write_bytes(f.getbuffer())
            doc_paths.append(str(path))

    try:
        llm = build_llm(provider)
        search_tool = build_search_tool_from_env()
    except (ImportError, ValueError) as exc:
        st.error(f"Setup error: {exc}")
        st.stop()

    progress = st.empty()
    log_box = st.empty()
    log_lines: list[str] = []

    def on_step(name: str, state) -> None:
        progress.info(f"Running step: **{name}**")
        if state.get("log"):
            log_lines.append(state["log"][-1])
            log_box.code("\n".join(log_lines), language="text")

    with st.spinner("Researching..."):
        try:
            from research_agent.graph import build_graph
            from research_agent.state import new_state

            app_graph = build_graph(llm, search_tool)
            state = new_state(
                topic=topic,
                local_document_paths=doc_paths,
                max_results_per_query=max_results,
                max_iterations=max_iterations,
            )
            final_state = state
            for event in app_graph.stream(state):
                for node_name, node_state in event.items():
                    final_state = node_state
                    on_step(node_name, final_state)
        except ImportError:
            from research_agent.engine import run_research

            final_state = run_research(
                topic=topic,
                llm=llm,
                search_tool=search_tool,
                local_document_paths=doc_paths,
                max_results_per_query=max_results,
                max_iterations=max_iterations,
                on_step=on_step,
            )

    progress.success("Done.")
    st.markdown("---")
    st.markdown(final_state["report"])
    st.download_button(
        "Download report as Markdown",
        data=final_state["report"],
        file_name="research_report.md",
        mime="text/markdown",
    )
