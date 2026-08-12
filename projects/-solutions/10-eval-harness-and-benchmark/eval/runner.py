"""The runner — executes an agent against a dataset and feeds each row into
a list of evaluators.

Design goals:

- **Deterministic by default.** Same agent + dataset + evaluators + seed →
  byte-identical report. Parallelism is opt-in.
- **Crash-safe.** If one row blows up the agent, the runner captures the
  exception, marks the row as failed, and continues. The report always
  contains every row.
- **Observable.** Progress is streamed to a Rich console so long-running
  evals don't look frozen.
"""

from __future__ import annotations

import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from eval.agents.base import BaseAgent
from eval.config import Settings, get_settings
from eval.evaluators import EvaluatorRegistry
from eval.evaluators.base import BaseEvaluator
from eval.schemas import (
    AgentOutput,
    DatasetRow,
    EvalResult,
    RowResult,
    RunReport,
    RunSummary,
)
from eval.utils import import_string, load_dataset_rows


@dataclass
class RunnerConfig:
    """Knobs for the runner."""

    workers: int = 1
    timeout_s: int = 60
    seed: int = 42
    llm_provider: str | None = None
    fail_fast: bool = False
    show_progress: bool = True

    @classmethod
    def from_settings(cls, s: Settings) -> "RunnerConfig":
        return cls(
            workers=s.workers,
            timeout_s=s.run_timeout_s,
            seed=s.seed,
            llm_provider=s.llm_provider,
        )


@dataclass
class Runner:
    """Orchestrates the evaluation of one agent against one dataset."""

    agent: BaseAgent
    dataset_path: str
    evaluators: list[BaseEvaluator] = field(default_factory=list)
    config: RunnerConfig = field(default_factory=RunnerConfig)
    console: Console = field(default_factory=Console)

    # ----- public API ----------------------------------------------------

    def run(self) -> RunReport:
        rows = load_dataset_rows(self.dataset_path)
        if self.config.show_progress:
            row_results = self._run_with_progress(rows)
        else:
            row_results = self._run_plain(rows)
        summary = _summarise(
            agent=repr(self.agent),
            dataset=_dataset_name(self.dataset_path),
            pattern=getattr(self.agent, "pattern", "unknown"),
            row_results=row_results,
            seed=self.config.seed,
            llm_provider=self.config.llm_provider,
        )
        return RunReport(
            summary=summary,
            rows=row_results,
            config={
                "workers": self.config.workers,
                "timeout_s": self.config.timeout_s,
                "seed": self.config.seed,
                "llm_provider": self.config.llm_provider,
                "agent": repr(self.agent),
                "dataset": self.dataset_path,
                "evaluators": [e.display_name() for e in self.evaluators],
            },
        )

    # ----- internals -----------------------------------------------------

    def _run_plain(self, rows: list[DatasetRow]) -> list[RowResult]:
        out: list[RowResult] = []
        for row in rows:
            out.append(self._run_one(row))
            if self.config.fail_fast and out[-1].error:
                break
        return out

    def _run_with_progress(self, rows: list[DatasetRow]) -> list[RowResult]:
        # Use a dict to preserve order despite concurrent completion.
        results: dict[int, RowResult] = {}

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
        )
        with progress:
            task_id = progress.add_task(
                f"Running {self.agent.name} on {len(rows)} rows...", total=len(rows)
            )

            if self.config.workers <= 1:
                for i, row in enumerate(rows):
                    rr = self._run_one(row)
                    results[i] = rr
                    status = "✓" if rr.passed else "✗"
                    progress.console.print(
                        f"  [{ 'green' if rr.passed else 'red' }]{status}[/{ 'green' if rr.passed else 'red' }] "
                        f"{row.id}: {_short(rr)}"
                    )
                    progress.advance(task_id)
                    if self.config.fail_fast and rr.error:
                        break
            else:
                with ThreadPoolExecutor(max_workers=self.config.workers) as pool:
                    futures = {
                        pool.submit(self._run_one, row): i for i, row in enumerate(rows)
                    }
                    for fut in as_completed(futures):
                        i = futures[fut]
                        rr = fut.result()
                        results[i] = rr
                        status = "✓" if rr.passed else "✗"
                        progress.console.print(
                            f"  [{ 'green' if rr.passed else 'red' }]{status}[/{ 'green' if rr.passed else 'red' }] "
                            f"{results[i].row.id}: {_short(rr)}"
                        )
                        progress.advance(task_id)

        return [results[i] for i in sorted(results)]

    def _run_one(self, row: DatasetRow) -> RowResult:
        start = time.perf_counter()
        try:
            output = self._invoke_agent(row.input)
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            err = f"{type(exc).__name__}: {exc}"
            tb = traceback.format_exc(limit=4)
            return RowResult(
                row=row,
                output=AgentOutput(answer=None),
                results=[
                    EvalResult(
                        evaluator="__runner__",
                        row_id=row.id,
                        passed=False,
                        score=0.0,
                        rationale=f"Agent crashed: {err}",
                        details={"traceback": tb},
                    )
                ],
                passed=False,
                duration_ms=duration,
                error=err,
            )

        duration = (time.perf_counter() - start) * 1000
        eval_results: list[EvalResult] = []
        for ev in self.evaluators:
            try:
                eval_results.append(
                    ev.evaluate(row, output, output.trajectory)
                )
            except Exception as exc:
                eval_results.append(
                    EvalResult(
                        evaluator=ev.display_name(),
                        row_id=row.id,
                        passed=False,
                        score=0.0,
                        rationale=f"Evaluator crashed: {type(exc).__name__}: {exc}",
                    )
                )
        passed = all(er.passed for er in eval_results) and bool(eval_results)
        return RowResult(
            row=row,
            output=output,
            results=eval_results,
            passed=passed,
            duration_ms=duration,
        )

    def _invoke_agent(self, input: str) -> AgentOutput:
        # NOTE: we do not enforce `timeout_s` here because Python's stdlib
        # doesn't make it trivial to interrupt arbitrary code. For real
        # agents that may hang, wrap them in a subprocess.
        return self.agent.run(input)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def build_agent(agent_spec: str, **agent_kwargs: Any) -> BaseAgent:
    """Resolve a `module:Class` spec into an instantiated BaseAgent."""

    cls = import_string(agent_spec)
    if not (isinstance(cls, type) and issubclass(cls, BaseAgent)):
        raise TypeError(f"{agent_spec!r} is not a BaseAgent subclass.")
    return cls(**agent_kwargs)


