"""
Writer Crew — mirrors the CrewAI ``Crew`` / ``Agent`` / ``Task`` pattern.

In real CrewAI:

    from crewai import Agent, Task, Crew, Process

    strategist = Agent(role="Content Strategist", goal="...", backstory="...")
    writer = Agent(role="Writer", goal="...", backstory="...")
    editor = Agent(role="Editor", goal="...", backstory="...")

    crew = Crew(
        agents=[strategist, writer, editor],
        tasks=[planning_task, writing_task, editing_task],
        process=Process.sequential,
    )
    result = crew.kickoff(inputs={"topic": "..."})

This module replicates that structure using the pluggable LLM backend.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from llm import get_llm
from llm.base import LLMBackend, LLMResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CrewAI-style enums
# ---------------------------------------------------------------------------
class Process(str, Enum):
    """CrewAI process types."""

    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"


# ---------------------------------------------------------------------------
# CrewAI-style Agent
# ---------------------------------------------------------------------------
@dataclass
class CrewAIAgent:
    """
    A single agent within a CrewAI crew.

    Mirrors ``crewai.Agent``:
        - ``role``: the agent's job title
        - ``goal``: what the agent aims to achieve
        - ``backstory``: persona context for the LLM
        - ``llm``: the model backing this agent
    """

    role: str
    goal: str
    backstory: str
    llm: LLMBackend = field(default_factory=get_llm)

    async def execute(self, task_description: str, context: str = "") -> LLMResponse:
        """Run this agent on a task description with optional context."""
        system = f"You are a {self.role}. {self.backstory}\nYour goal: {self.goal}"
        prompt = task_description
        if context:
            prompt = f"Context from previous step:\n{context}\n\n{task_description}"
        logger.info("CrewAI Agent '%s' executing task", self.role)
        return await self.llm.generate(
            prompt=prompt,
            system=system,
            max_tokens=1024,
            temperature=0.6,
        )


# ---------------------------------------------------------------------------
# CrewAI-style Task
# ---------------------------------------------------------------------------
@dataclass
class CrewAITask:
    """A task within a crew, mirroring ``crewai.Task``."""

    description: str
    agent: CrewAIAgent
    expected_output: str = "A well-structured text response."


# ---------------------------------------------------------------------------
# Writer Crew
# ---------------------------------------------------------------------------
class WriterCrew:
    """
    A CrewAI-style crew specialized for writing tasks.

    Composed of three agents:
        1. Content Strategist — plans structure and angle.
        2. Writer — drafts based on the strategy.
        3. Editor — reviews and polishes.

    The crew runs sequentially: each agent's output feeds the next.
    """

    def __init__(self) -> None:
        self.strategist = CrewAIAgent(
            role="Content Strategist",
            goal="Plan the structure, tone, and key messages of the content",
            backstory=(
                "You are a veteran content strategist with 15 years of "
                "experience in editorial planning. You know how to hook "
                "readers, structure arguments, and choose the right angle "
                "for any audience."
            ),
        )
        self.writer = CrewAIAgent(
            role="Writer",
            goal="Draft compelling, well-structured content based on the strategy",
            backstory=(
                "You are an award-winning writer with a gift for clear, "
                "engaging prose. You adapt your voice to any topic while "
                "maintaining depth and precision."
            ),
        )
        self.editor = CrewAIAgent(
            role="Editor",
            goal="Review, polish, and finalize the content for quality and clarity",
            backstory=(
                "You are a meticulous editor who catches every typo, "
                "strengthens every weak transition, and ensures the final "
                "piece is publication-ready."
            ),
        )

        self.agents: list[CrewAIAgent] = [self.strategist, self.writer, self.editor]

        self.tasks: list[CrewAITask] = [
            CrewAITask(
                description=(
                    "Analyze the writing request and produce a content "
                    "strategy: title, target audience, tone, outline with "
                    "3-5 sections, and key messages."
                ),
                agent=self.strategist,
                expected_output="A content strategy document with outline.",
            ),
            CrewAITask(
                description=(
                    "Using the content strategy provided, write the full "
                    "piece. Follow the outline, hit all key messages, and "
                    "ensure the tone matches the strategy."
                ),
                agent=self.writer,
                expected_output="A complete draft of the content.",
            ),
            CrewAITask(
                description=(
                    "Review the draft for clarity, flow, grammar, and "
                    "impact. Make improvements and produce the final "
                    "version. Add a brief editor's note at the end."
                ),
                agent=self.editor,
                expected_output="The final, polished piece ready for publication.",
            ),
        ]

    async def kickoff(self, inputs: dict[str, Any]) -> LLMResponse:
        """
        Run the crew sequentially.

        Mirrors ``crew.kickoff(inputs=...)``.  Each task's output becomes
        context for the next.  Returns the final agent's response.
        """
        topic = inputs.get("topic", inputs.get("query", ""))

        logger.info("WriterCrew kickoff: topic='%s'", topic[:80])

        context = f"Writing request: {topic}"
        final_response: LLMResponse | None = None

        for i, task in enumerate(self.tasks):
            logger.info("WriterCrew step %d/%d: %s", i + 1, len(self.tasks), task.agent.role)
            response = await task.agent.execute(task.description, context=context)
            context = response.text
            final_response = response

        assert final_response is not None
        # Append a crew summary.
        final_response.metadata["crew"] = {
            "agents": [a.role for a in self.agents],
            "process": Process.SEQUENTIAL.value,
            "steps": len(self.tasks),
        }
        return final_response


def create_writer_crew() -> WriterCrew:
    """Factory for the default writer crew."""
    return WriterCrew()
