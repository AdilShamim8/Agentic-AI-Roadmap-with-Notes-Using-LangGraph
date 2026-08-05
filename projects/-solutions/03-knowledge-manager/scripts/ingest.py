"""`km-ingest` / `python scripts/ingest.py <dir>` — ingest a directory tree."""
from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from knowledge_manager.ingestion.pipeline import ingest_directory

console = Console()


def main(path: str | None = None) -> int:
    target = Path(path) if path else Path("data/ingest")
    if not target.exists():
        console.print(f"[red]Path not found:[/red] {target}")
        return 2

    console.print(f"[cyan]Ingesting[/cyan] {target} ...")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as prog:
        task = prog.add_task("working", total=None)

        def _on(p: str, entry: dict) -> None:
            prog.update(task, description=f"{entry.get('status', '?')} {Path(p).name}")

        report = ingest_directory(target, on_progress=_on)

    tbl = Table(title="Ingestion report")
    tbl.add_column("metric", style="cyan")
    tbl.add_column("value", justify="right")
    tbl.add_row("files ingested", str(report.n_files))
    tbl.add_row("files skipped", str(report.n_skipped))
    tbl.add_row("chunks", str(report.n_chunks))
    tbl.add_row("entities", str(report.n_entities))
    tbl.add_row("relationships", str(report.n_relationships))
    tbl.add_row("elapsed (s)", f"{report.elapsed_s:.2f}")
    console.print(tbl)

    per_file = Table(title="Per-file detail")
    per_file.add_column("path")
    per_file.add_column("status")
    per_file.add_column("chunks", justify="right")
    per_file.add_column("entities", justify="right")
    per_file.add_column("rels", justify="right")
    for e in report.per_file:
        per_file.add_row(
            e.get("path", ""),
            e.get("status", ""),
            str(e.get("n_chunks", "")),
            str(e.get("n_entities", "")),
            str(e.get("n_relationships", "")),
        )
    console.print(per_file)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
