"""A2A Gateway service — serves aggregate Agent Card and routes A2A calls."""
import logging
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings

logger = logging.getLogger("a2a.gateway")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="A2A Gateway",
    description="Aggregates Agent Cards and routes A2A protocol calls.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Aggregate Agent Card
# -----------------------------------------------------------------------------
@app.get("/.well-known/agent.json")
async def aggregate_agent_card() -> dict[str, Any]:
    """Return an aggregate Agent Card describing all agents on the platform.

    Real A2A deployments serve one card per agent. This gateway serves a
    directory-style card that lists all available agents and how to reach them.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.agent_registry_url}")
            resp.raise_for_status()
            agents = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not reach agent registry: %s", e)
        agents = []

    return {
        "schema_version": "1.0",
        "name": "A2A Platform Gateway",
        "description": "Aggregate gateway for all agents deployed on the platform.",
        "version": "1.0.0",
        "url": str(settings.public_base_url) if hasattr(settings, "public_base_url") else "http://localhost:8080",
        "protocol_version": "0.3",
        "capabilities": {
            "streaming": False,
            "push_notifications": False,
            "state_transition": False,
        },
        "default_input_modes": ["text"],
        "default_output_modes": ["text"],
        "skills": [
            {
                "id": a["slug"],
                "name": a["name"],
                "description": a["description"],
                "tags": a.get("agent_card", {}).get("tags", []),
            }
            for a in agents
        ],
        "agents": [
            {
                "id": a["id"],
                "name": a["name"],
                "slug": a["slug"],
                "base_url": a["base_url"],
                "card_url": f"{a['base_url']}/.well-known/agent.json" if a.get("base_url") else None,
            }
            for a in agents
        ],
        "authentication": {"schemes": ["bearer"]},
        "provider": {
            "organization": "A2A Platform",
            "url": "http://localhost:3000",
        },
    }


# -----------------------------------------------------------------------------
# Per-agent routing
# -----------------------------------------------------------------------------
@app.get("/agents/{agent_slug}/.well-known/agent.json")
async def route_agent_card(agent_slug: str) -> dict[str, Any]:
    """Forward to a specific agent's Agent Card endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.agent_registry_url}")
            resp.raise_for_status()
            agents = resp.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Registry unavailable: {e}")

    agent = next((a for a in agents if a["slug"] == agent_slug), None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_slug}' not found")
    if not agent.get("base_url"):
        raise HTTPException(status_code=409, detail="Agent not yet deployed")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{agent['base_url']}/.well-known/agent.json")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Agent unreachable: {e}")


# -----------------------------------------------------------------------------
# A2A JSON-RPC forwarding
# -----------------------------------------------------------------------------
@app.post("/agents/{agent_slug}")
async def forward_a2a_call(agent_slug: str, request: Request) -> JSONResponse:
    """Forward an A2A JSON-RPC call to the agent runtime."""
    body = await request.json()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{settings.agent_registry_url}")
            agents = resp.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Registry unavailable: {e}")

    agent = next((a for a in agents if a["slug"] == agent_slug), None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_slug}' not found")
    if not agent.get("base_url"):
        raise HTTPException(status_code=409, detail="Agent not deployed")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{agent['base_url']}/",
                json=body,
                headers={"Content-Type": "application/json"},
            )
            return JSONResponse(status_code=resp.status_code, content=resp.json())
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Agent call failed: {e}")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "a2a-gateway"}


@app.get("/metrics")
async def metrics():
    """Prometheus scrape endpoint."""
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    from fastapi.responses import Response

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
