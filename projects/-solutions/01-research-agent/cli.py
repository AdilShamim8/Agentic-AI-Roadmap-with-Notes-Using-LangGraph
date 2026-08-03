#!/usr/bin/env python3
"""Command-line entry point for the Research Agent.

Examples
--------
    python cli.py "The impact of quantum computing on cryptography"

    python cli.py "State of small modular reactors in 2026" \\
        --provider openai --max-iterations 3 --max-results 6

    python cli.py "Our internal migration plan" \\
        --docs notes/plan.pdf notes/meeting.md --output migration_report.md
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import click

from research_agent.config import load_settings
from research_agent.llm import FakeLLM, build_llm
from research_agent.tools.web_search import DuckDuckGoSearch, FakeSearch, build_search_tool_from_env
from research_agent.utils import slugify

STEP_LABELS = {
    "load_documents": "Loading local documents",
    "plan": "Planning sub-questions",
    "search": "Searching",
    "synthesize": "Synthesizing findings",
    "critique": "Reviewing for gaps",
    "compile_report": "Compiling final report",
}


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("topic")
@click.option("--provider", default=None, help="LLM provider: anthropic | openai | ollama (default from .env)")
@click.option("--model", default=None, help="Override the model name for the chosen provider")
@click.option("--max-results", "max_results", default=None, type=int, help="Search results per sub-question")
@click.option("--max-iterations", "max_iterations", default=None, type=int, help="Max research refinement rounds")
@click.option("--docs", "docs", multiple=True, type=click.Path(), help="Local .txt/.md/.pdf files to include")
@click.option("--output", "output", default=None, type=click.Path(), help="Where to write the Markdown report")
@click.option(
    "--engine",
    type=click.Choice(["auto", "langgraph", "simple"]),
    default="auto",
    help="Orchestration engine (default: auto — tries LangGraph, falls back to the plain-Python runner)",
)
@click.option("--demo", is_flag=True, help="Run fully offline with fake LLM + fake search (no API keys needed)")
@click.option("-v", "--verbose", is_flag=True, help="Print the agent's step-by-step trace log")
def main(
    topic: str,
    provider: Optional[str],
    model: Optional[str],
    max_results: Optional[int],
    max_iterations: Optional[int],
    docs: Tuple[str, ...],
    output: Optional[str],
    engine: str,
    demo: bool,
    verbose: bool,
) -> None:
    """Research TOPIC and write a cited Markdown report."""

    settings = load_settings()
    resolved_provider = provider or settings.llm_provider
    resolved_max_results = max_results or settings.max_results_per_query
    resolved_max_iterations = max_iterations or settings.max_iterations

    if demo:
        llm, search_tool = _build_demo_dependencies(topic)
        click.secho("Running in --demo mode: fake LLM + fake search, no API calls made.\n", fg="yellow")
    else:
        try:
            llm = build_llm(resolved_provider, model or settings.llm_model)
        except (ImportError, ValueError) as exc:
            click.secho(f"Could not initialize LLM provider '{resolved_provider}': {exc}", fg="red")
            sys.exit(1)
        try:
            search_tool = build_search_tool_from_env()
        except ImportError as exc:
            click.secho(f"Could not initialize a search tool: {exc}", fg="red")
            sys.exit(1)

    click.secho(f"Researching: {topic}", fg="cyan", bold=True)
    click.echo(
        f"provider={resolved_provider} · max_results={resolved_max_results} · "
        f"max_iterations={resolved_max_iterations} · engine={engine}\n"
    )

    def on_step(name: str, state) -> None:
        label = STEP_LABELS.get(name, name)
        click.echo(f"  → {label}...")
        if verbose:
            for line in state.get("log", [])[-1:]:
                click.echo(f"      {line}")

    started = time.time()
    final_state = _run(
        engine_choice=engine,
        topic=topic,
        llm=llm,
        search_tool=search_tool,
        docs=list(docs),
        max_results=resolved_max_results,
        max_iterations=resolved_max_iterations,
        on_step=on_step,
    )
    elapsed = time.time() - started

    output_path = Path(output) if output else Path("reports") / f"{slugify(topic)}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_state["report"], encoding="utf-8")

    click.echo()
    click.secho(f"Done in {elapsed:.1f}s.", fg="green", bold=True)
    click.echo(f"Sources collected : {len(final_state.get('sources', []))}")
    click.echo(f"Sub-questions     : {len(final_state.get('findings', {}))}")
    click.echo(f"Report written to : {output_path}")


def _run(engine_choice: str, topic: str, llm, search_tool, docs, max_results, max_iterations, on_step):
    if engine_choice in ("auto", "langgraph"):
        try:
            from research_agent.graph import build_graph
            from research_agent.state import new_state

            app = build_graph(llm, search_tool)
            state = new_state(
                topic=topic,
                local_document_paths=docs,
                max_results_per_query=max_results,
                max_iterations=max_iterations,
            )
            # Stream so we can report progress per node; falls back to a
            # single invoke() if streaming isn't available.
            final_state = state
            for event in app.stream(state):
                for node_name, node_state in event.items():
                    final_state = node_state
                    on_step(node_name, final_state)
            return final_state
        except ImportError:
            if engine_choice == "langgraph":
                raise
            # auto mode: silently fall back
        except Exception:
            if engine_choice == "langgraph":
                raise

    from research_agent.engine import run_research

    return run_research(
        topic=topic,
        llm=llm,
        search_tool=search_tool,
        local_document_paths=docs,
        max_results_per_query=max_results,
        max_iterations=max_iterations,
        on_step=on_step,
    )


def _build_demo_dependencies(topic: str):
    """Fake LLM + fake search so `--demo` works with zero setup, purely
    to let someone try the CLI's shape before wiring up real API keys."""

    from research_agent.state import SearchResult

    def fake_responder(prompt: str, system):
        if "JSON array" in prompt and "follow-up" in prompt.lower():
            return '["What are the main open challenges?"]'
        if "JSON array" in prompt:
            return (
                f'["What is {topic}?", "What is the current state of {topic}?", '
                f'"What are the key debates around {topic}?", "What is the outlook for {topic}?"]'
            )
        if "JSON object" in prompt:
            return '{"sufficient": true, "gaps": ""}'
        if prompt.startswith("Write a concise"):
            return f"{topic}: A Demo Research Report"
        return (
            f"This is placeholder synthesis text about {topic}, generated in --demo mode "
            f"so you can see the report shape without an API key [1]."
        )

    def fake_search(query: str, max_results: int):
        return [
            SearchResult(
                title=f"Demo result for '{query}'",
                url="https://example.com/demo-source",
                snippet="This is a fake snippet used only in --demo mode.",
            )
        ][:max_results]

    return FakeLLM(fake_responder), FakeSearch(fake_search)


if __name__ == "__main__":
    main()
