"""Agent model — a deployed A2A-compliant agent on the platform."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AgentStatus(str, enum.Enum):
    """Lifecycle status of a deployed agent."""

    PENDING = "pending"        # uploaded but not yet running
    DEPLOYING = "deploying"    # container starting
    RUNNING = "running"        # healthy and serving
    STOPPED = "stopped"        # manually stopped
    FAILED = "failed"          # deployment failed
    UNDEPLOYED = "undeployed"  # removed


class Agent(Base):
    """A deployed agent owned by a user."""

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(32), default="0.1.0")

    # Docker image / source
    docker_image: Mapped[str] = mapped_column(String(512), nullable=False)
    container_id: Mapped[str | None] = mapped_column(String(128))
    container_port: Mapped[int | None] = mapped_column(Integer)

    # A2A Agent Card (cached) — see docs/A2A_PROTOCOL.md
    agent_card: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Runtime
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.PENDING, index=True
    )
    base_url: Mapped[str | None] = mapped_column(String(512))

    # Pricing (cents per invocation; 0 = free)
    price_per_invocation_cents: Mapped[int] = mapped_column(Integer, default=0)

    # Metrics snapshot (updated periodically by observability service)
    invocations_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0)

    # Ownership
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner = relationship("User", back_populates="agents")
    versions = relationship(
        "AgentVersion", back_populates="agent", cascade="all, delete-orphan"
    )
    ratings = relationship(
        "AgentRating", back_populates="agent", cascade="all, delete-orphan"
    )
    invocations = relationship("Invocation", back_populates="agent")


class AgentVersion(Base):
    """Version history for an agent."""

    __tablename__ = "agent_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    docker_image: Mapped[str] = mapped_column(String(512), nullable=False)
    changelog: Mapped[str] = mapped_column(Text, default="")
    agent_card: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    agent = relationship("Agent", back_populates="versions")


class AgentRating(Base):
    """User ratings for an agent (1-5 stars)."""

    __tablename__ = "agent_ratings"
    __table_args__ = (UniqueConstraint("agent_id", "user_id", name="uq_agent_user_rating"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    review: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    agent = relationship("Agent", back_populates="ratings")
