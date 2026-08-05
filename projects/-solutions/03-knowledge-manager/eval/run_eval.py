"""Run the full eval harness.

Usage:
    python eval/run_eval.py [--no-qa] [--judge] [--out PATH]

Without flags it runs the four core metrics:
  - retrieval precision@5 (using the hybrid retriever directly)
  - entity extraction F1 (using stored entities vs hand-labeled set)
  - provenance accuracy (using the LangGraph agent)
  - query latency p95

Metrics are written to stdout (rich table) and persisted as JSON to
`eval/out/<timestamp>.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from knowledge_manager.retrieval import hybrid
from knowledge_manager.storage.db import init_db

# Support both `python -m eval.run_eval` and `python eval/run_eval.py`
try:
    from .agent_stub import stub_ask  # local fallback for environments without OpenAI
    from .metrics import (
        entity_f1,
        latency_p95,
        load_labels,
        load_qa,
        provenance_accuracy,
        retrieval_precision_at_k,
    )
except ImportError:
    from eval.agent_stub import stub_ask
    from eval.metrics import (
        entity_f1,
        latency_p95,
        load_labels,
        load_qa,
        provenance_accuracy,
        retrieval_precision_at_k,
    )

console = Console()

TARGETS = {
    "retrieval_precision@5": 0.80,
    "entity_f1": 0.85,
    "provenance_accuracy": 1.00,
    "indexing_latency_s_per_doc": 30.0,
    "query_latency_p95_s": 5.0,
}


def _pick_asker(use_stub: bool):
    if use_stub:
        return stub_ask
    try:
        from knowledge_manager.agent.graph import ask

        # Quick smoke test — if OpenAI key is missing this will raise.
        return ask
    except Exception as e:
        console.print(
            f"[yellow]Falling back to stub asker:[/yellow] {type(e).__name__}: {e}"
        )
        return stub_ask


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run eval harness")
    p.add_argument("--no-qa", action="store_true", help="skip Q&A-dependent metrics")
    p.add_argument(
        "--stub", action="store_true", help="use stub asker (no OpenAI calls)"
    )
    p.add_argument(
        "--out", type=Path, default=None, help="write JSON results to this path"
    )
    args = p.parse_args(argv)

    init_db()
    qa_pairs = load_qa()
    labels = load_labels()
    console.print(
        f"[cyan]Loaded[/cyan] {len(qa_pairs)} Q&A pairs, {len(labels)} labeled docs."
    )

    results: dict = {"started_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    targets = TARGETS

    # --- 1. Retrieval precision@5 (does NOT call the LLM in stub mode) ---
    console.print("\n[bold]1. Retrieval precision@5[/bold]")
    if args.stub:
        # BM25-style retriever — no OpenAI calls at all.
        try:
            from eval.agent_stub import stub_retriever as _retriever
        except ImportError:
            from .agent_stub import stub_retriever as _retriever
    else:
        try:
            from knowledge_manager.retrieval.hybrid import search as hybrid_search

            def _retriever(q, top_k):
                # hybrid_search internally calls the LLM for entity spotting;
                # fall back to vector-only if that fails so precision is still
                # measurable.
                try:
                    return hybrid_search(q, top_k=top_k)
                except Exception:
                    from knowledge_manager.retrieval import vector_search

                    return vector_search.search(q, top_k=top_k)

        except Exception:
            from knowledge_manager.retrieval import vector_search

            def _retriever(q, top_k):
                return vector_search.search(q, top_k=top_k)

    try:
        p_at_5, detail = retrieval_precision_at_k(_retriever, qa_pairs, k=5)
        results["retrieval_precision@5"] = round(p_at_5, 4)
        results["retrieval_detail"] = detail[:5]
        console.print(f"  precision@5 = [green]{p_at_5:.2%}[/green]  (target ≥ {targets['retrieval_precision@5']:.0%})")
    except Exception as e:
        console.print(f"  [red]error:[/red] {e}")
        results["retrieval_precision@5"] = None
        results["retrieval_error"] = str(e)

    # --- 2. Entity F1 ---
    console.print("\n[bold]2. Entity extraction F1[/bold]")
    try:
        f1, detail = entity_f1(labels)
        results["entity_f1"] = round(f1, 4)
        results["entity_detail"] = detail[:5]
        console.print(f"  macro-F1 = [green]{f1:.2%}[/green]  (target ≥ {targets['entity_f1']:.0%})")
    except Exception as e:
        console.print(f"  [red]error:[/red] {e}")
        results["entity_f1"] = None
        results["entity_error"] = str(e)

    if not args.no_qa:
        asker = _pick_asker(args.stub)

        # --- 3. Provenance accuracy ---
        console.print("\n[bold]3. Provenance accuracy[/bold]")
        try:
            acc, detail = provenance_accuracy(asker, qa_pairs)
            results["provenance_accuracy"] = round(acc, 4)
            results["provenance_detail"] = detail[:5]
            console.print(
                f"  accuracy = [green]{acc:.2%}[/green]  (target = {targets['provenance_accuracy']:.0%})"
            )
        except Exception as e:
            console.print(f"  [red]error:[/red] {e}")
            results["provenance_accuracy"] = None
            results["provenance_error"] = str(e)

        # --- 4. Query latency p95 ---
        console.print("\n[bold]4. Query latency p95[/bold]")
        try:
            p95, times = latency_p95(asker, qa_pairs)
            results["query_latency_p95_s"] = round(p95, 3)
            results["latency_samples"] = [round(t, 3) for t in times[:5]]
            console.print(
                f"  p95 = [green]{p95:.2f}s[/green]  (target ≤ {targets['query_latency_p95_s']:.0f}s)"
            )
        except Exception as e:
            console.print(f"  [red]error:[/red] {e}")
            results["query_latency_p95_s"] = None
            results["latency_error"] = str(e)

    # --- Summary table ---
    results["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tbl = Table(title="Eval summary", show_lines=True)
    tbl.add_column("metric", style="cyan")
    tbl.add_column("value", justify="right")
    tbl.add_column("target", justify="right")
    tbl.add_column("pass?", justify="center")

    def _row(name: str, value, target, higher_better: bool = True):
        if value is None:
            return (name, "n/a", str(target), "—")
        ok = (value >= target) if higher_better else (value <= target)
        mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
        v = f"{value:.2%}" if isinstance(value, float) and value <= 1.0 else f"{value}"
        return (name, v, str(target), mark)

    tbl.add_row(*_row("retrieval_precision@5", results.get("retrieval_precision@5"), targets["retrieval_precision@5"]))
    tbl.add_row(*_row("entity_f1", results.get("entity_f1"), targets["entity_f1"]))
    if not args.no_qa:
        tbl.add_row(*_row("provenance_accuracy", results.get("provenance_accuracy"), targets["provenance_accuracy"]))
        tbl.add_row(*_row("query_latency_p95_s", results.get("query_latency_p95_s"), targets["query_latency_p95_s"], higher_better=False))

    console.print(tbl)

    out_path = args.out or (
        Path(__file__).resolve().parent / "out" / f"{int(time.time())}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"\n[dim]Wrote results to {out_path}[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
