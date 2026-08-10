"""
Research Agent — mirrors the OpenAI Agents SDK ``Agent`` pattern.

In the real OpenAI Agents SDK, an ``Agent`` is defined by its name,
instructions, model, and tools.  This module replicates that structure
using the pluggable LLM backend so that the agent works with either a
mock or a real OpenAI model.

The agent is specialized for **research**: it produces structured
briefings with findings, trends, and outlooks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from llm import get_llm
from llm.base import LLMBackend, LLMResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Simulated tools (in production, these would be real function tools)
# ---------------------------------------------------------------------------
@dataclass
class ToolResult:
    name: str
    result: str


async def _search_tool(query: str) -> ToolResult:
    """Simulated web search tool."""
    return ToolResult(
        name="web_search",
        result=(
            f"[Simulated search results for '{query}']:\n"
            f"- Result 1: Overview and definition of the topic\n"
            f"- Result 2: Recent developments and news\n"
            f"- Result 3: Academic perspective and citations\n"
            f"- Result 4: Industry analysis and market data\n"
            f"- Result 5: Community discussion and open questions"
        ),
    )


async def _summarize_tool(text: str) -> ToolResult:
    """Simulated summarization tool."""
    summary = text[:500] + ("..." if len(text) > 500 else "")
    return ToolResult(name="summarize", result=f"[Summary]: {summary}")


# ---------------------------------------------------------------------------
# Agent definition (mirrors openai.agents.Agent)
# ---------------------------------------------------------------------------
@dataclass
class ResearchAgent:
    """
    A research-focused agent.

    Mirrors the structure of ``openai.agents.Agent``:
        - ``name``: display name
        - ``instructions``: system prompt
        - ``model``: LLM backend
        - ``tools``: list of tool coroutines
    """

    name: str = "Research Agent"
    instructions: str = (
        "You are an expert research assistant. Given a query, produce a "
        "structured research briefing with: (1) an overview, (2) key "
        "findings, (3) trends, (4) considerations, and (5) an outlook. "
        "Be thorough, factual, and well-organized. Use markdown formatting."
    )
    model: LLMBackend = field(default_factory=get_llm)
    tools: list = field(default_factory=lambda: [_search_tool, _summarize_tool])

    async def run(self, query: str) -> LLMResponse:
        """
        Execute the agent on a user query.

        Mirrors ``openai.agents.Runner.run(agent, query)``.
        """
        logger.info("ResearchAgent '%s' processing query: %s", self.name, query[:100])

        # Step 1: Run the search tool for context enrichment.
        search_result = await _search_tool(query)

        # Step 2: Build the augmented prompt.
        augmented_prompt = (
            f"Research Query: {query}\n\n"
            f"Context from search:\n{search_result.result}\n\n"
            f"Produce a comprehensive research briefing."
        )

        # Step 3: Generate the response via the LLM backend.
        response = await self.model.generate(
            prompt=augmented_prompt,
            system=self.instructions,
            max_tokens=1024,
            temperature=0.4,  # Lower temperature for factual research
        )

        logger.info(
            "ResearchAgent completed: %d chars, %.1fms",
            len(response.text),
            response.latency_ms,
        )
        return response


def create_research_agent() -> ResearchAgent:
    """Factory for the default research agent."""
    return ResearchAgent()
