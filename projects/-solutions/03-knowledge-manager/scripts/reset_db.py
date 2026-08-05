"""`km-reset` — wipe the local SQLite DB + graph pickle (irreversible)."""
from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console

from knowledge_manager.config import get_settings
from knowledge_manager.storage.db import wipe

console = Console()


def main(confirm: bool = False) -> int:
    s = get_settings()
    if not confirm:
        console.print(
            f"[yellow]This will delete[/yellow] {s.db_path} and {s.graph_path}."
        )
        console.print("Re-run with --yes to confirm.")
        return 1
    wipe(s.db_path)
    if s.graph_path.exists():
        s.graph_path.unlink()
    console.print("[green]OK[/green] DB wiped and graph pickle removed.")
    return 0


if __name__ == "__main__":
    confirm = "--yes" in sys.argv
    sys.exit(main(confirm=confirm))
