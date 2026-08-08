"""Pydantic schemas shared across the pipeline."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# Ingestion
# ----------------------------------------------------------------------
class ElementType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"


class DocElement(BaseModel):
    """A single element on a page (text block / image / table)."""

    element_id: str = Field(..., description="Stable id like 'doc::p3::e2'")
    doc_id: str
    page: int = Field(..., ge=1)
    element_index: int = Field(..., ge=0, description="0-based index within the page")
    type: ElementType
    text: str = ""
    image_path: str | None = None
    caption: str | None = None
    table: list[list[str]] | None = None
    bbox: tuple[float, float, float, float] | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class DocPage(BaseModel):
    """A page with all its extracted elements."""

    doc_id: str
    page: int
    width: float
    height: float
    elements: list[DocElement]
    page_image_path: str | None = None


class DocSummary(BaseModel):
    """Document-level summary returned by the ingester."""

    doc_id: str
    source: str
    n_pages: int
    n_elements: int
    n_text: int
    n_images: int
    n_tables: int
    ingested_at: str


# ----------------------------------------------------------------------
# Retrieval
# ----------------------------------------------------------------------
class RetrievedElement(BaseModel):
    """An element retrieved from the index."""

    element: DocElement
    score: float
    source: Literal["text", "caption", "table"]


# ----------------------------------------------------------------------
# Final answer
# ----------------------------------------------------------------------
class Citation(BaseModel):
    """A pointer back to a specific page + element in a source document."""

    doc_id: str
    page: int
    element_index: int
    element_type: ElementType
    snippet: str = Field("", description="Short text excerpt used as evidence")
    source: Literal["text", "caption", "table"] = "text"


class AnswerBlock(BaseModel):
    """A single claim in the final answer, with its citations."""

    claim: str
    citations: list[Citation] = Field(default_factory=list)


class Answer(BaseModel):
    """Structured final answer."""

    question: str
    summary: str
    blocks: list[AnswerBlock]
    citations: list[Citation]
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    latency_ms: float = 0.0
