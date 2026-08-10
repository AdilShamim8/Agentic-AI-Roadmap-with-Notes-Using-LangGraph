"""
Integration tests for the LangGraph supervisor.

These tests run the full supervisor graph against A2A agent servers
using in-process ASGI transports (no real network needed).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from a2a.client import A2AClient
from a2a.models import AgentCard
from agents.crewai_writer.server import WriterCrewExecutor, get_agent_card as writer_card
from agents.openai_research.server import (
    ResearchAgentExecutor,
    get_agent_card as research_card,
)
from agents.shared import build_a2a_server
from supervisor.a2a_adapter import A2AAdapter
from supervisor.graph import SupervisorGraph
from supervisor.state import AgentType
from supervisor.nodes import _parse_plan


# ---------------------------------------------------------------------------
# Fixtures: in-process A2A servers
# ---------------------------------------------------------------------------
@pytest.fixture
def research_server():
    card = research_card(base_url="http://test-research:8001")
    executor = ResearchAgentExecutor()
    return build_a2a_server(card, executor, port=8001)


@pytest.fixture
def writer_server():
    card = writer_card(base_url="http://test-writer:8002")
    executor = WriterCrewExecutor()
    return build_a2a_server(card, executor, port=8002)


@pytest.fixture
def research_transport(research_server):
    return ASGITransport(app=research_server.app)


@pytest.fixture
def writer_transport(writer_server):
    return ASGITransport(app=writer_server.app)


# ---------------------------------------------------------------------------
# Plan parsing
# ---------------------------------------------------------------------------
class TestPlanParsing:
    def test_parse_valid_plan(self):
        raw = (
            "[research] Research the topic\n"
            "[writing] Write an article about it"
        )
        plan = _parse_plan(raw, "test task")
        assert len(plan) == 2
        assert plan[0].agent == AgentType.RESEARCH
        assert plan[1].agent == AgentType.WRITING

    def test_parse_empty_plan_fallback(self):
        """Empty plan should fall back to a default 2-step plan."""
        plan = _parse_plan("", "do something")
        assert len(plan) == 2
        assert plan[0].agent == AgentType.RESEARCH
        assert plan[1].agent == AgentType.WRITING

    def test_parse_unparseable_lines(self):
        """Lines without [agent] prefix are treated as research steps."""
        raw = "Just a plain line\n[writing] Real writing step"
        plan = _parse_plan(raw, "test")
        assert len(plan) == 2
        assert plan[0].agent == AgentType.RESEARCH
        assert plan[1].agent == AgentType.WRITING


# ---------------------------------------------------------------------------
# A2A Adapter (using in-process transports)
# ---------------------------------------------------------------------------
class TestA2AAdapter:
    @pytest.mark.asyncio
    async def test_call_research_agent(self, research_transport):
        adapter = A2AAdapter(research_url="http://test-research")
        # Inject the transport into the client
        from a2a.client import A2AClient

        client = A2AClient("http://test-research", transport=research_transport)
        adapter._clients["http://test-research"] = client

        output, handoff = await adapter.call_agent(
            AgentType.RESEARCH, "Research AI agents", step_id=0
        )
        assert output
        assert len(output) > 50
        assert handoff.success
        assert handoff.latency_ms > 0
        assert handoff.agent == AgentType.RESEARCH
        await adapter.close()

    @pytest.mark.asyncio
    async def test_call_writing_agent(self, writer_transport):
        adapter = A2AAdapter(writing_url="http://test-writer")
        from a2a.client import A2AClient

        client = A2AClient("http://test-writer", transport=writer_transport)
        adapter._clients["http://test-writer"] = client

        output, handoff = await adapter.call_agent(
            AgentType.WRITING, "Write about AI", step_id=0
        )
        assert output
        assert len(output) > 50
        assert handoff.success
        assert handoff.agent == AgentType.WRITING
        await adapter.close()


# ---------------------------------------------------------------------------
# Full supervisor graph integration
# ---------------------------------------------------------------------------
class TestSupervisorGraph:
    @pytest.mark.asyncio
    async def test_supervisor_run(self, research_transport, writer_transport):
        """Full end-to-end supervisor run with in-process A2A agents."""
        from a2a.client import A2AClient

        adapter = A2AAdapter(
            research_url="http://test-research",
            writing_url="http://test-writer",
        )
        # Inject transports
        adapter._clients["http://test-research"] = A2AClient(
            "http://test-research", transport=research_transport
        )
        adapter._clients["http://test-writer"] = A2AClient(
            "http://test-writer", transport=writer_transport
        )

        graph = SupervisorGraph(adapter=adapter)
        state = await graph.run(
            "Research multi-agent AI systems and write a blog post about the findings"
        )

        assert state.final_output
        assert len(state.final_output) > 100
        assert len(state.plan) >= 2
        assert len(state.handoffs) >= 2
        assert all(h.success for h in state.handoffs)

    @pytest.mark.asyncio
    async def test_supervisor_streaming(self, research_transport, writer_transport):
        """Streaming mode should yield state updates at each node."""
        from a2a.client import A2AClient

        adapter = A2AAdapter(
            research_url="http://test-research",
            writing_url="http://test-writer",
        )
        adapter._clients["http://test-research"] = A2AClient(
            "http://test-research", transport=research_transport
        )
        adapter._clients["http://test-writer"] = A2AClient(
            "http://test-writer", transport=writer_transport
        )

        graph = SupervisorGraph(adapter=adapter)
        events = []
        async for node_name, state in graph.run_streaming(
            "Research and write about A2A protocol"
        ):
            events.append((node_name, state))

        # Should have at least: plan_start, plan_done, execute_start, execute_done, synthesize_start, synthesize_done
        node_names = [e[0] for e in events]
        assert "plan_done" in node_names
        assert "synthesize_done" in node_names
        assert events[-1][1].final_output