def build_evaluators(specs) -> list[BaseEvaluator]:
    """Build evaluators from a list of EvaluatorSpec (or dicts)."""

    out: list[BaseEvaluator] = []
    for spec in specs:
        if isinstance(spec, dict):
            name = spec.get("name")
            params = spec.get("params") or {}
        else:
            name = spec.name
            params = spec.params or {}
        out.append(EvaluatorRegistry.build(name, params))
    return out


# ---------------------------------------------------------------------------
# Summarisation
# ---------------------------------------------------------------------------


def _summarise(
    agent: str,
    dataset: str,
    pattern: str,
    row_results: list[RowResult],
    seed: int | None,
    llm_provider: str | None,
    baseline_diff: dict[str, float] | None = None,
) -> RunSummary:
    n = len(row_results)
    n_passed = sum(1 for r in row_results if r.passed)
    pass_rate = (n_passed / n) if n else 0.0

    # Per-evaluator scores.
    scores_by_ev: dict[str, list[float]] = {}
    passes_by_ev: dict[str, int] = {}
    for rr in row_results:
        for er in rr.results:
            scores_by_ev.setdefault(er.evaluator, []).append(er.score)
            passes_by_ev[er.evaluator] = passes_by_ev.get(er.evaluator, 0) + (
                1 if er.passed else 0
            )
    evaluator_scores = {
        ev: round(sum(s) / len(s), 4) for ev, s in scores_by_ev.items() if s
    }
    evaluator_pass_rates = {
        ev: round(passes_by_ev[ev] / n, 4) for ev in passes_by_ev if n
    }

    # Adversarial subset.
    adv_rows = [r for r in row_results if r.row.adversarial]
    adv_pass_rate: float | None = None
    if adv_rows:
        adv_pass_rate = round(
            sum(1 for r in adv_rows if r.passed) / len(adv_rows), 4
        )

    total_ms = sum(r.duration_ms or 0.0 for r in row_results)

    return RunSummary(
        agent=agent,
        dataset=dataset,
        pattern=pattern,
        n_rows=n,
        n_passed=n_passed,
        pass_rate=round(pass_rate, 4),
        evaluator_scores=evaluator_scores,
        evaluator_pass_rates=evaluator_pass_rates,
        adversarial_pass_rate=adv_pass_rate,
        total_duration_ms=total_ms,
        seed=seed,
        llm_provider=llm_provider,
        baseline_diff=baseline_diff,
    )


def _dataset_name(path: str) -> str:
    """`benchmarks/datasets/react.jsonl` -> `react`."""

    import os

    base = os.path.basename(path)
    if "." in base:
        base = base.rsplit(".", 1)[0]
    return base


def _short(rr: RowResult) -> str:
    if rr.error:
        return f"ERROR: {rr.error[:80]}"
    parts = []
    for er in rr.results:
        if er.evaluator == "__runner__":
            continue
        parts.append(f"{er.evaluator}={er.score:.2f}")
    return " ".join(parts) if parts else "(no evaluators)"
