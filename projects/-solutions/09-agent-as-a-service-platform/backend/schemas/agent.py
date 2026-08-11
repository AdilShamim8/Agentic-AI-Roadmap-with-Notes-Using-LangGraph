"""Agent-related schemas — including the A2A Agent Card."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# =============================================================================
# A2A Agent Card — the protocol-level description of an agent.
# See docs/A2A_PROTOCOL.md
# =============================================================================
class AgentSkill(BaseModel):
    """A capability advertised by an agent."""

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    input_modes: list[str] = Field(default_factory=lambda: ["text"])
    output_modes: list[str] = Field(default_factory=lambda: ["text"])


class AgentCard(BaseModel):
    """The A2A Agent Card served at /.well-known/agent.json."""

    schema_version: str = "1.0"
    name: str
    description: str
    version: str
    url: HttpUrl  # base URL where the agent lives
    protocol_version: str = "0.3"
    capabilities: dict[str, Any] = Field(
        default_factory=lambda: {
            "streaming": False,
            "push_notifications": False,
            "state_transition": False,
        }
    )
    default_input_modes: list[str] = Field(default_factory=lambda: ["text"])
    default_output_modes: list[str] = Field(default_factory=lambda: ["text"])
    skills: list[AgentSkill] = Field(default_factory=list)
    authentication: dict[str, Any] = Field(
        default_factory=lambda: {"schemes": ["bearer"]}
    )
    provider: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# CRUD schemas
# =============================================================================
class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    version: str = "0.1.0"
    docker_image: str = Field(min_length=1, max_length=512)
    price_per_invocation_cents: int = Field(default=0, ge=0)
    skills: list[AgentSkill] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    version: str | None = None
    price_per_invocation_cents: int | None = Field(default=None, ge=0)


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str
    version: str
    docker_image: str
    status: str
    base_url: str | None
    price_per_invocation_cents: int
    invocations_count: int
    avg_rating: float
    agent_card: dict[str, Any]
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class AgentDeployResponse(BaseModel):
    agent: AgentOut
    message: str = "Deployment started. Poll /agents/{id} for status."


# =============================================================================
# Invocation
# =============================================================================
class AgentInvokeRequest(BaseModel):
    """A2A-style task request."""

    message: str = Field(description="User input message for the agent")
    skill_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False  # A2A streaming support


class AgentInvokeResponse(BaseModel):
    invocation_id: UUID
    a2a_task_id: str | None
    status: str
    output: str
    duration_ms: int | None
    cost_cents: int


# =============================================================================
# Ratings
# =============================================================================
class RatingCreate(BaseModel):
    score: int = Field(ge=1, le=5)
    review: str | None = None


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    user_id: UUID
    score: int
    review: str | None
    created_at: datetime
