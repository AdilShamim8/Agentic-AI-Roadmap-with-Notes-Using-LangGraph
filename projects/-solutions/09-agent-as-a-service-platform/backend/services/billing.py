"""Billing service — Stripe integration + per-invocation accounting."""
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from models.billing import BillingEvent, Subscription, SubscriptionPlan, SubscriptionStatus
from models.user import User

logger = logging.getLogger(__name__)


PLAN_TO_STRIPE_PRICE = {
    SubscriptionPlan.STARTER: "price_starter",
    SubscriptionPlan.PRO: "price_pro",
    SubscriptionPlan.ENTERPRISE: "price_enterprise",
}

PLAN_INVOCATIONS = {
    SubscriptionPlan.FREE: 100,
    SubscriptionPlan.STARTER: 1000,
    SubscriptionPlan.PRO: 10000,
    SubscriptionPlan.ENTERPRISE: 100000,
}


class BillingService:
    """Handles Stripe checkout sessions, subscription sync, and per-invocation
    billing events."""

    def __init__(self) -> None:
        self._stripe = None
        if settings.stripe_secret_key:
            try:
                import stripe

                stripe.api_key = settings.stripe_secret_key
                self._stripe = stripe
            except Exception as e:  # noqa: BLE001
                logger.warning("Stripe not available: %s", e)

    # -----------------------------------------------------------------
    # Customer / subscription lifecycle
    # -----------------------------------------------------------------
    async def ensure_stripe_customer(self, user: User, db: Session) -> str | None:
        """Create a Stripe customer for the user if not already present."""
        if not self._stripe:
            return None
        if user.stripe_customer_id:
            return user.stripe_customer_id
        try:
            customer = self._stripe.Customer.create(
                email=user.email,
                name=user.full_name or user.username,
                metadata={"user_id": str(user.id)},
            )
            user.stripe_customer_id = customer.id
            db.commit()
            return customer.id
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to create Stripe customer: %s", e)
            return None

    async def create_checkout_session(
        self, user: User, plan: SubscriptionPlan, db: Session
    ) -> Any:
        """Create a Stripe Checkout session for upgrading to `plan`."""
        if not self._stripe:
            raise RuntimeError("Stripe not configured")

        customer_id = await self.ensure_stripe_customer(user, db)
        session = self._stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": PLAN_TO_STRIPE_PRICE[plan], "quantity": 1}],
            success_url=f"{settings.cors_origins.split(',')[0]}/billing?success=1",
            cancel_url=f"{settings.cors_origins.split(',')[0]}/billing?canceled=1",
            metadata={"user_id": str(user.id), "plan": plan.value},
        )
        return session

    # -----------------------------------------------------------------
    # Per-invocation billing
    # -----------------------------------------------------------------
    async def record_invocation_charge(
        self,
        user_id: uuid.UUID,
        invocation_id: uuid.UUID,
        amount_cents: int,
        description: str,
        db: Session,
    ) -> BillingEvent:
        """Record a per-invocation charge.

        Increments the user's subscription invocations_used counter, and if
        they exceed the included amount, records an overage billing event.
        """
        event = BillingEvent(
            user_id=user_id,
            invocation_id=invocation_id,
            amount_cents=amount_cents,
            description=description,
        )
        db.add(event)

        # Update subscription counter
        sub = db.scalar(select(Subscription).where(Subscription.user_id == user_id))
        if sub:
            sub.invocations_used += 1
            # If they're on free tier and over the limit, mark as past_due
            if (
                sub.plan == SubscriptionPlan.FREE
                and sub.invocations_used > sub.invocations_included
            ):
                sub.status = SubscriptionStatus.PAST_DUE

        db.commit()
        db.refresh(event)
        return event


billing_service = BillingService()
