"""Typer-based CLI for the anomaly monitor.

Usage:
    anomaly-monitor run                      # run the pipeline (local mode by default)
    anomaly-monitor run --mode kafka
    anomaly-monitor publish --file events.jsonl   # publish events to Kafka
    anomaly-monitor feedback --anomaly-id <id> --real <true|false>
    anomaly-monitor version
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from anomaly_monitor import __version__
from anomaly_monitor.config import Mode, Severity, get_settings

app = typer.Typer(
    name="anomaly-monitor",
    help="Real-time anomaly monitor with async streaming agents.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


@app.command()
def version() -> None:
    """Print version and exit."""
    console.print(f"anomaly-monitor v{__version__}")


@app.command()
def run(
    mode: Optional[Mode] = typer.Option(
        None, "--mode", "-m", help="Override ANOMON_MODE."
    ),
    max_events: Optional[int] = typer.Option(
        None, "--max-events", "-n", help="Stop after N events (default: run forever)."
    ),
) -> None:
    """Run the end-to-end pipeline."""
    settings = get_settings()
    if mode is not None:
        settings.mode = mode
    # Refresh cached settings consumers (windower/detectors read globals lazily)
    get_settings.cache_clear()
    from anomaly_monitor.config import settings as fresh_settings

    if mode is not None:
        fresh_settings.mode = mode

    from anomaly_monitor.pipeline import AnomalyPipeline

    pipeline = AnomalyPipeline(settings=fresh_settings)

    try:
        asyncio.run(pipeline.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")


@app.command()
def publish(
    file: Path = typer.Option(..., "--file", "-f", help="JSONL file to publish."),
    topic: Optional[str] = typer.Option(None, "--topic", "-t"),
) -> None:
    """Publish events from a JSONL file to the configured Kafka topic."""
    settings = get_settings()
    target_topic = topic or settings.kafka_topic

    async def _publish() -> int:
        from aiokafka import AIOKafkaProducer  # type: ignore

        producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: v.encode("utf-8"),
        )
        await producer.start()
        n = 0
        try:
            with file.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    # Validate JSON
                    json.loads(line)
                    await producer.send_and_wait(target_topic, line)
                    n += 1
        finally:
            await producer.stop()
        return n

    try:
        n = asyncio.run(_publish())
        console.print(f"[green]Published {n} events to topic '{target_topic}'.[/green]")
    except ImportError:
        console.print(
            "[red]aiokafka is not installed. Install with: pip install aiokafka[/red]"
        )
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Publish failed: {exc}[/red]")
        raise typer.Exit(1)


@app.command("feedback")
def feedback_cmd(
    anomaly_id: str = typer.Option(..., "--anomaly-id", "-a"),
    real: bool = typer.Option(..., "--real/--not-real", help="Was it a real anomaly?"),
    action_correct: Optional[bool] = typer.Option(
        None, "--action-correct/--action-wrong"
    ),
    note: Optional[str] = typer.Option(None, "--note", "-n"),
) -> None:
    """Record operator feedback on a previously-detected anomaly."""
    from anomaly_monitor.models import Feedback

    settings = get_settings()

    async def _record() -> int:
        from anomaly_monitor.feedback.store import FeedbackStore

        store = FeedbackStore(settings=settings)
        await store.start()
        try:
            return await store.record(
                Feedback(
                    anomaly_id=anomaly_id,
                    is_real_anomaly=real,
                    action_correct=action_correct,
                    operator_note=note,
                )
            )
        finally:
            await store.aclose()

    fb_id = asyncio.run(_record())
    console.print(f"[green]Feedback recorded (id={fb_id}).[/green]")


@app.command("stats")
def stats() -> None:
    """Print aggregated feedback stats."""
    settings = get_settings()

    async def _stats() -> dict:
        from anomaly_monitor.feedback.store import FeedbackStore

        store = FeedbackStore(settings=settings)
        await store.start()
        try:
            return await store.stats()
        finally:
            await store.aclose()

    s = asyncio.run(_stats())
    table = Table(title="Feedback stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    for k, v in s.items():
        table.add_row(k, str(v))
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
