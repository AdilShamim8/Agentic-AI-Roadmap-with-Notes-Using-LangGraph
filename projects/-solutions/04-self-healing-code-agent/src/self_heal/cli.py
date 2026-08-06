"""CLI entrypoint: `self-heal ...` and `python -m self_heal ...`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from self_heal.agent import RunConfig, SelfHealAgent
from self_heal.config import get_settings
from self_heal.logging import configure_logging, get_logger

app = typer.Typer(
    name="self-heal",
    help="Self-healing code agent: reproduce → diagnose → patch → verify → reflexion.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
log = get_logger(__name__)


@app.command()
def run(
    repo_path: Path = typer.Argument(..., help="Path to the Python repo to fix."),
    test_target: str = typer.Option(
        ..., "--test", "-t", help="pytest nodeid, e.g. tests/test_calc.py::test_add"
    ),
    max_iterations: int = typer.Option(
        None, "--max-iterations", "-n", help="Override max iterations."
    ),
    branch: str = typer.Option(
        "self-heal/patch", "--branch", help="Git branch to commit the patch to."
    ),
    no_pr: bool = typer.Option(
        False, "--no-pr", help="Do not open a GitHub PR even if configured."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate but do not apply patches."),
    json_out: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of a table."
    ),
) -> None:
    """Run the agent on a single failing test."""
    configure_logging()
    settings = get_settings(refresh=True)

    if not repo_path.exists():
        console.print(f"[red]error:[/red] repo path does not exist: {repo_path}")
        raise typer.Exit(code=2)

    agent = SelfHealAgent(settings=settings)
    cfg = RunConfig(
        repo_path=repo_path,
        test_target=test_target,
        max_iterations=max_iterations,
        work_branch=branch,
        open_pr=not no_pr,
        dry_run=dry_run,
    )
    result = agent.run(cfg)

    if json_out:
        print(json.dumps(result.to_dict(), default=str, indent=2))
    else:
        console.print(_result_table(result))
        console.print(result.summary())

    raise typer.Exit(code=0 if result.status == "passed" else 1)


@app.command()
def doctor() -> None:
    """Diagnose the environment: API keys, provider, tools."""
    configure_logging()
    settings = get_settings(refresh=True)

    table = Table(title="self-heal doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")

    table.add_row(
        "python", sys.version.split()[0], "ok" if sys.version_info >= (3, 10) else "need >=3.10"
    )
    table.add_row("provider", settings.llm_provider.value, settings.llm_provider.value)
    table.add_row(
        "openai key", "set" if settings.has_openai() else "missing", settings.openai_model
    )
    table.add_row(
        "anthropic key", "set" if settings.has_anthropic() else "missing", settings.anthropic_model
    )
    table.add_row(
        "langsmith", "on" if settings.has_langsmith() else "off", settings.langsmith_project
    )
    table.add_row("github", "on" if settings.has_github() else "off", settings.github_repo or "-")
    table.add_row("git", _which("git"), "ok" if _which("git") else "missing")
    table.add_row("pytest", _which("pytest"), "ok" if _which("pytest") else "missing")
    table.add_row("max_iterations", str(settings.max_iterations), "")
    table.add_row("max_cost_usd", f"${settings.max_cost_usd:.2f}", "")

    console.print(table)


def _which(tool: str) -> str:
    import shutil

    return shutil.which(tool) or "not found"


def _result_table(result) -> Table:  # type: ignore[no-untyped-def]
    t = Table(title="self-heal result")
    t.add_column("key")
    t.add_column("value")
    t.add_row("status", result.status)
    t.add_row("iterations", str(result.iterations))
    t.add_row("llm_calls", str(result.llm_calls))
    t.add_row("cost_usd", f"${result.cost_usd:.4f}")
    t.add_row("pr_url", result.pr_url or "-")
    return t


if __name__ == "__main__":
    app()
