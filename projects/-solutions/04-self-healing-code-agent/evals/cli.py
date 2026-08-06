"""Eval CLI: `self-heal-eval run --fixtures fixtures/`."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from evals.metrics import aggregate
from evals.runner import EvalRunner, discover_cases
from self_heal.agent import SelfHealAgent
from self_heal.logging import configure_logging

app = typer.Typer(
    name="self-heal-eval",
    help="Evaluation harness for the self-healing agent.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def run(
    fixtures: Path = typer.Option(
        Path("fixtures"), "--fixtures", "-f", help="Directory of fixture cases."
    ),
    max_iterations: int = typer.Option(3, "--max-iterations", "-n"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    only: str = typer.Option(
        None, "--only", help="Only run cases whose name contains this substring."
    ),
) -> None:
    """Run the agent over all fixture cases and print the rubric metrics."""
    configure_logging()
    cases = discover_cases(fixtures)
    if only:
        cases = [c for c in cases if only in c.name]
    if not cases:
        console.print(f"[red]no fixture cases found under[/red] {fixtures}")
        raise typer.Exit(code=2)

    console.print(f"[bold]discovered {len(cases)} cases[/bold]")
    agent = SelfHealAgent()
    runner = EvalRunner(agent=agent)
    results = runner.run_all(cases, max_iterations=max_iterations)
    metrics = aggregate(results)

    if json_out:
        print(json.dumps(metrics.to_dict(), indent=2))
    else:
        console.print(_per_case_table(results))
        console.print(_metrics_table(metrics))

    raise typer.Exit(code=0 if metrics.pass_rate > 0 else 1)


@app.command(name="list")
def list_cases(
    fixtures: Path = typer.Option(Path("fixtures"), "--fixtures", "-f"),
) -> None:
    """List discovered fixture cases without running them."""
    cases = discover_cases(fixtures)
    table = Table(title=f"cases under {fixtures}")
    table.add_column("name")
    table.add_column("target_test")
    for c in cases:
        table.add_row(c.name, c.target_test)
    console.print(table)


def _per_case_table(results) -> Table:  # type: ignore[no-untyped-def]
    t = Table(title="per-case results")
    t.add_column("case")
    t.add_column("passed")
    t.add_column("no-reg")
    t.add_column("iters")
    t.add_column("llm")
    t.add_column("cost")
    t.add_column("status")
    for r in results:
        t.add_row(
            r.name,
            "✓" if r.passed else "✗",
            "✓" if r.no_regression else "✗",
            str(r.iterations),
            str(r.llm_calls),
            f"${r.cost_usd:.4f}",
            r.status,
        )
    return t


def _metrics_table(m) -> Table:  # type: ignore[no-untyped-def]
    t = Table(title="rubric metrics")
    t.add_column("metric")
    t.add_column("value")
    t.add_column("target", justify="right")
    t.add_row("pass rate", f"{m.pass_rate:.1%}", "≥ 40%")
    t.add_row("no-regression rate", f"{m.no_regression_rate:.1%}", "≥ 95%")
    t.add_row("cost per patch", f"${m.cost_per_patch_usd:.4f}", "< $1.00")
    t.add_row("median LLM calls", f"{m.median_llm_calls:.1f}", "< 8")
    t.add_row("mean LLM calls", f"{m.mean_llm_calls:.1f}", "")
    t.add_row("total cost", f"${m.total_cost_usd:.4f}", "")
    t.add_row("cases", f"{m.n_passed}/{m.n_cases}", "")
    return t


if __name__ == "__main__":
    app()
