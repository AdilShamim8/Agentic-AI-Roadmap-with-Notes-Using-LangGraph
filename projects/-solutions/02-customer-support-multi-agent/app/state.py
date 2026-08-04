"""Shared state schema passed between every node in the LangGraph graph."""
from __future__ import annotations

from typing import Annotated, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

Category = Literal["billing", "technical", "order", "general", "escalation"]
Sentiment = Literal["neutral", "frustrated", "angry"]


class AgentState(TypedDict):
    # `add_messages` makes this an append-only, auto-merging message list -
    # each node returns only the *new* messages it wants to add, and
    # LangGraph handles concatenation (and de-duplication by message id).
    messages: Annotated[list[BaseMessage], add_messages]

    customer_id: Optional[str]
    category: Optional[Category]
    sentiment: Sentiment
    resolved: bool
    needs_escalation: bool
    ticket_id: Optional[str]
