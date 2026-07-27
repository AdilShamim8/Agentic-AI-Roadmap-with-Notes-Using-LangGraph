"""Conversational ReAct agent with persistence and a recursion limit.

This is the minimum viable production agent: it uses create_react_agent,
has a tool, persists state with MemorySaver (swap for PostgresSaver in
production), and has a recursion limit to prevent infinite loops.

Run:
    python examples/conversational_agent_demo.py

Environment:
    OPENAI_API_KEY - required
"""

from __future__ import annotations

import os
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

# A simple tool. In production, this would call a real weather API.
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location.

    Use this when the user asks about current weather, temperature, or
    conditions. Do not use this for forecasts.

    Args:
        location: City and state/country, e.g. "San Francisco, CA".

    Returns:
        A string like "72F, sunny in San Francisco".
    """
    # In production, call a real weather API here.
    return f"72F, sunny in {location}"


def build_agent() -> object:
    """Build the conversational agent.

    Returns a compiled LangGraph agent. The agent is stateless between
    calls unless a thread_id is provided in the config.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    # MemorySaver for dev; use PostgresSaver for production.
    checkpointer = MemorySaver()
    agent = create_react_agent(
        llm,
        tools=[get_weather],
        checkpointer=checkpointer,
        recursion_limit=8,  # safety net: max 8 LLM calls per request
    )
    return agent


# Module-level agent, used by the eval runner and the deployment.
agent = build_agent()


def main() -> None:
    """Run a two-turn conversation to demonstrate persistence."""
    config = {"configurable": {"thread_id": "demo-001"}}

    # Turn 1
    print("\n=== Turn 1 ===")
    print("User: What's the weather in San Francisco?")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config=config,
    )
    print(f"Agent: {result['messages'][-1].content}")

    # Turn 2 - the agent remembers the previous turn
    print("\n=== Turn 2 ===")
    print("User: What about Tokyo?")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What about Tokyo?"}]},
        config=config,
    )
    print(f"Agent: {result['messages'][-1].content}")


if __name__ == "__main__":
    main()
