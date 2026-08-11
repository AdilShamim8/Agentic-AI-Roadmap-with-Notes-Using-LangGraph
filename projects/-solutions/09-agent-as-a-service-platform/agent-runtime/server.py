"""Sample A2A-compliant agent runtime.

Implements the A2A v0.3 protocol:
- GET  /.well-known/agent.json   — Agent Card
- POST /                          — JSON-RPC: tasks/send, tasks/get, tasks/cancel
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest, Histogram

from agents.researcher import researcher_agent
from agents.coder import coder_agent
from agents.summarizer import summarizer_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("a2a.agent")

app = FastAPI(title="A2A Agent Runtime", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
INVOCATIONS = Counter("agent_invocations_total", "Total invocations", ["skill"])
LATENCY = Histogram(
    "agent_invocation_duration_ms",
    "Invocation latency (ms)",
    ["skill"],
    buckets=(50, 100, 250, 500, 1000, 2500, 5000),
)

# In-memory task store (a real impl would use Postgres or Redis)
TASKS: dict[str, dict[str, Any]] = {}


# -----------------------------------------------------------------------------
# Agent Card — A2A protocol
# -----------------------------------------------------------------------------
AGENT_CARD: dict[str, Any] = {
    "schema_version": "1.0",
    "name": "Sample Research Agent",
    "description": (
        "A multi-skill agent that can research topics, write code, and "
        "summarize text. Demonstrates A2A protocol compliance."
    ),
    "version": "1.0.0",
    "url": "http://localhost:8081",
    "protocol_version": "0.3",
    "capabilities": {
        "streaming": False,
        "push_notifications": False,
        "state_transition": True,
    },
    "default_input_modes": ["text"],
    "default_output_modes": ["text"],
    "skills": [
        {
            "id": "researcher",
            "name": "Researcher",
            "description": "Answers factual questions using a knowledge base.",
            "tags": ["research", "qa"],
            "input_modes": ["text"],
            "output_modes": ["text"],
        },
        {
            "id": "coder",
            "name": "Coder",
            "description": "Writes and explains Python code snippets.",
            "tags": ["code", "python"],
            "input_modes": ["text"],
            "output_modes": ["text"],
        },
        {
            "id": "summarizer",
            "name": "Summarizer",
            "description": "Summarizes long text into bullet points.",
            "tags": ["summarize", "nlp"],
            "input_modes": ["text"],
            "output_modes": ["text"],
        },
    ],
    "authentication": {"schemes": ["bearer"]},
    "provider": {
        "organization": "A2A Platform Samples",
        "url": "http://localhost:3000",
    },
}


@app.get("/.well-known/agent.json")
async def agent_card() -> dict[str, Any]:
    """Serve the A2A Agent Card."""
    return AGENT_CARD


# -----------------------------------------------------------------------------
# A2A JSON-RPC entrypoint
# -----------------------------------------------------------------------------
@app.post("/")
async def a2a_rpc(request: Request) -> JSONResponse:
    """Handle A2A JSON-RPC calls.

    Methods:
    - tasks/send     — start a new task synchronously
    - tasks/get      — fetch a task by id
    - tasks/cancel   — cancel a running task
    """
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    rpc_id = body.get("id")

    if method == "tasks/send":
        return await _handle_send(params, rpc_id)
    elif method == "tasks/get":
        return await _handle_get(params, rpc_id)
    elif method == "tasks/cancel":
        return await _handle_cancel(params, rpc_id)
    else:
        return _error(rpc_id, -32601, f"Method not found: {method}")


# -----------------------------------------------------------------------------
# Task handlers
# -----------------------------------------------------------------------------
async def _handle_send(params: dict, rpc_id: Any) -> JSONResponse:
    task_id = params.get("id") or str(uuid.uuid4())
    message = params.get("message", {})
    metadata = params.get("metadata", {}) or {}
    skill_id = metadata.get("skill_id", "researcher")

    # Extract text from message parts
    text_parts = [
        p.get("text", "")
        for p in message.get("parts", [])
        if p.get("type") == "text"
    ]
    input_text = "\n".join(text_parts) or "(empty input)"

    # Route to the right skill
    import time
    started = time.monotonic()
    try:
        if skill_id == "researcher":
            output = await researcher_agent.handle(input_text)
        elif skill_id == "coder":
            output = await coder_agent.handle(input_text)
        elif skill_id == "summarizer":
            output = await summarizer_agent.handle(input_text)
        else:
            return _error(rpc_id, -32602, f"Unknown skill: {skill_id}")
    except Exception as e:  # noqa: BLE001
        return _error(rpc_id, -32603, f"Agent error: {e}")

    duration_ms = int((time.monotonic() - started) * 1000)
    INVOCATIONS.labels(skill=skill_id).inc()
    LATENCY.labels(skill=skill_id).observe(duration_ms)

    task = {
        "id": task_id,
        "status": {"state": "completed"},
        "messages": [
            message,
            {
                "role": "agent",
                "parts": [{"type": "text", "text": output}],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ],
        "artifacts": [],
        "metadata": {"duration_ms": duration_ms, "skill_id": skill_id},
    }
    TASKS[task_id] = task

    return _result(rpc_id, task)


async def _handle_get(params: dict, rpc_id: Any) -> JSONResponse:
    task_id = params.get("id")
    if not task_id or task_id not in TASKS:
        return _error(rpc_id, -32602, f"Task not found: {task_id}")
    return _result(rpc_id, TASKS[task_id])


async def _handle_cancel(params: dict, rpc_id: Any) -> JSONResponse:
    task_id = params.get("id")
    if task_id and task_id in TASKS:
        TASKS[task_id]["status"] = {"state": "canceled"}
    return _result(rpc_id, {"id": task_id, "status": {"state": "canceled"}})


def _result(rpc_id: Any, result: Any) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})


def _error(rpc_id: Any, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}},
        status_code=200,  # JSON-RPC errors return 200 with error body
    )


# -----------------------------------------------------------------------------
# Health & metrics
# -----------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "agent-runtime", "skills": list(AGENTS.keys())}


@app.get("/metrics")
async def metrics():
    from fastapi.responses import Response

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


AGENTS = {
    "researcher": researcher_agent,
    "coder": coder_agent,
    "summarizer": summarizer_agent,
}
