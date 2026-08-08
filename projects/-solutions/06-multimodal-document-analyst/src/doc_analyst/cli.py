"""Typer-based command-line interface.

Commands:
  doc-analyst ingest <pdf...>       Ingest one or more PDFs.
  doc-analyst ask <question>        Ask a question against the index.
  doc-analyst list                  List ingested documents.
  doc-analyst clear                 Delete the entire index (data dir stays).
  doc-analyst info <doc_id>         Show details for a single document.
  doc-analyst serve                 Start the FastAPI server.
  doc-analyst web                   Start the Streamlit web UI.
"""
from __future__ import annotations

import asyncio
import json
import sys
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agents.retrieval_agent import ask as agent_ask
from .config import settings
from .storage.doc_registry import get_registry
from .storage.indexer import Indexer
from .storage.vector_store import get_store
from .utils.logging import get_logger

app = typer.Typer(
    name="doc-analyst",
    help="Multimodal Document Analyst — ingest PDFs and ask questions with citations.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
log = get_logger(__name__)


# ----------------------------------------------------------------------
# ingest
# ----------------------------------------------------------------------
@app.command()
def ingest(
    pdfs: list[Path] = typer.Argument(
        ..., help="One or more PDF files to ingest.", exists=True, dir_okay=False
    ),
    no_caption: bool = typer.Option(
        False, "--no-caption", help="Skip VLM captioning (faster, but images will not be searchable)."
    ),
) -> None:
    """Ingest one or more PDFs into the index."""
    indexer = Indexer()
    if no_caption:
        # Stub the VLM so captioning becomes a no-op.
        from .embeddings.vlm import VLMClient

        class _NoopVLM(VLMClient):
            provider = "zai"  # type: ignore[assignment]

            async def caption_image(self, image_path, prompt=None):  # noqa: D401
                return "(captioning skipped)"

            async def chat(self, messages, *, json_mode=False):
                return "{}"

        indexer.vlm = _NoopVLM()

    async def _run() -> None:
        for pdf in pdfs:
            console.print(f"[bold cyan]Ingesting[/] {pdf}...")
            summary = await indexer.ingest_pdf(pdf)
            table = Table(show_header=False, box=None)
            table.add_row("doc_id", summary.doc_id)
            table.add_row("pages", str(summary.n_pages))
            table.add_row(
                "elements",
                f"{summary.n_elements} (text={summary.n_text}, images={summary.n_images}, tables={summary.n_tables})",
            )
            console.print(Panel(table, title=f"Ingested {pdf.name}", expand=False))

    asyncio.run(_run())


# ----------------------------------------------------------------------
# ask
# ----------------------------------------------------------------------
@app.command()
def ask(
    question: str = typer.Argument(..., help="The question to ask."),
    doc_id: Optional[list[str]] = typer.Option(
        None, "--doc", "-d", help="Restrict to a doc_id (can be repeated)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit the answer as JSON."),
) -> None:
    """Ask a question against the indexed corpus."""
    answer = asyncio.run(agent_ask(question, doc_ids=doc_id or None))

    if json_out:
        console.print_json(json.dumps(answer.model_dump(mode="json"), indent=2))
        return

    console.print(
        Panel(
            f"[bold]Q:[/] {question}\n\n{answer.summary}",
            title=f"Answer  ·  confidence={answer.confidence:.0%}  ·  {answer.latency_ms:.0f} ms",
            expand=False,
        )
    )

    if answer.blocks:
        blocks_tbl = Table(title="Claims", show_lines=True)
        blocks_tbl.add_column("#", style="dim", width=3)
        blocks_tbl.add_column("Claim", overflow="fold")
        blocks_tbl.add_column("Citations", overflow="fold")
        for i, blk in enumerate(answer.blocks, 1):
            cites = "\n".join(
                f"[{c.doc_id}::p{c.page}·e{c.element_index}] ({c.element_type.value}/{c.source})"
                + (f"\n  “{c.snippet[:80]}{'...' if len(c.snippet)>80 else ''}”" if c.snippet else "")
                for c in blk.citations
            )
            blocks_tbl.add_row(str(i), blk.claim, cites)
        console.print(blocks_tbl)


# ----------------------------------------------------------------------
# list
# ----------------------------------------------------------------------
@app.command(name="list")
def list_docs() -> None:
    """List ingested documents."""
    registry = get_registry()
    docs = registry.list()
    if not docs:
        console.print("[yellow]No documents ingested yet.[/]")
        return
    tbl = Table(title="Ingested documents")
    tbl.add_column("doc_id", style="cyan")
    tbl.add_column("source", overflow="fold")
    tbl.add_column("pages", justify="right")
    tbl.add_column("elements", justify="right")
    tbl.add_column("text/img/tbl")
    tbl.add_column("ingested_at")
    for d in docs:
        tbl.add_row(
            d.doc_id,
            d.source,
            str(d.n_pages),
            str(d.n_elements),
            f"{d.n_text}/{d.n_images}/{d.n_tables}",
            d.ingested_at.replace("T", " ").split(".")[0],
        )
    console.print(tbl)


# ----------------------------------------------------------------------
# info
# ----------------------------------------------------------------------
@app.command()
def info(doc_id: str) -> None:
    """Show details for a single document."""
    registry = get_registry()
    summary = registry.get(doc_id)
    if not summary:
        console.print(f"[red]No such doc_id:[/] {doc_id}")
        raise typer.Exit(1)
    store = get_store()
    counts = store.count_for_doc(doc_id)
    console.print(
        Panel(
            f"doc_id: {summary.doc_id}\n"
            f"source: {summary.source}\n"
            f"pages:  {summary.n_pages}\n"
            f"elements: {summary.n_elements} (text={summary.n_text}, "
            f"images={summary.n_images}, tables={summary.n_tables})\n"
            f"indexed rows: text={counts.get('text', 0)}, captions={counts.get('captions', 0)}\n"
            f"ingested_at: {summary.ingested_at}",
            title="Document info",
            expand=False,
        )
    )


# ----------------------------------------------------------------------
# clear / delete
# ----------------------------------------------------------------------
@app.command()
def clear(
    yes: bool = typer.Option(False, "--yes", "-y", help="Don't ask for confirmation."),
) -> None:
    """Delete the entire index (cache + Chroma + registry)."""
    if not yes:
        if not typer.confirm("This will delete ALL ingested documents. Continue?", default=False):
            raise typer.Abort()
    import shutil

    # Clear Chroma collections.
    store = get_store()
    try:
        store._client.delete_collection(settings.chroma_text_collection)
        store._client.delete_collection(settings.chroma_caption_collection)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not delete collections: %s", exc)

    # Clear caches.
    if settings.pdf_cache_path.exists():
        shutil.rmtree(settings.pdf_cache_path)
    settings.pdf_cache_path.mkdir(parents=True, exist_ok=True)
    if settings.page_images_path.exists():
        shutil.rmtree(settings.page_images_path)
    settings.page_images_path.mkdir(parents=True, exist_ok=True)

    # Clear registry.
    if settings.sqlite_path.exists():
        settings.sqlite_path.unlink()

    console.print("[green]Index cleared.[/]")


@app.command()
def delete(doc_id: str) -> None:
    """Delete a single document from the index."""
    indexer = Indexer()
    if indexer.delete_doc(doc_id):
        console.print(f"[green]Deleted[/] {doc_id}")
    else:
        console.print(f"[yellow]Not found:[/] {doc_id}")


# ----------------------------------------------------------------------
# serve (FastAPI)
# ----------------------------------------------------------------------
@app.command()
def serve(
    host: str = typer.Option(None, "--host", help="Bind host (default from settings)."),
    port: int = typer.Option(None, "--port", help="Bind port (default from settings)."),
    reload: bool = typer.Option(False, "--reload", help="Enable uvicorn reload (dev)."),
) -> None:
    """Start the FastAPI server."""
    import uvicorn

    host = host or settings.api_host
    port = port or settings.api_port
    uvicorn.run(
        "doc_analyst.api.server:app",
        host=host,
        port=port,
        reload=reload,
    )


# ----------------------------------------------------------------------
# web (Streamlit)
# ----------------------------------------------------------------------
@app.command()
def web(
    port: int = typer.Option(8501, "--port", help="Streamlit port."),
    browser: bool = typer.Option(True, "--no-browser", help="Don't open a browser tab."),
) -> None:
    """Start the Streamlit web UI."""
    import subprocess

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(Path(__file__).parent / "ui" / "app.py"),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    if browser:
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:  # noqa: BLE001
            pass
    subprocess.run(cmd, check=False)


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()
