"""
Tests for the A2A server — task management, JSON-RPC dispatch, Agent Card.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from a2a.models import (
    AgentCard,
    Message,
    MessageRole,
    TaskState,
    TextPart,
)
from a2a.server import A2AServer, InMemoryTaskManager
from agents.shared import build_a2a_server, complete_task, extract_user_text


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def test_agent_card():
    return AgentCard(
        name="Test Agent",
        description="A test agent",
        url="http://test:9999",
        version="1.0.0",
    )


async def _simple_execute(task):
    """A simple executor that echoes the input."""
    text = extract_user_text(task)
    return complete_task(task, f"Echo: {text}", model="test-model")


@pytest.fixture
def test_server(test_agent_card):
    return build_a2a_server(test_agent_card, _simple_execute, port=9999)


@pytest.fixture
async def client(test_server):
    transport = ASGITransport(app=test_server.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Agent Card endpoint
# ---------------------------------------------------------------------------
class TestAgentCardEndpoint:
    @pytest.mark.asyncio
    async def test_get_agent_card(self, client, test_agent_card):
        resp = await client.get("/.well-known/agent.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Agent"
        assert data["url"] == "http://test:9999"
        assert data["protocolVersion"] == "0.2.5"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_card" in data


# ---------------------------------------------------------------------------
# JSON-RPC task/send
# ---------------------------------------------------------------------------
class TestSendTask:
    @pytest.mark.asyncio
    async def test_send_task(self, client):
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello, agent!"}],
                }
            },
        }
        resp = await client.post("/", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "1"
        assert "result" in data
        assert "error" not in data
        task = data["result"]
        assert task["status"]["state"] == "completed"
        assert len(task["artifacts"]) >= 1
        assert "Echo: Hello, agent!" in task["artifacts"][0]["parts"][0]["text"]

    @pytest.mark.asyncio
    async def test_send_task_with_id(self, client):
        """Sending a task with an explicit ID should reuse that ID."""
        payload = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tasks/send",
            "params": {
                "id": "my-task-id",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Test"}],
                }
            },
        }
        resp = await client.post("/", json=payload)
        data = resp.json()
        assert data["result"]["id"] == "my-task-id"

    @pytest.mark.asyncio
    async def test_invalid_jsonrpc(self, client):
        """Missing jsonrpc field should return an error."""
        payload = {"id": "1", "method": "tasks/send", "params": {}}
        resp = await client.post("/", json=payload)
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32600  # Invalid Request


# ---------------------------------------------------------------------------
# JSON-RPC tasks/get
# ---------------------------------------------------------------------------
class TestGetTask:
    @pytest.mark.asyncio
    async def test_get_existing_task(self, client):
        # First create a task
        send_payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tasks/send",
            "params": {
                "id": "get-test-id",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Test"}],
                }
            },
        }
        await client.post("/", json=send_payload)

        # Now get it
        get_payload = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tasks/get",
            "params": {"id": "get-test-id"},
        }
        resp = await client.post("/", json=get_payload)
        data = resp.json()
        assert data["result"]["id"] == "get-test-id"
        assert data["result"]["status"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, client):
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tasks/get",
            "params": {"id": "nonexistent"},
        }
        resp = await client.post("/", json=payload)
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32001  # Task not found


# ---------------------------------------------------------------------------
# JSON-RPC tasks/cancel
# ---------------------------------------------------------------------------
class TestCancelTask:
    @pytest.mark.asyncio
    async def test_cancel_completed_task_fails(self, client):
        # Create and complete a task first
        await client.post("/", json={
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tasks/send",
            "params": {
                "id": "cancel-test",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Test"}],
                }
            },
        })
        # Try to cancel the completed task
        resp = await client.post("/", json={
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tasks/cancel",
            "params": {"id": "cancel-test"},
        })
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32002  # Not cancelable


# ---------------------------------------------------------------------------
# JSON-RPC tasks/list
# ---------------------------------------------------------------------------
class TestListTasks:
    @pytest.mark.asyncio
    async def test_list_tasks(self, client):
        # Create a couple of tasks
        for i in range(3):
            await client.post("/", json={
                "jsonrpc": "2.0",
                "id": str(i),
                "method": "tasks/send",
                "params": {
                    "id": f"list-test-{i}",
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": f"Task {i}"}],
                    }
                },
            })
        # List them
        resp = await client.post("/", json={
            "jsonrpc": "2.0",
            "id": "99",
            "method": "tasks/list",
            "params": {},
        })
        data = resp.json()
        assert isinstance(data["result"], list)
        assert len(data["result"]) >= 3


# ---------------------------------------------------------------------------
# Unknown method
# ---------------------------------------------------------------------------
class TestUnknownMethod:
    @pytest.mark.asyncio
    async def test_unknown_method(self, client):
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tasks/unknown",
            "params": {},
        }
        resp = await client.post("/", json=payload)
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found
