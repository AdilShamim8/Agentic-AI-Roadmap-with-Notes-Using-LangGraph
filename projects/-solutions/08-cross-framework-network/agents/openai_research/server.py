"""
A2A Server for the OpenAI Agents SDK Research Agent.

Exposes the :class:`ResearchAgent` as an A2A-compatible server.

Run directly::

    python -m agents.openai_research.server --port 8001

Or via the Makefile / docker-compose.
"""

from __future__ import annotations

import argparse
import logging
import os

from a2a.models import (
    AgentCapabilities,
    AgentCard,
    AgentProvider,
    AgentSkill,
)
from a2a.models import Task as A2ATask
from agents.openai_research.agent import ResearchAgent, create_research_agent
from agents.shared import build_a2a_server, complete_task, extract_user_text

logger = logging.getLogger(__name__)


def get_agent_card(base_url: str | None = None) -> AgentCard:
    """
    Build the Agent Card advertising this research agent.

    The card is served at ``/.well-known/agent.json`` and used by A2A
    clients for discovery.
    """
    host = os.environ.get("AGENT_HOST", "0.0.0.0")
    port = os.environ.get("AGENT_PORT", "8001")
    url = base_url or f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"

    return AgentCard(
        name="Research Agent (OpenAI Agents SDK)",
        description=(
            "A research specialist built on the OpenAI Agents SDK and "
            "exposed via the A2A protocol. Produces structured research "
            "briefings with findings, trends, and outlooks."
        ),
        url=url,
        version="1.0.0",
        protocolVersion="0.2.5",
        provider=AgentProvider(
            organization="Cross-Framework Network Demo",
            url="https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects",
        ),
        capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
        skills=[
            AgentSkill(
                id="research",
                name="Research Briefing",
                description=(
                    "Produces a structured research briefing on any topic, "
                    "including overview, key findings, trends, and outlook."
                ),
                tags=["research", "analysis", "information"],
                examples=[
                    "Research the current state of multi-agent AI systems",
                    "What are the latest trends in A2A protocol adoption?",
                ],
                inputModes=["text"],
                outputModes=["text"],
            ),
        ],
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
    )


class ResearchAgentExecutor:
    """
    Bridges A2A tasks to the ResearchAgent.

    Implements the ``execute(task) -> task`` protocol expected by
    :class:`InMemoryTaskManager`.
    """

    def __init__(self, agent: ResearchAgent | None = None) -> None:
        self.agent = agent or create_research_agent()

    async def __call__(self, task: A2ATask) -> A2ATask:
        query = extract_user_text(task)
        if not query:
            from a2a.models import Message, MessageRole, TaskState, TaskStatus, TextPart

            task.status = TaskStatus(
                state=TaskState.FAILED,
                message=Message(
                    role=MessageRole.AGENT,
                    parts=[TextPart(text="No query text found in task message.")],
                ),
            )
            return task

        try:
            response = await self.agent.run(query)
            return complete_task(task, response.text, model=response.model)
        except Exception as exc:
            logger.exception("Research agent failed: %s", exc)
            from a2a.models import Message, MessageRole, TaskState, TaskStatus, TextPart

            task.status = TaskStatus(
                state=TaskState.FAILED,
                message=Message(
                    role=MessageRole.AGENT,
                    parts=[TextPart(text=f"Research agent error: {exc}")],
                ),
            )
            return task


def create_server(port: int = 8001, host: str = "0.0.0.0") -> object:
    """Build (but do not start) the A2A server for the research agent."""
    card = get_agent_card(base_url=f"http://localhost:{port}")
    executor = ResearchAgentExecutor()
    return build_a2a_server(card, executor, host=host, port=port)


def main() -> None:
    """CLI entry point: start the research agent A2A server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Start the Research Agent A2A server")
    parser.add_argument("--host", default=os.environ.get("AGENT_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("AGENT_PORT", "8001")))
    args = parser.parse_args()

    logger.info("Starting Research Agent A2A server on %s:%s", args.host, args.port)
    card = get_agent_card(base_url=f"http://localhost:{args.port}")
    executor = ResearchAgentExecutor()
    server = build_a2a_server(card, executor, host=args.host, port=args.port)
    server.run()


if __name__ == "__main__":
    main()
