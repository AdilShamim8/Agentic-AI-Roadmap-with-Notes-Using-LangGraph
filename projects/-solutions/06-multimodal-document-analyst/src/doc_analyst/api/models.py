"""Pydantic models for the FastAPI request/response surface."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..schemas import Answer, DocSummary


class IngestResponse(BaseModel):
    summary: DocSummary


class IngestManyResponse(BaseModel):
    summaries: list[DocSummary]
    failed: list[dict[str, str]] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str
    doc_ids: list[str] | None = None


class AskResponse(BaseModel):
    answer: Answer


class DeleteResponse(BaseModel):
    doc_id: str
    deleted: bool


class ClearResponse(BaseModel):
    cleared: bool


class HealthResponse(BaseModel):
    status: str = "ok"
    documents: int
    chroma_text_count: int
    chroma_caption_count: int


class DocPageImage(BaseModel):
    page: int
    image_path: str


class DocDetailResponse(BaseModel):
    summary: DocSummary
    pages: list[dict[str, Any]]
