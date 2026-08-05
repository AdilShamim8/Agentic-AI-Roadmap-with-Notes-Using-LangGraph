"""`km-ask` / `python scripts/ask.py "your question"` — query the agent."""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from knowledge_manager.agent.graph import ask

console = Console()


def main(question: str | None = None) -> int:
    if not question:
        console.print("[red]Usage:[/red] km-ask \"your question\"")
        return 2

    resp = ask(question)

    console.print(Panel(resp.answer, title="Answer", border_style="cyan"))

    src = Table(title="Sources", show_lines=False)
    src.add_column("#", justify="right", style="cyan")
    src.add_column("title")
    src.add_column("path", style="dim")
    src.add_column("score", justify="right")
    for i, s in enumerate(resp.sources, start=1):
        cited = any(p["citation"] == i for p in resp.provenance)
        marker = "[green]✓[/green]" if cited else " "
        src.add_row(
            f"{marker} {i}",
            s["title"],
            s["path"],
            f"{s['fused_score']:.3f}",
        )
    console.print(src)

    if resp.provenance:
        prov = Table(title="Provenance")
        prov.add_column("cite", justify="right", style="cyan")
        prov.add_column("chunk_id", justify="right")
        prov.add_column("title")
        prov.add_column("path", style="dim")
        for p in resp.provenance:
            prov.add_row(
                f"[{p['citation']}]",
                str(p["chunk_id"]),
                p["title"],
                p["path"],
            )
        console.print(prov)

    console.print(f"\n[dim]elapsed: {resp.elapsed_s:.2f}s[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
