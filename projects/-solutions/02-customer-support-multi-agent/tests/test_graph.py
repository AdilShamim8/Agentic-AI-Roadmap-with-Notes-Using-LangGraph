"""
End-to-end tests for the compiled LangGraph graph, run in mock mode (no LLM
API key needed - see app/llm.py). These require the packages in
requirements.txt (langgraph, langchain-core) to be installed; if they
aren't, the whole module is skipped rather than failing, so `pytest` still
passes on a bare `core/`-only install.
"""
from __future__ import annotations

import uuid

import pytest

langgraph = pytest.importorskip("langgraph", reason="langgraph not installed - see requirements.txt")

from langchain_core.messages import HumanMessage  # noqa: E402

from app.graph import build_graph  # noqa: E402
from core import tickets  # noqa: E402


@pytest.fixture()
def graph():
    return build_graph()


@pytest.fixture()
def config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def test_order_lookup_end_to_end(graph, config):
    result = graph.invoke(
        {"messages": [HumanMessage(content="Where is my order ORD-5001?")]}, config=config
    )
    assert result["category"] == "order"
    assert result["resolved"] is True
    assert "shipped" in result["messages"][-1].content.lower()


def test_billing_lookup_end_to_end(graph, config):
    result = graph.invoke(
        {"messages": [HumanMessage(content="What's my latest invoice? CUST-1001")]},
        config=config,
    )
    assert result["category"] == "billing"
    assert "INV-9001" in result["messages"][-1].content


def test_angry_customer_is_escalated(graph, config):
    tickets.reset_tickets()
    result = graph.invoke(
        {"messages": [HumanMessage(content="This is UNACCEPTABLE!! I want a refund NOW!!")]},
        config=config,
    )
    assert result["category"] == "escalation"
    assert result["resolved"] is False
    assert result["ticket_id"] is not None
    assert result["sentiment"] == "angry"


def test_unknown_order_id_escalates_via_reviewer(graph, config):
    result = graph.invoke(
        {"messages": [HumanMessage(content="Where is my order ORD-0000?")]}, config=config
    )
    # order not found -> specialist flags needs_escalation -> reviewer routes to escalation
    assert result["category"] == "escalation"
    assert result["ticket_id"] is not None


def test_multi_turn_conversation_keeps_customer_id(graph, config):
    graph.invoke({"messages": [HumanMessage(content="Hi, my customer ID is CUST-1002")]}, config=config)
    result = graph.invoke(
        {"messages": [HumanMessage(content="What's my most recent invoice?")]}, config=config
    )
    assert "INV-9002" in result["messages"][-1].content


def test_general_question_routes_to_general_agent(graph, config):
    result = graph.invoke(
        {"messages": [HumanMessage(content="What's your return policy?")]}, config=config
    )
    assert result["category"] == "general"
    assert result["resolved"] is True
