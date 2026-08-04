"""
Node functions that make up the LangGraph graph:

    intake -> supervisor -> {billing_agent | technical_agent | order_agent |
                              general_agent | escalation} -> reviewer -> (escalation | END)

Each specialist node uses a real LLM + tool-calling ReAct agent when one is
configured (see app/llm.py), and falls back to a deterministic, template-
based response built directly from `core/` functions when running in mock
mode (no API key). Either way the *tools* being called are the exact same
`core/` functions, so behavior is consistent between modes - only the
natural-language phrasing differs. This also means the graph is fully
testable offline, with no API key and no network access.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from app.llm import get_llm
from app.state import AgentState
from app.tools import BILLING_TOOLS, TECHNICAL_TOOLS, ORDER_TOOLS, GENERAL_TOOLS
from core import billing, orders, tickets
from core.intent import classify_intent, extract_ids
from core.knowledge_base import search_kb
from core.sentiment import detect_sentiment, wants_human


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _last_user_text(state: AgentState) -> str:
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            return m.content
    return ""


def _run_react_agent(tools, system_prompt: str, state: AgentState) -> AIMessage:
    from langgraph.prebuilt import create_react_agent

    llm = get_llm()
    agent = create_react_agent(llm, tools, prompt=system_prompt)
    result = agent.invoke({"messages": state["messages"]})
    final = result["messages"][-1]
    if isinstance(final, AIMessage):
        return final
    return AIMessage(content=str(final.content))


# ---------------------------------------------------------------------------
# intake & routing
# ---------------------------------------------------------------------------

def intake(state: AgentState) -> dict:
    """First node: read sentiment/urgency and pull out any IDs mentioned, before routing."""
    text = _last_user_text(state)
    sentiment = detect_sentiment(text)
    ids = extract_ids(text)

    update: dict = {"sentiment": sentiment}
    if ids["customer_id"] and not state.get("customer_id"):
        update["customer_id"] = ids["customer_id"]
    if sentiment == "angry" or wants_human(text):
        update["needs_escalation"] = True
    return update


def supervisor(state: AgentState) -> dict:
    """Route to a specialist based on a fast keyword classifier (see core/intent.py)."""
    if state.get("needs_escalation"):
        return {"category": "escalation"}
    text = _last_user_text(state)
    category = classify_intent(text)
    return {"category": category}


def route_after_supervisor(state: AgentState) -> str:
    return state["category"]


# ---------------------------------------------------------------------------
# specialist agents
# ---------------------------------------------------------------------------

BILLING_PROMPT = (
    "You are a billing support specialist for a SaaS product. Be concise, "
    "empathetic, and precise about amounts and dates. Use the lookup_invoice "
    "tool before discussing any invoice, and issue_refund only after you "
    "have confirmed the invoice ID. Use search_knowledge_base for policy "
    "questions (e.g. refund timelines, failed payments)."
)

TECHNICAL_PROMPT = (
    "You are a technical support specialist for a SaaS product. Diagnose "
    "the issue using search_knowledge_base, and if it needs engineering "
    "follow-up (e.g. persistent bugs, lost 2FA device), use "
    "create_support_ticket with priority 'high' and explain that a human "
    "will follow up."
)

ORDER_PROMPT = (
    "You are an order-tracking support specialist for an e-commerce "
    "product. Use get_order_status to answer questions about a specific "
    "order, and search_knowledge_base for general shipping policy "
    "questions (e.g. what happens with delayed packages)."
)

GENERAL_PROMPT = (
    "You are a friendly customer support specialist. Answer general "
    "questions using search_knowledge_base. If the question is really "
    "about billing, a specific order, or a technical problem, say so "
    "briefly so the customer can rephrase with those details."
)


def billing_agent(state: AgentState) -> dict:
    if get_llm() is not None:
        reply = _run_react_agent(BILLING_TOOLS, BILLING_PROMPT, state)
        return {"messages": [reply], "category": "billing"}
    return _mock_billing(state)


def technical_agent(state: AgentState) -> dict:
    if get_llm() is not None:
        reply = _run_react_agent(TECHNICAL_TOOLS, TECHNICAL_PROMPT, state)
        return {"messages": [reply], "category": "technical"}
    return _mock_technical(state)


def order_agent(state: AgentState) -> dict:
    if get_llm() is not None:
        reply = _run_react_agent(ORDER_TOOLS, ORDER_PROMPT, state)
        return {"messages": [reply], "category": "order"}
    return _mock_order(state)


def general_agent(state: AgentState) -> dict:
    if get_llm() is not None:
        reply = _run_react_agent(GENERAL_TOOLS, GENERAL_PROMPT, state)
        return {"messages": [reply], "category": "general"}
    return _mock_general(state)


# ---------------------------------------------------------------------------
# mock-mode (no API key) fallbacks - deterministic, built on core/ directly
# ---------------------------------------------------------------------------

def _mock_billing(state: AgentState) -> dict:
    text = _last_user_text(state)
    ids = extract_ids(text)
    customer_id = ids["customer_id"] or state.get("customer_id")

    if ids["invoice_id"] and ("refund" in text.lower() or "chargeback" in text.lower()):
        result = billing.process_refund(ids["invoice_id"], reason=text[:200])
        return {"messages": [AIMessage(content=result.message)], "category": "billing",
                "needs_escalation": not result.ok}

    if customer_id:
        result = billing.get_latest_invoice(customer_id)
        if result.ok:
            return {"messages": [AIMessage(content=result.message)], "category": "billing"}
        return {"messages": [AIMessage(content=result.message)], "category": "billing",
                "needs_escalation": True}

    hits = search_kb(text, k=1)
    if hits:
        msg = (f"Here's what I found on billing: {hits[0].content.strip()}\n\n"
               f"If you can share your customer ID (e.g. CUST-1001), I can look at your account directly.")
        return {"messages": [AIMessage(content=msg)], "category": "billing"}

    return {
        "messages": [AIMessage(content=(
            "I can help with billing - could you share your customer ID (e.g. CUST-1001) "
            "or the invoice number so I can look into it?"
        ))],
        "category": "billing",
    }


def _mock_technical(state: AgentState) -> dict:
    text = _last_user_text(state)
    hits = search_kb(text, k=1)
    if hits:
        msg = f"{hits[0].content.strip()}\n\nDid that resolve it, or should I open a ticket for engineering?"
        return {"messages": [AIMessage(content=msg)], "category": "technical"}

    customer_id = state.get("customer_id")
    t = tickets.create_ticket(customer_id, "technical", summary=text[:200], priority="high")
    msg = (f"I wasn't able to resolve this from our help articles, so I've opened ticket "
           f"{t.ticket_id} for our engineering team to take a closer look. They'll follow up soon.")
    return {"messages": [AIMessage(content=msg)], "category": "technical", "ticket_id": t.ticket_id}


def _mock_order(state: AgentState) -> dict:
    text = _last_user_text(state)
    ids = extract_ids(text)

    if ids["order_id"]:
        result = orders.get_order_status(ids["order_id"])
        return {"messages": [AIMessage(content=result.message)], "category": "order",
                "needs_escalation": not result.ok}

    customer_id = ids["customer_id"] or state.get("customer_id")
    if customer_id:
        rows = orders.list_orders_for_customer(customer_id)
        if rows:
            listing = "; ".join(f"{r['order_id']} ({r['status']})" for r in rows)
            msg = f"Here are the orders on your account: {listing}. Which one would you like details on?"
            return {"messages": [AIMessage(content=msg)], "category": "order"}

    return {
        "messages": [AIMessage(content=(
            "I can help track your order - could you share the order ID (e.g. ORD-5001)?"
        ))],
        "category": "order",
    }


def _mock_general(state: AgentState) -> dict:
    text = _last_user_text(state)
    hits = search_kb(text, k=1)
    if hits:
        msg = hits[0].content.strip()
        return {"messages": [AIMessage(content=msg)], "category": "general"}
    msg = ("I'm not totally sure about that one. Could you tell me a bit more, or let me know if this "
           "is about billing, an order, or a technical issue so I can route you to the right place?")
    return {"messages": [AIMessage(content=msg)], "category": "general"}


# ---------------------------------------------------------------------------
# escalation & review
# ---------------------------------------------------------------------------

def escalation(state: AgentState) -> dict:
    """Create a human-handoff ticket. Reached directly (angry/explicit request) or via reviewer."""
    text = _last_user_text(state)
    customer_id = state.get("customer_id")
    category = state.get("category") or "general"
    priority = "urgent" if state.get("sentiment") == "angry" else "high"

    t = tickets.create_ticket(customer_id, category, summary=text[:200], priority=priority)
    msg = (
        "I'm sorry for the trouble - I'm connecting you with a member of our team who can help "
        f"directly. I've opened ticket {t.ticket_id} (priority: {priority}) with the details of "
        "our conversation so far, and they'll follow up as soon as possible."
    )
    return {
        "messages": [AIMessage(content=msg)],
        "ticket_id": t.ticket_id,
        "resolved": False,
        "category": "escalation",
    }


def reviewer(state: AgentState) -> dict:
    """Mark the turn resolved, unless a specialist flagged it for escalation."""
    if state.get("needs_escalation") and state.get("category") != "escalation":
        return {"resolved": False}
    return {"resolved": True}


def route_after_reviewer(state: AgentState) -> str:
    if state.get("needs_escalation") and state.get("category") != "escalation":
        return "escalation"
    return "end"
