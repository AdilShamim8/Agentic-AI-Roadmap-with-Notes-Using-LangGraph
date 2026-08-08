"""FastAPI server exposing ingest / ask / list / delete endpoints."""
from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..agents.retrieval_agent import ask as agent_ask
from ..config import settings
from ..ingest.pdf_ingester import PDFIngester
from ..storage.doc_registry import get_registry
from ..storage.indexer import Indexer
from ..storage.vector_store import get_store
from ..utils.logging import get_logger
from .models import (
    AskRequest,
    AskResponse,
    ClearResponse,
    DeleteResponse,
    DocDetailResponse,
    HealthResponse,
    IngestManyResponse,
    IngestResponse,
)

log = get_logger(__name__)

app = FastAPI(
    title="Multimodal Document Analyst",
    version="0.1.0",
    description="Ingest PDFs (text + images + tables) and answer questions with element-level citations.",
)

# CORS — the Streamlit UI runs on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files: served page PNGs (used by the UI to show cited pages).
app.mount("/static", StaticFiles(directory=str(settings.page_images_path)), name="static")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    registry = get_registry()
    store = get_store()
    text_n = store._text_col.count()
    cap_n = store._caption_col.count()
    return HealthResponse(
        documents=len(registry.list()),
        chroma_text_count=text_n,
        chroma_caption_count=cap_n,
    )


@app.get("/documents")
def list_documents() -> list[dict]:
    return [d.model_dump(mode="json") for d in get_registry().list()]


@app.get("/documents/{doc_id}", response_model=DocDetailResponse)
def document_detail(doc_id: str) -> DocDetailResponse:
    registry = get_registry()
    summary = registry.get(doc_id)
    if not summary:
        raise HTTPException(404, f"doc_id not found: {doc_id}")
    ingester = PDFIngester()
    cached = ingester.load_cached(doc_id)
    pages = []
    if cached:
        for p in cached[1]:
            pages.append(
                {
                    "page": p.page,
                    "width": p.width,
                    "height": p.height,
                    "page_image_url": f"/static/{Path(p.page_image_path).name}" if p.page_image_path else None,
                    "elements": [e.model_dump(mode="json") for e in p.elements],
                }
            )
    return DocDetailResponse(summary=summary, pages=pages)


@app.post("/ingest", response_model=IngestResponse)
async def ingest_upload(file: UploadFile = File(...)) -> IngestResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")
    tmp = Path(tempfile.mkdtemp()) / file.filename
    try:
        with tmp.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        indexer = Indexer()
        summary = await indexer.ingest_pdf(tmp)
        return IngestResponse(summary=summary)
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


@app.post("/ingest_many", response_model=IngestManyResponse)
async def ingest_many_upload(files: list[UploadFile] = File(...)) -> IngestManyResponse:
    summaries: list = []
    failed: list[dict[str, str]] = []
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            failed.append({"file": f.filename or "?", "error": "not a PDF"})
            continue
        tmp = Path(tempfile.mkdtemp()) / f.filename
        try:
            with tmp.open("wb") as fh:
                shutil.copyfileobj(f.file, fh)
            indexer = Indexer()
            summaries.append(await indexer.ingest_pdf(tmp))
        except Exception as exc:  # noqa: BLE001
            failed.append({"file": f.filename, "error": str(exc)})
        finally:
            shutil.rmtree(tmp.parent, ignore_errors=True)
    return IngestManyResponse(summaries=summaries, failed=failed)


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(req: AskRequest) -> AskResponse:
    answer = await agent_ask(req.question, doc_ids=req.doc_ids)
    return AskResponse(answer=answer)


@app.delete("/documents/{doc_id}", response_model=DeleteResponse)
def delete_doc(doc_id: str) -> DeleteResponse:
    indexer = Indexer()
    deleted = indexer.delete_doc(doc_id)
    return DeleteResponse(doc_id=doc_id, deleted=deleted)


@app.post("/clear", response_model=ClearResponse)
def clear_index() -> ClearResponse:
    """Clear everything: Chroma collections, caches, registry."""
    store = get_store()
    try:
        store._client.delete_collection(settings.chroma_text_collection)
        store._client.delete_collection(settings.chroma_caption_collection)
    except Exception as exc:  # noqa: BLE001
        log.warning("clear: could not delete collections: %s", exc)
    if settings.pdf_cache_path.exists():
        shutil.rmtree(settings.pdf_cache_path)
        settings.pdf_cache_path.mkdir(parents=True, exist_ok=True)
    if settings.page_images_path.exists():
        shutil.rmtree(settings.page_images_path)
        settings.page_images_path.mkdir(parents=True, exist_ok=True)
    if settings.sqlite_path.exists():
        settings.sqlite_path.unlink()
    # Re-create collections by re-opening the store.
    from ..storage.vector_store import reset_store

    reset_store()
    _ = get_store()
    return ClearResponse(cleared=True)


@app.get("/citations/{doc_id}/page/{page}/image")
def page_image(doc_id: str, page: int) -> FileResponse:
    """Return the rendered PNG of a single page."""
    path = settings.page_images_path / f"{doc_id}_p{page}.png"
    if not path.exists():
        raise HTTPException(404, "page image not found")
    return FileResponse(str(path), media_type="image/png")


@app.get("/citations/{doc_id}/page/{page}/element/{element_index}/image")
def element_image(doc_id: str, page: int, element_index: int) -> FileResponse:
    """Return the extracted image for an image element."""
    ingester = PDFIngester()
    cached = ingester.load_cached(doc_id)
    if not cached:
        raise HTTPException(404, "doc not found")
    for p in cached[1]:
        if p.page != page:
            continue
        for el in p.elements:
            if el.element_index == element_index and el.image_path:
                return FileResponse(el.image_path, media_type="image/png")
    raise HTTPException(404, "element not found or not an image")


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        {
            "service": "Multimodal Document Analyst",
            "docs": "/docs",
            "health": "/health",
        }
    )
