"""
Evaluation runner — executes the dataset through the supervisor and
computes metrics.

Usage::

    python -m eval.runner                          # run all 20 tasks
    python -m eval.runner --limit 5                # run first 5 tasks
    python -m eval.runner --output results.json    # save results
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from eval.metrics import EvalMetrics, TaskResult, compute_metrics, state_to_result
from supervisor.graph import SupervisorGraph

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).parent / "dataset.json"
RESULTS_DIR = Path(__file__).parent / "results"


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    """Load the evaluation dataset."""
    with open(path) as f:
        data = json.load(f)
    return data["tasks"]


async def run_single_task(
    graph: SupervisorGraph, task_def: dict[str, Any]
) -> TaskResult:
    """Run a single task through the supervisor and capture results."""
    task_id = task_def["id"]
    task_text = task_def["task"]

    logger.info("EVAL: running task %d: %s", task_id, task_text[:80])

    t0 = time.perf_counter()
    try:
        state = await graph.run(task_text)
        result = state_to_result(task_id, task_text, state)
        result.total_latency_ms = (time.perf_counter() - t0) * 1000
    except Exception as exc:
        logger.error("EVAL: task %d failed: %s", task_id, exc)
        result = TaskResult(
            task_id=task_id,
            task=task_text,
            completed=False,
            final_output="",
            error=str(exc),
            total_latency_ms=(time.perf_counter() - t0) * 1000,
        )
    return result


async def run_eval(
    limit: int | None = None,
    output_file: str | None = None,
    verbose: bool = True,
) -> EvalMetrics:
    """
    Run the full evaluation.

    Args:
        limit: If set, only run the first N tasks (useful for quick checks).
        output_file: If set, save detailed results to this JSON file.
        verbose: If True, print progress and summary.

    Returns:
        The computed :class:`EvalMetrics`.
    """
    tasks = load_dataset()
    if limit:
        tasks = tasks[:limit]

    logger.info("EVAL: starting evaluation with %d tasks", len(tasks))

    # Create a fresh supervisor for the eval (shares the A2A adapter).
    graph = SupervisorGraph()
    results: list[TaskResult] = []

    for i, task_def in enumerate(tasks):
        if verbose:
            print(f"[{i+1}/{len(tasks)}] Task {task_def['id']}: {task_def['task'][:60]}...")
        result = await run_single_task(graph, task_def)
        results.append(result)
        if verbose:
            status = "✓" if result.completed else "✗"
            print(f"   {status} {result.steps_completed}/{result.steps_total} steps, "
                  f"{len(result.handoffs)} handoffs, {result.total_latency_ms:.0f}ms")

    metrics = compute_metrics(results)

    if verbose:
        print()
        print(metrics.summary())

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = output_file or str(RESULTS_DIR / "eval_results.json")
    output = {
        "metrics": metrics.to_dict(),
        "task_results": [
            {
                "task_id": r.task_id,
                "task": r.task,
                "completed": r.completed,
                "steps_total": r.steps_total,
                "steps_completed": r.steps_completed,
                "steps_failed": r.steps_failed,
                "handoffs": r.handoffs,
                "total_latency_ms": r.total_latency_ms,
                "final_output_length": len(r.final_output),
                "error": r.error,
            }
            for r in results
        ],
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("EVAL: results saved to %s", out_path)

    return metrics


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run the evaluation")
    parser.add_argument("--limit", type=int, help="Only run first N tasks")
    parser.add_argument("--output", "-o", help="Output results JSON file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Less output")
    args = parser.parse_args()

    asyncio.run(run_eval(limit=args.limit, output_file=args.output, verbose=not args.quiet))


if __name__ == "__main__":
    main()
