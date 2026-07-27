"""ReAct agent with web search and calculator tools.

Demonstrates the foundational agent pattern: the LLM reasons about what
to do, calls a tool, observes the result, and repeats until it can
answer.

Run:
    python examples/react_demo.py

Environment:
    OPENAI_API_KEY - required
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

load_dotenv()


@tool
def web_search(query: str) -> str:
    """Search the web for current information.

    Use when the question requires up-to-date information or facts not
    in your training data. Do not use for math (use calculator instead).

    Args:
        query: The search query, e.g. "population of Tokyo 2026".

    Returns:
        A string with the search results.
    """
    # In production, call Tavily, Brave, or another search API.
    return f"[Search results for: {query}]"


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression.

    Use for any arithmetic or calculation. Input should be a valid
    Python expression like '2 + 2' or '13960000 * 2'.

    Args:
        expression: A Python-evaluable math expression.

    Returns:
        The result as a string, or an error message.
    """
    try:
        # Restrict builtins for safety.
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def build_agent():
    """Build the ReAct agent."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    agent = create_react_agent(
        llm,
        tools=[web_search, calculator],
        recursion_limit=8,
    )
    return agent


# Module-level agent.
agent = build_agent()


def main() -> None:
    """Run a demo question that requires both tools."""
    print("\n=== ReAct demo ===")
    print("Question: What is the population of Tokyo times 2?\n")

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What is the population of Tokyo times 2?"}]}
    )

    # Print the tool calls and the final answer.
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for call in msg.tool_calls:
                print(f"  [tool call] {call['name']}({call['args']})")
        elif msg.type == "tool":
            print(f"  [tool result] {msg.content[:100]}")
        elif msg.type == "ai" and msg.content:
            print(f"\nFinal answer: {msg.content}")


if __name__ == "__main__":
    main()
