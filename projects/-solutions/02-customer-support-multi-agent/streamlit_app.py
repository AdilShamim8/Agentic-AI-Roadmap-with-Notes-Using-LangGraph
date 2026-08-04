"""
Streamlit chat UI for the customer support multi-agent system.

Run with:  streamlit run streamlit_app.py

This talks to the LangGraph graph directly (in-process) rather than via the
FastAPI backend, so `streamlit run` is all you need - no separate server.
See app/api.py if you'd rather deploy the graph as a standalone REST API
and point a frontend at that instead.
"""
from __future__ import annotations

import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from app.graph import build_graph
from app.llm import is_mock_mode

st.set_page_config(page_title="Customer Support Multi-Agent", page_icon="🎧", layout="centered")


@st.cache_resource
def get_graph():
    return build_graph()


if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "history" not in st.session_state:
    st.session_state.history = []  # list of (role, content) for display only

graph = get_graph()

st.title("🎧 Customer Support Multi-Agent")
mode_label = "🧪 Mock mode (no API key - deterministic responses)" if is_mock_mode() else "🤖 Live LLM mode"
st.caption(mode_label)

with st.sidebar:
    st.subheader("Try these")
    st.code("Where is my order ORD-5001?", language=None)
    st.code("I was charged twice, CUST-1001", language=None)
    st.code("The app keeps crashing on login", language=None)
    st.code("This is unacceptable, I want a manager!", language=None)
    st.divider()
    st.caption(f"Thread ID: `{st.session_state.thread_id}`")
    if st.button("Start new conversation"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.history = []
        st.rerun()

for role, content in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)

user_input = st.chat_input("Type your message...")
if user_input:
    st.session_state.history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)
            reply = result["messages"][-1]
            reply_text = reply.content if isinstance(reply, AIMessage) else str(reply.content)
            st.markdown(reply_text)

            badges = [f"category: `{result.get('category')}`", f"sentiment: `{result.get('sentiment')}`"]
            if result.get("ticket_id"):
                badges.append(f"ticket: `{result['ticket_id']}`")
            st.caption(" · ".join(badges))

    st.session_state.history.append(("assistant", reply_text))
