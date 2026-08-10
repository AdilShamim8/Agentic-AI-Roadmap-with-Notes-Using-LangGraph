"""
Tests for the research agent (OpenAI Agents SDK pattern).
"""

import pytest

from agents.openai_research.agent import ResearchAgent, create_research_agent
from agents.openai_research.server import ResearchAgentExecutor, get_agent_card


class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_agent_run(self):
        agent = create_research_agent()
        response = await agent.run("What is the A2A protocol?")
        assert response.text
        assert len(response.text) > 50
        assert response.model  # should report a model id

    @pytest.mark.asyncio
    async def test_agent_deterministic(self):
        """Same input should produce same output (mock LLM is deterministic)."""
        agent = create_research_agent()
        r1 = await agent.run("Quantum computing basics")
        r2 = await agent.run("Quantum computing basics")
        assert r1.text == r2.text

    @pytest.mark.asyncio
    async def test_agent_name(self):
        agent = ResearchAgent()
        assert agent.name == "Research Agent"

    @pytest.mark.asyncio
    async def test_agent_has_tools(self):
        agent = create_research_agent()
        assert len(agent.tools) >= 2  # search + summarize


class TestResearchAgentCard:
    def test_agent_card(self):
        card = get_agent_card(base_url="http://test:8001")
        assert "Research Agent" in card.name
        assert card.url == "http://test:8001"
        assert len(card.skills) >= 1
        assert card.skills[0].id == "research"

    def test_agent_card_capabilities(self):
        card = get_agent_card()
        assert card.capabilities.streaming is True


class TestResearchExecutor:
    @pytest.mark.asyncio
    async def test_executor_completes_task(self):
        from a2a.models import Message, MessageRole, Task, TaskState, TaskStatus, TextPart

        executor = ResearchAgentExecutor()
        task = Task(
            id="test-1",
            status=TaskStatus(state=TaskState.SUBMITTED),
            history=[
                Message(
                    role=MessageRole.USER,
                    parts=[TextPart(text="Research multi-agent systems")],
                )
            ],
        )
        result = await executor(task)
        assert result.status.state == TaskState.COMPLETED
        assert len(result.artifacts) >= 1
        assert result.artifacts[0].parts[0].text

    @pytest.mark.asyncio
    async def test_executor_no_query(self):
        from a2a.models import Task, TaskState, TaskStatus

        executor = ResearchAgentExecutor()
        task = Task(id="test-2", status=TaskStatus(state=TaskState.SUBMITTED))
        result = await executor(task)
        assert result.status.state == TaskState.FAILED
