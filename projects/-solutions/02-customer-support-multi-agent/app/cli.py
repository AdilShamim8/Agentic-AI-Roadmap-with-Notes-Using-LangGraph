"""
Interactive terminal chat client for the customer support multi-agent graph.

Run with:  python -m app.cli

Conversation state (messages, customer_id, category, etc.) is persisted per
thread_id by LangGraph's MemorySaver checkpointer, so you only need to send
the newest message each turn - not the whole history.
"""
from __future__ import annotations

import uuid

from langchain_core.messages import HumanMessage

from app.graph import build_graph
from app.llm import is_mock_mode


def main() -> None:
    graph = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    mode = "MOCK (no API key configured - deterministic template responses)" if is_mock_mode() else "LIVE LLM"
    print("=" * 70)
    print("Customer Support Multi-Agent - CLI demo")
    print(f"Mode: {mode}")
    print(f"Thread ID: {thread_id}")
    print("Try:")
    print("  Where is my order ORD-5001?")
    print("  I was charged twice, my customer ID is CUST-1001")
    print("  This is ridiculous, I want to speak to a manager!!")
    print("Type 'exit' to quit.")
    print("=" * 70)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        result = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)
        reply = result["messages"][-1]

        print(f"\nAgent [{result.get('category', '?')}]: {reply.content}")
        if result.get("ticket_id"):
            print(f"   (ticket: {result['ticket_id']}, resolved: {result.get('resolved')})")


if __name__ == "__main__":
    main()
