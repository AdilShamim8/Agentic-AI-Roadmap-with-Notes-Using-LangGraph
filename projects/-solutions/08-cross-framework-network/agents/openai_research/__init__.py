"""
OpenAI Agents SDK — Research Agent (A2A server).

This module wraps an OpenAI Agents SDK-style agent as an A2A server.
The agent is configured with:

    * **Instructions**: a system prompt that scopes it to research tasks.
    * **Tools**: simulated search and summarization tools.
    * **Model**: provided by the pluggable LLM backend (mock by default).

When a task arrives via A2A, the agent:
    1. Extracts the user's query.
    2. Optionally invokes "tools" (simulated) for richer context.
    3. Generates a research briefing via the LLM backend.
    4. Returns the result as an A2A artifact.
"""

from agents.openai_research.agent import ResearchAgent, create_research_agent
from agents.openai_research.server import (
    ResearchAgentExecutor,
    create_server,
    get_agent_card,
)

__all__ = [
    "ResearchAgent",
    "create_research_agent",
    "ResearchAgentExecutor",
    "create_server",
    "get_agent_card",
]
