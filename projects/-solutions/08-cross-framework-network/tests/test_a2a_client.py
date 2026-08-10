"""
Tests for the A2A client — discovery, task sending, error handling.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from a2a.client import A2AClient
from a2a.models import AgentCard, Message, MessageRole, TextPart
from a2a.server import A2AServer, InMemoryTaskManager
from agents.shared import build_a2a_server, complete_task, extract_user_text


async def _echo_executor(task):
    text = extract_user_text(task)
    return complete_task(task, f"Result: {text}", model="test")


@pytest.fixture
def test_card():
    return AgentCard(
        name="Client Test Agent",
        description="For client tests",
        url="http://test:9998",
    )


@pytest.fixture
def test_server(test_card):
    return build_a2a_server(test_card, _echo_executor, port=9998)


@pytest.fixture
def transport(test_server):
    return ASGITransport(app=test_server.app)


class TestAgentCardDiscovery:
    @pytest.mark.asyncio
    async def test_get_agent_card(self, transport, test_card):
        async with A2AClient("http://test", transport=transport) as client:
            card = await client.get_agent_card()
            assert card.name == "Client Test Agent"
            assert card.url == "http://test:9998"
            assert client.agent_card is not None


class TestSendTask:
    @pytest.mark.asyncio
    async def test_send_task_text(self, transport):
        async with A2AClient("http://test", transport=transport) as client:
            task = await client.send_task("Hello, agent!")
            assert task.status.state.value == "completed"
            assert len(task.artifacts) >= 1
            assert "Result: Hello, agent!" in task.artifacts[0].parts[0].text

    @pytest.mark.asyncio
    async def test_send_task_message(self, transport):
        msg = Message(
            role=MessageRole.USER,
            parts=[TextPart(text="Structured message test")],
        )
        async with A2AClient("http://test", transport=transport) as client:
            task = await client.send_task(message=msg)
            assert task.status.state.value == "completed"
            assert "Result: Structured message test" in task.artifacts[0].parts[0].text

    @pytest.mark.asyncio
    async def test_send_task_with_id(self, transport):
        async with A2AClient("http://test", transport=transport) as client:
            task = await client.send_task("Test", task_id="custom-id-123")
            assert task.id == "custom-id-123"


class TestGetTask:
    @pytest.mark.asyncio
    async def test_get_task(self, transport):
        async with A2AClient("http://test", transport=transport) as client:
            created = await client.send_task("Get me later", task_id="get-test-1")
            fetched = await client.get_task("get-test-1")
            assert fetched.id == created.id
            assert fetched.status.state.value == "completed"


class TestListTasks:
    @pytest.mark.asyncio
    async def test_list_tasks(self, transport):
        async with A2AClient("http://test", transport=transport) as client:
            await client.send_task("Task A", task_id="list-a")
            await client.send_task("Task B", task_id="list-b")
            tasks = await client.list_tasks()
            assert len(tasks) >= 2
            ids = {t.id for t in tasks}
            assert "list-a" in ids
            assert "list-b" in ids


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, transport):
        from a2a.exceptions import JSONRPCError

        async with A2AClient("http://test", transport=transport) as client:
            with pytest.raises(JSONRPCError):
                await client.get_task("does-not-exist")
