"""Agents router — browse, deploy, invoke, rate agents."""
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from deps import CurrentUser, DbSession
from models.agent import Agent, AgentRating, AgentStatus
from models.invocation import Invocation, InvocationStatus
from schemas.agent import (
    AgentCard,
    AgentCreate,
    AgentDeployResponse,
    AgentInvokeRequest,
    AgentInvokeResponse,
    AgentOut,
    AgentSkill,
    AgentUpdate,
    RatingCreate,
    RatingOut,
)
from services.agent_runtime import agent_runtime
from services.observability import observability

router = APIRouter(prefix="/agents", tags=["agents"])


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return slug or f"agent-{uuid.uuid4().hex[:8]}"


def _build_agent_card(agent: Agent, base_url: str) -> AgentCard:
    """Construct an A2A Agent Card from an Agent row."""
    return AgentCard(
        name=agent.name,
        description=agent.description,
        version=agent.version,
        url=base_url,
        skills=[AgentSkill(**s) for s in agent.agent_card.get("skills", [])],
        capabilities=agent.agent_card.get(
            "capabilities",
            {"streaming": False, "push_notifications": False, "state_transition": False},
        ),
    )


# ---------------------------------------------------------------------------
# Browse
# ---------------------------------------------------------------------------
@router.get("", response_model=list[AgentOut])
async def list_agents(
    db: DbSession,
    status_filter: AgentStatus | None = Query(default=None, alias="status"),
    q: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> list[Agent]:
    """List all deployed agents, optionally filtered."""
    stmt = select(Agent).options(selectinload(Agent.owner))
    if status_filter:
        stmt = stmt.where(Agent.status == status_filter)
    else:
        stmt = stmt.where(Agent.status == AgentStatus.RUNNING)
    if q:
        stmt = stmt.where(
            Agent.name.ilike(f"%{q}%") | Agent.description.ilike(f"%{q}%")
        )
    stmt = stmt.order_by(Agent.invocations_count.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: uuid.UUID, db: DbSession) -> Agent:
    agent = db.scalar(
        select(Agent).options(selectinload(Agent.owner)).where(Agent.id == agent_id)
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/card", response_model=AgentCard)
async def get_agent_card(agent_id: uuid.UUID, db: DbSession) -> AgentCard:
    """Return the A2A Agent Card for this agent."""
    agent = db.scalar(select(Agent).where(Agent.id == agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.base_url:
        raise HTTPException(status_code=409, detail="Agent not yet deployed")
    return _build_agent_card(agent, agent.base_url)


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
@router.post("", response_model=AgentDeployResponse, status_code=status.HTTP_201_CREATED)
async def deploy_agent(
    payload: AgentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> AgentDeployResponse:
    """Deploy a new agent.

    This kicks off an async deployment via the agent_runtime service.
    """
    slug = _slugify(payload.name)
    # Ensure slug uniqueness
    existing = db.scalar(select(Agent).where(Agent.slug == slug))
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    skills_payload = [s.model_dump() for s in payload.skills]

    agent = Agent(
        name=payload.name,
        slug=slug,
        description=payload.description,
        version=payload.version,
        docker_image=payload.docker_image,
        price_per_invocation_cents=payload.price_per_invocation_cents,
        owner_id=current_user.id,
        status=AgentStatus.PENDING,
        agent_card={"skills": skills_payload, "protocol_version": "0.3"},
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    # Kick off deployment asynchronously (best-effort)
    try:
        await agent_runtime.deploy(agent_id=agent.id, docker_image=agent.docker_image, db=db)
    except Exception as e:  # noqa: BLE001
        # Don't fail the request — deployment happens in background
        agent.status = AgentStatus.FAILED
        agent.agent_card["deploy_error"] = str(e)
        db.commit()

    return AgentDeployResponse(agent=AgentOut.model_validate(agent))


# ---------------------------------------------------------------------------
# Invoke
# ---------------------------------------------------------------------------
@router.post("/{agent_id}/invoke", response_model=AgentInvokeResponse)
async def invoke_agent(
    agent_id: uuid.UUID,
    payload: AgentInvokeRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> AgentInvokeResponse:
    """Invoke an agent via the A2A gateway.

    Records an Invocation row, proxies to the agent runtime, charges the user.
    """
    agent = db.scalar(select(Agent).where(Agent.id == agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.status != AgentStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail=f"Agent is {agent.status.value}, cannot invoke",
        )

    # Record invocation
    invocation = Invocation(
        agent_id=agent.id,
        user_id=current_user.id,
        input_message=payload.message,
        status=InvocationStatus.RUNNING,
        cost_cents=agent.price_per_invocation_cents,
        metadata=payload.metadata,
    )
    db.add(invocation)
    db.commit()
    db.refresh(invocation)

    started_at = datetime.now(timezone.utc)

    try:
        result = await agent_runtime.invoke(
            agent=agent,
            message=payload.message,
            skill_id=payload.skill_id,
            metadata=payload.metadata,
        )

        invocation.output_message = result.output
        invocation.a2a_task_id = result.a2a_task_id
        invocation.status = InvocationStatus.COMPLETED
        invocation.duration_ms = int(
            (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
        )
        invocation.completed_at = datetime.now(timezone.utc)

        # Update agent stats
        agent.invocations_count += 1

        # Billing event
        if invocation.cost_cents > 0:
            from services.billing import billing_service

            await billing_service.record_invocation_charge(
                user_id=current_user.id,
                invocation_id=invocation.id,
                amount_cents=invocation.cost_cents,
                description=f"Invocation of {agent.name}",
                db=db,
            )

        db.commit()

        observability.record_invocation(
            agent_id=str(agent.id),
            duration_ms=invocation.duration_ms or 0,
            status="completed",
        )

        return AgentInvokeResponse(
            invocation_id=invocation.id,
            a2a_task_id=invocation.a2a_task_id,
            status="completed",
            output=result.output,
            duration_ms=invocation.duration_ms,
            cost_cents=invocation.cost_cents,
        )

    except Exception as e:  # noqa: BLE001
        invocation.status = InvocationStatus.FAILED
        invocation.error = str(e)
        invocation.duration_ms = int(
            (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
        )
        invocation.completed_at = datetime.now(timezone.utc)
        db.commit()

        observability.record_invocation(
            agent_id=str(agent.id),
            duration_ms=invocation.duration_ms or 0,
            status="failed",
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent invocation failed: {e}",
        )


# ---------------------------------------------------------------------------
# Update / delete
# ---------------------------------------------------------------------------
@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Agent:
    agent = db.scalar(select(Agent).where(Agent.id == agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not the agent owner")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)

    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    agent = db.scalar(select(Agent).where(Agent.id == agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not the agent owner")

    # Best-effort teardown
    try:
        await agent_runtime.undeploy(agent=agent, db=db)
    except Exception:  # noqa: BLE001
        pass

    db.delete(agent)
    db.commit()


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------
@router.post("/{agent_id}/ratings", response_model=RatingOut, status_code=201)
async def rate_agent(
    agent_id: uuid.UUID,
    payload: RatingCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> AgentRating:
    agent = db.scalar(select(Agent).where(Agent.id == agent_id))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Upsert rating
    rating = db.scalar(
        select(AgentRating).where(
            AgentRating.agent_id == agent_id, AgentRating.user_id == current_user.id
        )
    )
    if rating:
        rating.score = payload.score
        rating.review = payload.review
    else:
        rating = AgentRating(
            agent_id=agent_id,
            user_id=current_user.id,
            score=payload.score,
            review=payload.review,
        )
        db.add(rating)

    db.commit()
    db.refresh(rating)

    # Recompute avg rating
    avg = db.scalar(
        select(func.avg(AgentRating.score)).where(AgentRating.agent_id == agent_id)
    )
    agent.avg_rating = float(avg or 0.0)
    db.commit()

    return rating


@router.get("/{agent_id}/ratings", response_model=list[RatingOut])
async def list_ratings(agent_id: uuid.UUID, db: DbSession) -> list[AgentRating]:
    return list(
        db.scalars(
            select(AgentRating)
            .where(AgentRating.agent_id == agent_id)
            .order_by(AgentRating.created_at.desc())
        )
    )
