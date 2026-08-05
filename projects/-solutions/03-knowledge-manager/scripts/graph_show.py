"""`km-graph` — print entity graph summary."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from knowledge_manager.storage import graph_store
from knowledge_manager.storage.db import get_conn, init_db

console = Console()


def main() -> int:
    init_db()
    g = graph_store.load_graph()
    console.print(
        f"[cyan]graph[/cyan]: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges"
    )

    nodes_tbl = Table(title="Top entities (by degree)")
    nodes_tbl.add_column("id", justify="right", style="cyan")
    nodes_tbl.add_column("name")
    nodes_tbl.add_column("kind")
    nodes_tbl.add_column("in", justify="right")
    nodes_tbl.add_column("out", justify="right")
    for n, data in sorted(g.nodes(data=True), key=lambda x: g.degree(x[0]), reverse=True)[:25]:
        nodes_tbl.add_row(
            str(n),
            data.get("name", ""),
            data.get("kind", ""),
            str(g.in_degree(n)),
            str(g.out_degree(n)),
        )
    console.print(nodes_tbl)

    edges_tbl = Table(title="Sample edges")
    edges_tbl.add_column("src", style="cyan")
    edges_tbl.add_column("predicate", style="magenta")
    edges_tbl.add_column("dst", style="cyan")
    for u, v, edata in list(g.edges(data=True))[:25]:
        su = g.nodes[u].get("name", u)
        sv = g.nodes[v].get("name", v)
        edges_tbl.add_row(su, edata.get("predicate", ""), sv)
    console.print(edges_tbl)

    with get_conn() as conn:
        (n_docs,) = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        (n_chunks,) = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
    console.print(f"[dim]docs={n_docs} chunks={n_chunks}[/dim]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
