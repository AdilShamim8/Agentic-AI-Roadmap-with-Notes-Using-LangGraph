"""Internal router — used by the A2A gateway to look up agents."""
import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from deps import DbSession
from models.agent import Agent, AgentStatus

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/agents")
async def list_internal_agents(db: DbSession) -> list[dict]:
    """Return all running agents with their base URLs — used by the A2A gateway
    to build the aggregate Agent Card and route requests.
    """
    rows = db.scalars(
        select(Agent).where(Agent.status == AgentStatus.RUNNING)
    )
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "slug": a.slug,
            "version": a.version,
            "description": a.description,
            "base_url": a.base_url,
            "agent_card": a.agent_card,
            "price_per_invocation_cents": a.price_per_invocation_cents,
        }
        for a in rows
    ]


@router.get("/agents/{agent_id}")
async def get_internal_agent(agent_id: uuid.UUID, db: DbSession) -> dict:
    a = db.scalar(select(Agent).where(Agent.id == agent_id))
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "id": str(a.id),
        "name": a.name,
        "slug": a.slug,
        "version": a.version,
        "description": a.description,
        "base_url": a.base_url,
        "agent_card": a.agent_card,
        "status": a.status.value,
    }


@router.patch("/agents/{agent_id}/status")
async def update_agent_status(
    agent_id: uuid.UUID, payload: dict, db: DbSession
) -> dict:
    """Used by the agent_runtime service to update status after deploy."""
    a = db.scalar(select(Agent).where(Agent.id == agent_id))
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")

    if "status" in payload:
        try:
            a.status = AgentStatus(payload["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {payload['status']}")
    if "base_url" in payload:
        a.base_url = payload["base_url"]
    if "container_id" in payload:
        a.container_id = payload["container_id"]
    if "container_port" in payload:
        a.container_port = payload["container_port"]

    db.commit()
    return {"ok": True}
