"""CLI entry point — `eval ...` commands.

Built with Typer + Rich. The CLI is intentionally thin: every command
just wires together pieces from the rest of the package and prints
something useful.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Load .env if python-dotenv is available (optional dep).
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from eval.config import get_settings, ensure_dirs
from eval.evaluators import EvaluatorRegistry
from eval.evaluators.reliability import (
    cohen_kappa,
    interpret_kappa,
    krippendorff_alpha_nominal,
)
from eval.registry import Registry
from eval.reporter import diff_against_baseline, write_report
from eval.runner import (
    Runner,
    RunnerConfig,
    build_agent,
    build_evaluators,
)
from eval.utils import load_dataset_rows

app = typer.Typer(
    name="eval",
    help="A reusable eval harness for benchmarking agents against golden datasets.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


# ---------------------------------------------------------------------------
# `eval run`
# ---------------------------------------------------------------------------


@app.command()
def run(
    agent: str = typer.Option(
        ...,
        "--agent",
        "-a",
        help="Dotted path to a BaseAgent subclass, e.g. "
        "'eval.agents.sample_agents:ReActSampleAgent'.",
    ),
    dataset: Optional[str] = typer.Option(
        None,
        "--dataset",
        "-d",
        help="Dataset name (without .jsonl) or path. Mutually exclusive with --pattern.",
    ),
    pattern: Optional[str] = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Run all datasets registered under this pattern.",
    ),
    baseline: Optional[Path] = typer.Option(
        None,
        "--baseline",
        "-b",
        help="Path to a baseline JSON report to compute a delta against.",
    ),
    report_path: Optional[Path] = typer.Option(
        None,
        "--report-path",
        "-r",
        help="Where to write the Markdown report. Defaults to reports/<dataset>.md.",
    ),
    workers: int = typer.Option(
        None,
        "--workers",
        "-w",
        help="Number of parallel workers. Defaults to EVAL_WORKERS.",
    ),
    no_progress: bool = typer.Option(
        False, "--no-progress", help="Disable the Rich progress bar."
    ),
    fail_fast: bool = typer.Option(
        False, "--fail-fast", help="Stop on the first agent crash."
    ),
) -> None:
    """Run an agent against a dataset and write a report."""

    settings = get_settings()
    ensure_dirs(settings)
    registry = Registry.default()

    # Resolve dataset + evaluators.
    if dataset and pattern:
        console.print(
            "[red]Error:[/] --dataset and --pattern are mutually exclusive."
        )
        raise typer.Exit(2)
    if not dataset and not pattern:
        console.print(
            "[red]Error:[/] must supply either --dataset or --pattern."
        )
        raise typer.Exit(2)

    if pattern:
        entry = registry.get(pattern)
        dataset_names = entry.datasets
        eval_specs = entry.evaluators
        baseline_path = baseline or (
            Path(entry.baseline) if entry.baseline else None
        )
    else:
        # Find the pattern that owns this dataset (or default to the agent's pattern).
        try:
            pattern_name = registry.find_dataset_pattern(dataset)
        except KeyError:
            pattern_name = "unknown"
            pattern_entry = None
        else:
            pattern_entry = registry.get(pattern_name)
        dataset_names = [dataset]
        eval_specs = pattern_entry.evaluators if pattern_entry else []
        baseline_path = baseline or (
            Path(pattern_entry.baseline) if pattern_entry and pattern_entry.baseline else None
        )

    # Resolve dataset paths.
    dataset_paths: list[str] = []
    for name in dataset_names:
        p = _resolve_dataset_path(name, settings)
        if not Path(p).exists():
            console.print(f"[red]Error:[/] dataset not found: {p}")
            raise typer.Exit(2)
        dataset_paths.append(p)

    # Build agent + evaluators.
    agent_obj = build_agent(agent)
    evaluators = build_evaluators(eval_specs)

    if not evaluators:
        console.print(
            "[yellow]Warning:[/] no evaluators resolved; report will be empty."
        )

    cfg = RunnerConfig(
        workers=workers or settings.workers,
        timeout_s=settings.run_timeout_s,
        seed=settings.seed,
        llm_provider=settings.llm_provider,
        fail_fast=fail_fast,
        show_progress=not no_progress,
    )

    # Run each dataset.
    reports_written: list[tuple[str, Path, Path]] = []
    for ds_path in dataset_paths:
        ds_name = Path(ds_path).stem
        runner = Runner(
            agent=agent_obj,
            dataset_path=ds_path,
            evaluators=evaluators,
            config=cfg,
            console=console,
        )
        report = runner.run()

        # Baseline diff (if any).
        if baseline_path and Path(baseline_path).exists():
            report.summary.baseline_diff = diff_against_baseline(report, baseline_path)

        # Write report.
        if report_path and len(dataset_paths) == 1:
            md_target = report_path
        else:
            md_target = settings.report_dir / f"{ds_name}.md"
        md_path, json_path = write_report(report, md_target)
        reports_written.append((ds_name, md_path, json_path))

        _print_summary(console, ds_name, report)

    console.print("")
    for ds_name, md_path, json_path in reports_written:
        console.print(
            f"[green]✓[/] {ds_name}: wrote [bold]{md_path}[/] and [bold]{json_path}[/]"
        )


# ---------------------------------------------------------------------------
# `eval list`
# ---------------------------------------------------------------------------


@app.command(name="list")
def list_registry() -> None:
    """Print the benchmark registry."""

    registry = Registry.default()
    table = Table(title="Benchmark registry")
    table.add_column("pattern", style="cyan")
    table.add_column("datasets", style="green")
    table.add_column("evaluators")
    table.add_column("baseline", style="dim")
    for name in registry.all_patterns():
        entry = registry.get(name)
        table.add_row(
            name,
            ", ".join(entry.datasets),
            ", ".join(e.name for e in entry.evaluators),
            entry.baseline or "-",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# `eval lint-dataset`
# ---------------------------------------------------------------------------


@app.command(name="lint-dataset")
def lint_dataset(
    path: Path = typer.Argument(..., help="Path to a .jsonl dataset file."),
) -> None:
    """Validate every row of a dataset against the schema."""

    try:
        rows = load_dataset_rows(path)
    except Exception as exc:
        console.print(f"[red]✗[/] Failed to load {path}: {exc}")
        raise typer.Exit(1)
    console.print(f"[green]✓[/] {path}: {len(rows)} valid rows.")
    n_adv = sum(1 for r in rows if r.adversarial)
    console.print(f"  adversarial: {n_adv}")
    for r in rows[:3]:
        console.print(f"  - {r.id}: {r.input[:80]}")


# ---------------------------------------------------------------------------
# `eval kappa`
# ---------------------------------------------------------------------------


@app.command()
def kappa(
    dataset: str = typer.Option(..., "--dataset", "-d", help="Dataset name."),
    judge_a: str = typer.Option(..., "--judge-a", help="First evaluator name."),
    judge_b: str = typer.Option(..., "--judge-b", help="Second evaluator name."),
    threshold: float = typer.Option(0.7, "--threshold", help="Pass-score threshold."),
    sample_agent: str = typer.Option(
        "eval.agents.sample_agents:ReActSampleAgent",
        "--agent",
        help="Agent to run the dataset against (default: ReActSampleAgent).",
    ),
) -> None:
    """Compute Cohen's kappa between two evaluators on a dataset.

    The spec target is kappa > 0.6 (substantial agreement).
    """

    settings = get_settings()
    ensure_dirs(settings)
    ds_path = _resolve_dataset_path(dataset, settings)
    rows = load_dataset_rows(ds_path)

    agent_obj = build_agent(sample_agent)
    ev_a = EvaluatorRegistry.build(judge_a)
    ev_b = EvaluatorRegistry.build(judge_b)

    scores_a: list[float] = []
    scores_b: list[float] = []
    for row in rows:
        try:
            out = agent_obj.run(row.input)
            sa = ev_a.evaluate(row, out, out.trajectory).score
            sb = ev_b.evaluate(row, out, out.trajectory).score
        except Exception:
            sa, sb = 0.0, 0.0
        scores_a.append(sa)
        scores_b.append(sb)

    k = cohen_kappa(scores_a, scores_b, threshold)
    a = krippendorff_alpha_nominal([scores_a, scores_b], threshold)
    interp = interpret_kappa(k)

    console.print(
        Panel.fit(
            f"[bold]Cohen's kappa[/]: [cyan]{k:.3f}[/]  ({interp})\n"
            f"[bold]Krippendorff α[/]: [cyan]{a:.3f}[/]\n"
            f"Dataset: {dataset} ({len(rows)} rows)\n"
            f"Judge A: {judge_a}\n"
            f"Judge B: {judge_b}\n"
            f"Threshold: {threshold}",
            title="Inter-rater reliability",
        )
    )
    if k < 0.6:
        console.print(
            "[yellow]⚠ kappa < 0.6 — below the spec target. Consider revising your rubric.[/]"
        )
    else:
        console.print("[green]✓ kappa ≥ 0.6 — meets the spec target.[/]")


# ---------------------------------------------------------------------------
# `eval eval-list` — list available evaluators
# ---------------------------------------------------------------------------


@app.command(name="evaluators")
def list_evaluators() -> None:
    """List all registered evaluators."""

    table = Table(title="Registered evaluators")
    table.add_column("name", style="cyan")
    for name in EvaluatorRegistry.all_names():
        table.add_row(name)
    console.print(table)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_dataset_path(name: str, settings) -> str:
    """Resolve a dataset name into a path.

    Accepts:
      - "react" → benchmarks/datasets/react.jsonl
      - "react.jsonl" → benchmarks/datasets/react.jsonl
      - "/abs/path/react.jsonl" → unchanged
    """

    if os.path.isabs(name) or os.path.exists(name):
        return name
    if not name.endswith(".jsonl"):
        name = name + ".jsonl"
    return str(settings.datasets_dir / name)


def _print_summary(console: Console, dataset: str, report) -> None:
    s = report.summary
    table = Table(title=f"Summary — {dataset}")
    table.add_column("metric", style="cyan")
    table.add_column("value", style="green")
    table.add_row("agent", s.agent)
    table.add_row("pattern", s.pattern)
    table.add_row("rows", str(s.n_rows))
    table.add_row("passed", f"{s.n_passed}/{s.n_rows}")
    table.add_row("pass_rate", f"{s.pass_rate * 100:.1f}%")
    if s.adversarial_pass_rate is not None:
        table.add_row("adversarial", f"{s.adversarial_pass_rate * 100:.1f}%")
    table.add_row("runtime", f"{(s.total_duration_ms or 0) / 1000:.2f}s")
    for ev, sc in s.evaluator_scores.items():
        table.add_row(f"score:{ev}", f"{sc:.3f}")
    if s.baseline_diff:
        for metric, delta in s.baseline_diff.items():
            arrow = "📈" if delta > 0 else ("📉" if delta < 0 else "→")
            table.add_row(f"Δ:{metric}", f"{arrow} {delta:+.3f}")
    console.print(table)


if __name__ == "__main__":
    app()
