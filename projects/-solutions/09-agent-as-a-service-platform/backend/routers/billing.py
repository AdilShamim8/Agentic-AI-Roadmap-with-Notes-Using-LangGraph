"""Billing router — usage, subscription, checkout, webhook."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import settings
from deps import CurrentUser, DbSession, get_db
from models.billing import BillingEvent, Subscription, SubscriptionPlan, SubscriptionStatus
from models.invocation import Invocation
from models.user import User
from schemas.billing import CheckoutSessionResponse, SubscriptionOut, UsageOut
from services.billing import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
@router.get("/usage", response_model=UsageOut)
async def get_usage(current_user: CurrentUser, db: DbSession) -> UsageOut:
    """Aggregated usage stats for the current user."""
    # Total
    total_invocations = db.scalar(
        select(func.count(Invocation.id)).where(Invocation.user_id == current_user.id)
    ) or 0
    total_cost = db.scalar(
        select(func.coalesce(func.sum(Invocation.cost_cents), 0)).where(
            Invocation.user_id == current_user.id
        )
    )

    # This month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_invocations = db.scalar(
        select(func.count(Invocation.id)).where(
            Invocation.user_id == current_user.id,
            Invocation.created_at >= month_start,
        )
    ) or 0
    month_cost = db.scalar(
        select(func.coalesce(func.sum(Invocation.cost_cents), 0)).where(
            Invocation.user_id == current_user.id,
            Invocation.created_at >= month_start,
        )
    )

    # Subscription
    sub = db.scalar(select(Subscription).where(Subscription.user_id == current_user.id))
    plan = sub.plan.value if sub else SubscriptionPlan.FREE.value
    used = sub.invocations_used if sub else month_invocations
    included = (
        sub.invocations_included
        if sub
        else 100  # free tier monthly cap
    )

    # By agent
    by_agent_stmt = (
        select(
            Invocation.agent_id,
            func.count(Invocation.id).label("count"),
            func.coalesce(func.sum(Invocation.cost_cents), 0).label("cost"),
        )
        .where(Invocation.user_id == current_user.id)
        .group_by(Invocation.agent_id)
    )
    by_agent = [
        {"agent_id": str(r.agent_id), "count": r.count, "cost_cents": int(r.cost)}
        for r in db.execute(by_agent_stmt)
    ]

    # Resolve names
    from models.agent import Agent

    for entry in by_agent:
        a = db.scalar(select(Agent).where(Agent.id == entry["agent_id"]))
        entry["name"] = a.name if a else "deleted"

    return UsageOut(
        total_invocations=int(total_invocations),
        total_cost_cents=int(total_cost or 0),
        invocations_this_month=int(month_invocations),
        cost_this_month_cents=int(month_cost or 0),
        plan=plan,
        invocations_used=int(used),
        invocations_included=int(included),
        by_agent=by_agent,
    )


@router.get("/subscription", response_model=SubscriptionOut | None)
async def get_subscription(current_user: CurrentUser, db: DbSession) -> Subscription | None:
    return db.scalar(select(Subscription).where(Subscription.user_id == current_user.id))


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------
@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout(
    current_user: CurrentUser,
    db: DbSession,
    plan: SubscriptionPlan = SubscriptionPlan.STARTER,
) -> CheckoutSessionResponse:
    """Create a Stripe checkout session for upgrading a subscription.

    Falls back to a mock URL if Stripe is not configured (test mode).
    """
    if not settings.stripe_secret_key:
        # Mock mode — for local dev without Stripe
        return CheckoutSessionResponse(
            checkout_url=f"http://localhost:3000/billing?mock=1&plan={plan.value}&user={current_user.id}",
            session_id=f"mock_session_{current_user.id}_{plan.value}",
        )

    try:
        session = await billing_service.create_checkout_session(
            user=current_user, plan=plan, db=db
        )
        return CheckoutSessionResponse(
            checkout_url=session.url, session_id=session.id
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe checkout failed: {e}",
        )


@router.post("/upgrade")
async def upgrade_plan(
    current_user: CurrentUser,
    db: DbSession,
    plan: SubscriptionPlan = SubscriptionPlan.STARTER,
) -> dict:
    """Mock upgrade endpoint (for dev without Stripe)."""
    included_map = {
        SubscriptionPlan.FREE: 100,
        SubscriptionPlan.STARTER: 1000,
        SubscriptionPlan.PRO: 10000,
        SubscriptionPlan.ENTERPRISE: 100000,
    }
    sub = db.scalar(select(Subscription).where(Subscription.user_id == current_user.id))
    if not sub:
        sub = Subscription(user_id=current_user.id)
        db.add(sub)
    sub.plan = plan
    sub.status = SubscriptionStatus.ACTIVE
    sub.invocations_included = included_map[plan]
    db.commit()
    db.refresh(sub)
    return {"status": "upgraded", "plan": plan.value}


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    """Receive Stripe webhook events (checkout completed, invoice paid, etc.).

    Verifies the signature if STRIPE_WEBHOOK_SECRET is set; otherwise accepts
    the event as-is (dev mode).
    """
    payload = await request.body()

    if settings.stripe_webhook_secret and settings.stripe_secret_key:
        try:
            import stripe

            stripe.api_key = settings.stripe_secret_key
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, settings.stripe_webhook_secret
            )
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")
    else:
        import json

        try:
            event = json.loads(payload)
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        customer_email = data.get("customer_email") or data.get("customer_details", {}).get("email")
        if customer_email:
            user = db.scalar(select(User).where(User.email == customer_email))
            if user:
                sub = db.scalar(
                    select(Subscription).where(Subscription.user_id == user.id)
                )
                if not sub:
                    sub = Subscription(user_id=user.id)
                    db.add(sub)
                sub.stripe_subscription_id = data.get("subscription")
                sub.status = SubscriptionStatus.ACTIVE
                db.commit()

    return {"received": True, "type": event_type}
