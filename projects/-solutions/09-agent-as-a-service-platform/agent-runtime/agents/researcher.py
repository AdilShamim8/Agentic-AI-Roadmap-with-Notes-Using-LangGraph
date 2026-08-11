"""Sample researcher agent — answers factual questions with a knowledge base."""
import asyncio
from typing import Any


# A tiny built-in knowledge base. In production this would be RAG over a
# vector store, a web search call, or an LLM call.
KNOWLEDGE_BASE: dict[str, str] = {
    "a2a": (
        "A2A (Agent-to-Agent) is an open protocol by Google for agent "
        "interoperability. Agents advertise their capabilities via an Agent "
        "Card at /.well-known/agent.json, and clients invoke them via "
        "JSON-RPC over HTTP using the tasks/send method. The protocol "
        "supports streaming, push notifications, and stateful sessions."
    ),
    "agent card": (
        "An Agent Card is a JSON document at /.well-known/agent.json that "
        "declares an agent's identity, capabilities, skills, authentication "
        "schemes, and endpoints. It is the discovery mechanism in A2A."
    ),
    "langgraph": (
        "LangGraph is a framework from LangChain for building stateful, "
        "multi-actor agent applications as graphs. It supports cycles, "
        "memory, and human-in-the-loop flows. LangGraph Platform is its "
        "managed deployment offering."
    ),
    "fastapi": (
        "FastAPI is a modern Python web framework for building APIs. It is "
        "ASGI-native, uses Pydantic for validation, and auto-generates "
        "OpenAPI docs. It is widely used for ML and AI backend services."
    ),
    "stripe": (
        "Stripe is a payment infrastructure provider. Its API supports "
        "subscriptions, metered billing, one-time charges, and webhooks. "
        "For per-invocation billing we typically use idempotent "
        "UsageRecord calls on a metered subscription item."
    ),
}


async def handle(input_text: str) -> str:
    """Answer a factual question from the knowledge base."""
    await asyncio.sleep(0.05)  # simulate latency

    q = input_text.lower().strip()
    for key, answer in KNOWLEDGE_BASE.items():
        if key in q:
            return f"[Researcher] {answer}"

    return (
        "[Researcher] I don't have a cached answer for that. In production I "
        "would call a search engine or LLM. Try asking about: "
        + ", ".join(KNOWLEDGE_BASE.keys())
    )
