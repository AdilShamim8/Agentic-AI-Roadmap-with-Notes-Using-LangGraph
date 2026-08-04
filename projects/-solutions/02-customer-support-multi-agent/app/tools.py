"""
LangChain `@tool`-decorated wrappers around the framework-agnostic functions
in `core/`. These are only used when a real LLM is configured (see
app/llm.py) - each specialist agent is built with `create_react_agent`
bound to the subset of tools relevant to it, so the LLM decides which
tool(s) to call and with what arguments, then writes the final reply.
"""
from __future__ import annotations

from langchain_core.tools import tool

from core import billing, orders, tickets
from core.knowledge_base import search_kb as _search_kb


@tool
def lookup_invoice(customer_id: str) -> str:
    """Look up the most recent invoice for a customer, given their customer ID (e.g. CUST-1001)."""
    return billing.get_latest_invoice(customer_id).message


@tool
def issue_refund(invoice_id: str, reason: str) -> str:
    """Issue a refund for a specific invoice ID (e.g. INV-9001), given a short reason."""
    return billing.process_refund(invoice_id, reason).message


@tool
def get_order_status(order_id: str) -> str:
    """Look up shipping/delivery status for an order, given its order ID (e.g. ORD-5001)."""
    return orders.get_order_status(order_id).message


@tool
def search_knowledge_base(query: str) -> str:
    """Search internal help-center articles for policy/how-to information relevant to `query`."""
    hits = _search_kb(query, k=2)
    if not hits:
        return "No relevant knowledge base article was found."
    return "\n\n---\n\n".join(f"[{h.title}]\n{h.content}" for h in hits)


@tool
def create_support_ticket(customer_id: str, category: str, summary: str, priority: str = "normal") -> str:
    """
    Create a support ticket for a human agent to follow up on. Use this when you
    cannot resolve the issue yourself, or the customer explicitly asks for a human.
    priority must be one of: low, normal, high, urgent.
    """
    t = tickets.create_ticket(customer_id, category, summary, priority=priority)
    return f"Ticket {t.ticket_id} created (priority: {priority}). A human agent will follow up."


BILLING_TOOLS = [lookup_invoice, issue_refund, search_knowledge_base]
TECHNICAL_TOOLS = [search_knowledge_base, create_support_ticket]
ORDER_TOOLS = [get_order_status, search_knowledge_base]
GENERAL_TOOLS = [search_knowledge_base]
