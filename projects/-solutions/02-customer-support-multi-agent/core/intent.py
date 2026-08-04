"""
Keyword-based intent classifier used by the supervisor node to route a
message to the right specialist agent.

This is intentionally a fast, deterministic, dependency-free classifier
rather than an LLM call: routing is a low-ambiguity, high-frequency
decision, so a cheap heuristic keeps latency and cost down and keeps the
whole graph testable without an API key. Swap in an LLM-based classifier
(see app/agents.py `USE_LLM_ROUTER`) if you need to handle more nuanced,
multi-intent messages.
"""
from __future__ import annotations

import re
from typing import Literal

Category = Literal["billing", "technical", "order", "general"]

_KEYWORDS: dict[Category, list[str]] = {
    "billing": [
        "refund", "charge", "charged", "invoice", "payment", "billing",
        "subscription", "price", "cost", "credit card", "card declined",
        "overcharged", "receipt", "cancel my plan", "renew",
    ],
    "order": [
        "order", "tracking", "track", "shipment", "shipped", "delivery",
        "package", "delayed", "where is my", "arrive", "arrived",
    ],
    "technical": [
        "login", "log in", "password", "error", "bug", "crash", "crashed",
        "not working", "sync", "2fa", "two-factor", "app won't", "reset",
        "500 error", "broken", "glitch",
    ],
}

ORDER_ID_RE = re.compile(r"\bORD-\d+\b", re.IGNORECASE)
INVOICE_ID_RE = re.compile(r"\bINV-\d+\b", re.IGNORECASE)
CUSTOMER_ID_RE = re.compile(r"\bCUST-\d+\b", re.IGNORECASE)


def classify_intent(text: str) -> Category:
    """Classify free-text customer message into one of the specialist categories."""
    lowered = text.lower()

    if ORDER_ID_RE.search(text):
        return "order"
    if INVOICE_ID_RE.search(text):
        return "billing"

    scores = {category: 0 for category in _KEYWORDS}
    for category, keywords in _KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                scores[category] += 1

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        return "general"
    return best_category


def extract_ids(text: str) -> dict[str, str | None]:
    """Pull any order/invoice/customer IDs mentioned in free text, e.g. 'ORD-5001'."""
    order_match = ORDER_ID_RE.search(text)
    invoice_match = INVOICE_ID_RE.search(text)
    customer_match = CUSTOMER_ID_RE.search(text)
    return {
        "order_id": order_match.group(0).upper() if order_match else None,
        "invoice_id": invoice_match.group(0).upper() if invoice_match else None,
        "customer_id": customer_match.group(0).upper() if customer_match else None,
    }
