"""Invocations router — list, get, status."""
import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from deps import CurrentUser, DbSession
from models.invocation import Invocation
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/invocations", tags=["invocations"])


@router.get("")
async def list_invocations(
    current_user: CurrentUser,
    db: DbSession,
    agent_id: uuid.UUID | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> list[dict]:
    """List invocations for the current user."""
    stmt = (
        select(Invocation)
        .options(selectinload(Invocation.agent))
        .where(Invocation.user_id == current_user.id)
        .order_by(Invocation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if agent_id:
        stmt = stmt.where(Invocation.agent_id == agent_id)

    rows = list(db.scalars(stmt))
    return [
        {
            "id": str(r.id),
            "agent_id": str(r.agent_id),
            "agent_name": r.agent.name if r.agent else None,
            "status": r.status.value if r.status else None,
            "a2a_task_id": r.a2a_task_id,
            "input_message": r.input_message[:200],
            "output_message": r.output_message[:500],
            "duration_ms": r.duration_ms,
            "cost_cents": r.cost_cents,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/{invocation_id}")
async def get_invocation(
    invocation_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> dict:
    inv = db.scalar(
        select(Invocation)
        .options(selectinload(Invocation.agent))
        .where(Invocation.id == invocation_id)
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invocation not found")
    if inv.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not your invocation")

    return {
        "id": str(inv.id),
        "agent_id": str(inv.agent_id),
        "agent_name": inv.agent.name if inv.agent else None,
        "status": inv.status.value if inv.status else None,
        "a2a_task_id": inv.a2a_task_id,
        "input_message": inv.input_message,
        "output_message": inv.output_message,
        "error": inv.error,
        "duration_ms": inv.duration_ms,
        "cost_cents": inv.cost_cents,
        "metadata": inv.metadata,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
    }
