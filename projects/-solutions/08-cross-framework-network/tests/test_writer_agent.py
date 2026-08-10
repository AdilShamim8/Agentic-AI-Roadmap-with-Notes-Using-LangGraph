"""
Tests for the CrewAI writer crew.
"""

import pytest

from agents.crewai_writer.crew import (
    CrewAIAgent,
    CrewAITask,
    Process,
    WriterCrew,
    create_writer_crew,
)
from agents.crewai_writer.server import WriterCrewExecutor, get_agent_card


class TestWriterCrew:
    @pytest.mark.asyncio
    async def test_crew_kickoff(self):
        crew = create_writer_crew()
        result = await crew.kickoff(inputs={"topic": "Multi-agent AI systems"})
        assert result.text
        assert len(result.text) > 100
        assert result.model

    @pytest.mark.asyncio
    async def test_crew_has_three_agents(self):
        crew = create_writer_crew()
        assert len(crew.agents) == 3
        roles = [a.role for a in crew.agents]
        assert "Content Strategist" in roles
        assert "Writer" in roles
        assert "Editor" in roles

    @pytest.mark.asyncio
    async def test_crew_has_three_tasks(self):
        crew = create_writer_crew()
        assert len(crew.tasks) == 3

    @pytest.mark.asyncio
    async def test_crew_deterministic(self):
        crew = create_writer_crew()
        r1 = await crew.kickoff(inputs={"topic": "AI safety"})
        r2 = await crew.kickoff(inputs={"topic": "AI safety"})
        assert r1.text == r2.text

    @pytest.mark.asyncio
    async def test_crew_metadata(self):
        crew = create_writer_crew()
        result = await crew.kickoff(inputs={"topic": "Test topic"})
        assert "crew" in result.metadata
        assert result.metadata["crew"]["process"] == Process.SEQUENTIAL.value
        assert result.metadata["crew"]["steps"] == 3


class TestCrewAIAgent:
    @pytest.mark.asyncio
    async def test_agent_execute(self):
        agent = CrewAIAgent(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory",
        )
        response = await agent.execute("Do something")
        assert response.text
        assert len(response.text) > 10


class TestWriterCrewCard:
    def test_agent_card(self):
        card = get_agent_card(base_url="http://test:8002")
        assert "Writer" in card.name
        assert "CrewAI" in card.name
        assert card.url == "http://test:8002"
        assert len(card.skills) >= 1
        assert card.skills[0].id == "writing"


class TestWriterCrewExecutor:
    @pytest.mark.asyncio
    async def test_executor_completes_task(self):
        from a2a.models import Message, MessageRole, Task, TaskState, TaskStatus, TextPart

        executor = WriterCrewExecutor()
        task = Task(
            id="test-write-1",
            status=TaskStatus(state=TaskState.SUBMITTED),
            history=[
                Message(
                    role=MessageRole.USER,
                    parts=[TextPart(text="Write about AI agents")],
                )
            ],
        )
        result = await executor(task)
        assert result.status.state == TaskState.COMPLETED
        assert len(result.artifacts) >= 1
        assert len(result.artifacts[0].parts[0].text) > 50
