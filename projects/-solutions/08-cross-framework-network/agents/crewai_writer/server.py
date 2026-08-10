"""
A2A Server for the CrewAI Writer Crew.

Exposes the :class:`WriterCrew` as an A2A-compatible server.

Run directly::

    python -m agents.crewai_writer.server --port 8002
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
from agents.crewai_writer.crew import WriterCrew, create_writer_crew
from agents.shared import build_a2a_server, complete_task, extract_user_text

logger = logging.getLogger(__name__)


def get_agent_card(base_url: str | None = None) -> AgentCard:
    """Build the Agent Card advertising this writer crew."""
    host = os.environ.get("AGENT_HOST", "0.0.0.0")
    port = os.environ.get("AGENT_PORT", "8002")
    url = base_url or f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"

    return AgentCard(
        name="Writer Crew (CrewAI)",
        description=(
            "A writing specialist built on CrewAI and exposed via the "
            "A2A protocol. Produces polished, publication-ready content "
            "through a three-agent crew: strategist, writer, and editor."
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
                id="writing",
                name="Content Writing",
                description=(
                    "Produces polished written content on any topic through "
                    "a multi-agent crew (strategist → writer → editor)."
                ),
                tags=["writing", "content", "editorial"],
                examples=[
                    "Write a blog post about multi-agent AI systems",
                    "Draft a technical article about the A2A protocol",
                ],
                inputModes=["text"],
                outputModes=["text"],
            ),
        ],
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
    )


class WriterCrewExecutor:
    """
    Bridges A2A tasks to the WriterCrew.

    Implements the ``execute(task) -> task`` protocol expected by
    :class:`InMemoryTaskManager`.
    """

    def __init__(self, crew: WriterCrew | None = None) -> None:
        self.crew = crew or create_writer_crew()

    async def __call__(self, task: A2ATask) -> A2ATask:
        query = extract_user_text(task)
        if not query:
            from a2a.models import Message, MessageRole, TaskState, TaskStatus, TextPart

            task.status = TaskStatus(
                state=TaskState.FAILED,
                message=Message(
                    role=MessageRole.AGENT,
                    parts=[TextPart(text="No writing request found in task message.")],
                ),
            )
            return task

        try:
            response = await self.crew.kickoff(inputs={"topic": query, "query": query})
            return complete_task(task, response.text, model=response.model)
        except Exception as exc:
            logger.exception("Writer crew failed: %s", exc)
            from a2a.models import Message, MessageRole, TaskState, TaskStatus, TextPart

            task.status = TaskStatus(
                state=TaskState.FAILED,
                message=Message(
                    role=MessageRole.AGENT,
                    parts=[TextPart(text=f"Writer crew error: {exc}")],
                ),
            )
            return task


def create_server(port: int = 8002, host: str = "0.0.0.0") -> object:
    """Build (but do not start) the A2A server for the writer crew."""
    card = get_agent_card(base_url=f"http://localhost:{port}")
    executor = WriterCrewExecutor()
    return build_a2a_server(card, executor, host=host, port=port)


def main() -> None:
    """CLI entry point: start the writer crew A2A server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Start the Writer Crew A2A server")
    parser.add_argument("--host", default=os.environ.get("AGENT_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("AGENT_PORT", "8002")))
    args = parser.parse_args()

    logger.info("Starting Writer Crew A2A server on %s:%s", args.host, args.port)
    card = get_agent_card(base_url=f"http://localhost:{args.port}")
    executor = WriterCrewExecutor()
    server = build_a2a_server(card, executor, host=args.host, port=args.port)
    server.run()


if __name__ == "__main__":
    main()
