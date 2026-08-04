"""
Quick end-to-end sanity check after `pip install -r requirements.txt`.

Run with:  python scripts/smoke_test.py

Exercises the compiled graph with a handful of representative messages and
prints the routed category + reply for each, so you can eyeball that
routing, tools, and (if configured) the LLM are all wired up correctly.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage  # noqa: E402

from app.graph import build_graph  # noqa: E402
from app.llm import is_mock_mode  # noqa: E402

SAMPLE_MESSAGES = [
    "Where is my order ORD-5001?",
    "I was charged twice this month, my customer ID is CUST-1001",
    "The app keeps crashing every time I try to log in",
    "What's your return policy?",
    "This is absolutely unacceptable, I want to speak to a manager NOW!!",
]


def main() -> None:
    graph = build_graph()
    mode = "MOCK" if is_mock_mode() else "LIVE LLM"
    print(f"Running smoke test in {mode} mode\n")

    for msg in SAMPLE_MESSAGES:
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = graph.invoke({"messages": [HumanMessage(content=msg)]}, config=config)
        reply = result["messages"][-1].content

        print(f"> {msg}")
        print(
            f"  category={result.get('category')} sentiment={result.get('sentiment')} "
            f"resolved={result.get('resolved')} ticket={result.get('ticket_id')}"
        )
        print(f"  reply: {reply[:200]}{'...' if len(reply) > 200 else ''}\n")


if __name__ == "__main__":
    main()
