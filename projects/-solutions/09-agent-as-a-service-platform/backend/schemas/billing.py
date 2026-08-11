"""Billing + usage schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UsageOut(BaseModel):
    """Aggregated usage stats for a user."""

    model_config = ConfigDict(from_attributes=True)

    total_invocations: int
    total_cost_cents: int
    invocations_this_month: int
    cost_this_month_cents: int
    plan: str
    invocations_used: int
    invocations_included: int
    by_agent: list[dict]  # [{agent_id, name, count, cost_cents}]


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan: str
    status: str
    invocations_used: int
    invocations_included: int
    current_period_start: datetime | None
    current_period_end: datetime | None


class CheckoutSessionResponse(BaseModel):
    """Stripe checkout session URL."""

    checkout_url: str
    session_id: str
