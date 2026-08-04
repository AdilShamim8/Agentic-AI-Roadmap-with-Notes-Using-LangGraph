"""
FastAPI backend exposing the multi-agent graph as a simple REST API.

Run with:  uvicorn app.api:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from app.graph import build_graph
from app.llm import is_mock_mode

app = FastAPI(
    title="Customer Support Multi-Agent API",
    description="LangGraph-powered multi-agent customer support system.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# One compiled graph (with its own MemorySaver checkpointer) shared by every request.
# Each conversation is isolated by `thread_id`.
_graph = build_graph()


class ChatRequest(BaseModel):
    message: str = Field(..., description="The customer's message.")
    thread_id: str | None = Field(
        None, description="Conversation/session ID. Omit to start a new conversation."
    )


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    category: str | None
    sentiment: str
    resolved: bool
    ticket_id: str | None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "mock" if is_mock_mode() else "live"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = _graph.invoke({"messages": [HumanMessage(content=req.message)]}, config=config)
    reply = result["messages"][-1]
    reply_text = reply.content if isinstance(reply, AIMessage) else str(reply.content)

    return ChatResponse(
        thread_id=thread_id,
        reply=reply_text,
        category=result.get("category"),
        sentiment=result.get("sentiment", "neutral"),
        resolved=result.get("resolved", False),
        ticket_id=result.get("ticket_id"),
    )


@app.get("/tickets")
def list_tickets() -> list[dict]:
    from core import tickets

    return [t.__dict__ for t in tickets.list_tickets()]
