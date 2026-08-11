"""Invocation model — every agent call is recorded for billing + analytics."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class InvocationStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Invocation(Base):
    """A single invocation of an agent by a user."""

    __tablename__ = "invocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # A2A task id (assigned by the gateway)
    a2a_task_id: Mapped[str | None] = mapped_column(String(128), index=True)

    status: Mapped[InvocationStatus] = mapped_column(
        Enum(InvocationStatus), default=InvocationStatus.PENDING, index=True
    )

    # Request / response payloads (truncated for very large payloads)
    input_message: Mapped[str] = mapped_column(Text, default="")
    output_message: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Latency in milliseconds
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    # Cost in cents (charged to user)
    cost_cents: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    agent = relationship("Agent", back_populates="invocations")
    user = relationship("User", back_populates="invocations")
