"""
Tests for A2A protocol data models — serialization, validation, defaults.
"""

import pytest
from a2a.models import (
    AgentCard,
    AgentSkill,
    Artifact,
    DataPart,
    FilePart,
    FileWithBytes,
    Message,
    MessageRole,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)


class TestTextPart:
    def test_creation(self):
        part = TextPart(text="Hello")
        assert part.type == "text"
        assert part.text == "Hello"

    def test_serialization(self):
        part = TextPart(text="Hello", metadata={"lang": "en"})
        d = part.model_dump(exclude_none=True)
        assert d == {"type": "text", "text": "Hello", "metadata": {"lang": "en"}}

    def test_deserialization(self):
        part = TextPart.model_validate({"type": "text", "text": "World"})
        assert part.text == "World"


class TestDataPart:
    def test_creation(self):
        part = DataPart(data={"key": "value"})
        assert part.type == "data"
        assert part.data == {"key": "value"}


class TestFilePart:
    def test_creation_with_bytes(self):
        part = FilePart(file=FileWithBytes(name="test.txt", bytes="aGVsbG8="))
        assert part.type == "file"
        assert part.file.bytes == "aGVsbG8="


class TestMessage:
    def test_user_message(self):
        msg = Message(role=MessageRole.USER, parts=[TextPart(text="Hi")])
        assert msg.role == MessageRole.USER
        assert len(msg.parts) == 1
        assert msg.messageId  # auto-generated

    def test_serialization_roundtrip(self):
        msg = Message(role=MessageRole.AGENT, parts=[TextPart(text="Response")])
        d = msg.model_dump(mode="json")
        msg2 = Message.model_validate(d)
        assert msg2.role == MessageRole.AGENT
        assert msg2.parts[0].text == "Response"


class TestTask:
    def test_default_task(self):
        task = Task(status=TaskStatus(state=TaskState.SUBMITTED))
        assert task.id  # auto-generated UUID
        assert task.contextId  # auto-generated
        assert task.status.state == TaskState.SUBMITTED
        assert task.history == []
        assert task.artifacts == []

    def test_task_with_history(self):
        msg = Message(role=MessageRole.USER, parts=[TextPart(text="Do something")])
        task = Task(status=TaskStatus(state=TaskState.SUBMITTED), history=[msg])
        assert len(task.history) == 1

    def test_task_state_coercion(self):
        """TaskStatus should accept a string state."""
        task = Task(status={"state": "working"})
        assert task.status.state == TaskState.WORKING


class TestAgentCard:
    def test_minimal_card(self):
        card = AgentCard(name="Test", description="A test agent", url="http://localhost:8000")
        assert card.name == "Test"
        assert card.version == "1.0.0"
        assert card.protocolVersion == "0.2.5"
        assert card.defaultInputModes == ["text"]

    def test_card_with_skills(self):
        card = AgentCard(
            name="Test",
            description="A test agent",
            url="http://localhost:8000",
            skills=[
                AgentSkill(id="s1", name="Skill 1", description="Does thing 1"),
            ],
        )
        assert len(card.skills) == 1
        assert card.skills[0].id == "s1"

    def test_serialization(self):
        card = AgentCard(name="Test", description="desc", url="http://localhost:8000")
        d = card.model_dump(mode="json", exclude_none=True)
        assert d["name"] == "Test"
        assert "capabilities" in d


class TestArtifact:
    def test_creation(self):
        art = Artifact(name="result", parts=[TextPart(text="Output")])
        assert art.name == "result"
        assert len(art.parts) == 1
        assert art.artifactId  # auto-generated
