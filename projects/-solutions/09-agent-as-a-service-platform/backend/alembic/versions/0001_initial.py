"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255)),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean, server_default=sa.text("false")),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("agent_provider_id", sa.String(255), unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # --- agents ---
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("version", sa.String(32), server_default="0.1.0"),
        sa.Column("docker_image", sa.String(512), nullable=False),
        sa.Column("container_id", sa.String(128)),
        sa.Column("container_port", sa.Integer),
        sa.Column("agent_card", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "status",
            sa.Enum("pending", "deploying", "running", "stopped", "failed", "undeployed", name="agentstatus"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("base_url", sa.String(512)),
        sa.Column("price_per_invocation_cents", sa.Integer, server_default="0"),
        sa.Column("invocations_count", sa.Integer, server_default="0"),
        sa.Column("avg_rating", sa.Float, server_default="0.0"),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_agents_slug", "agents", ["slug"])
    op.create_index("ix_agents_status", "agents", ["status"])

    # --- agent_versions ---
    op.create_table(
        "agent_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("docker_image", sa.String(512), nullable=False),
        sa.Column("changelog", sa.Text, server_default=""),
        sa.Column("agent_card", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # --- agent_ratings ---
    op.create_table(
        "agent_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("review", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("agent_id", "user_id", name="uq_agent_user_rating"),
    )

    # --- invocations ---
    op.create_table(
        "invocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("a2a_task_id", sa.String(128)),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", "timeout", name="invocationstatus"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("input_message", sa.Text, server_default=""),
        sa.Column("output_message", sa.Text, server_default=""),
        sa.Column("error", sa.Text),
        sa.Column("metadata", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("cost_cents", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_invocations_a2a_task_id", "invocations", ["a2a_task_id"])
    op.create_index("ix_invocations_status", "invocations", ["status"])
    op.create_index("ix_invocations_created_at", "invocations", ["created_at"])

    # --- subscriptions ---
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan",
            sa.Enum("free", "starter", "pro", "enterprise", name="subscriptionplan"),
            server_default="free",
        ),
        sa.Column(
            "status",
            sa.Enum("active", "past_due", "canceled", "trialing", name="subscriptionstatus"),
            server_default="active",
        ),
        sa.Column("stripe_subscription_id", sa.String(255)),
        sa.Column("invocations_used", sa.Integer, server_default="0"),
        sa.Column("invocations_included", sa.Integer, server_default="100"),
        sa.Column("current_period_start", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # --- billing_events ---
    op.create_table(
        "billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invocation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invocations.id", ondelete="SET NULL"),
        ),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("description", sa.String(255), server_default=""),
        sa.Column("stripe_charge_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_billing_events_created_at", "billing_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("billing_events")
    op.drop_table("subscriptions")
    op.drop_table("invocations")
    op.drop_table("agent_ratings")
    op.drop_table("agent_versions")
    op.drop_table("agents")
    op.drop_table("users")
    sa.Enum(name="agentstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="invocationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="subscriptionplan").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="subscriptionstatus").drop(op.get_bind(), checkfirst=True)
