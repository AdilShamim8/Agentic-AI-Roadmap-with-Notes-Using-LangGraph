"""Eval rubric — precision / recall / latency / response correctness.

Implements the rubric from the project README:

| Metric                | Target  | How measured                              |
|-----------------------|---------|-------------------------------------------|
| Detection precision   | >= 80%  | flagged anomalies that are real           |
| Detection recall      | >= 90%  | real anomalies that are flagged           |
| Response correctness  | >= 85%  | LLM-as-judge on response appropriateness  |
| End-to-end latency    | < 30s   | anomaly.ts -> response.ts                 |
| False-positive cost   | tracked | business metric, not gated                |

A flagged anomaly (a :class:`PipelineRecord`) is a **true positive** iff
its window overlaps at least one labeled anomaly window, where overlap is
defined as::

    record.window.start_ts <= label["end_ts"] and
    record.window.end_ts   >= label["start_ts"]

A labeled anomaly is a **false negative** iff no flagged record overlaps
it. Precision / recall are then::

    precision = TP / n_flagged                 (1.0 when n_flagged == 0)
    recall    = (n_real - FN) / n_real         (1.0 when n_real == 0)

.. note::
   This is time-overlap matching, not one-to-one matching. A single
   flagged record can cover multiple labels (counted as 1 TP), and a
   single label can be covered by multiple records (counted once for
   recall). This matches the README definition.

Latency is taken from :attr:`PipelineRecord.e2e_latency_sec`
(``response_ts - detect_ts``); P95 and P99 are computed via
:func:`numpy.percentile`. ``response_correctness`` is the mean of the
LLM-as-judge scores (see :mod:`eval.judge`); when no judge results are
supplied it defaults to ``1.0`` and a note is added to the result.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

import structlog

from anomaly_monitor.models import PipelineRecord

log = structlog.get_logger()

# Cost (in arbitrary $ units) assigned to each false positive.
# Placeholder business metric — replace with a real cost model when available.
_FP_COST_PER_UNIT = 10.0


def _overlap(rec_start: float, rec_end: float, label: dict) -> bool:
    """True iff ``[rec_start, rec_end]`` overlaps the label's time window."""
    return (
        rec_start <= float(label["end_ts"])
        and rec_end >= float(label["start_ts"])
    )


def _pctile(values: list[float], q: float) -> float:
    """Return the q-th percentile of *values* (0.0 if empty)."""
    if not values:
        return 0.0
    import numpy as np  # lazy

    return float(np.percentile(values, q))


@dataclass
class EvalResult:
    """All metrics computed by :meth:`EvalRubric.evaluate`."""

    precision: float
    recall: float
    response_correctness: float
    p95_latency_sec: float
    p99_latency_sec: float
    fp_cost: float  # estimated cost of false positives
    n_flagged: int
    n_real: int
    n_true_positives: int
    n_false_positives: int
    n_false_negatives: int
    passed: dict[str, bool]  # metric_name -> passed threshold
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-friendly dict (for ``--out`` file)."""
        return asdict(self)

    def pretty(self) -> str:
        """Return a rich-rendered string suitable for printing."""
        from rich.console import Console, Group
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        t = Table(title="Anomaly Monitor — Eval Result", show_lines=True)
        t.add_column("Metric", style="cyan", no_wrap=True)
        t.add_column("Value", style="white")
        t.add_column("Target", style="yellow")
        t.add_column("Pass", style="green")

        def _ps(name: str) -> str:
            v = self.passed.get(name)
            if v is None:
                return "—"
            return "✓" if v else "✗"

        t.add_row("Precision", f"{self.precision:.1%}", ">= 80%", _ps("precision"))
        t.add_row("Recall", f"{self.recall:.1%}", ">= 90%", _ps("recall"))
        t.add_row(
            "Response correctness",
            f"{self.response_correctness:.1%}",
            ">= 85%",
            _ps("response_correctness"),
        )
        t.add_row(
            "P95 latency",
            f"{self.p95_latency_sec:.2f}s",
            "< 30s",
            _ps("latency_p95"),
        )
        t.add_row("P99 latency", f"{self.p99_latency_sec:.2f}s", "(tracked)", "—")
        t.add_row("FP cost", f"${self.fp_cost:.2f}", "(tracked)", "—")
        t.add_row("Flagged (TP+FP)", str(self.n_flagged), "", "")
        t.add_row("  TP", str(self.n_true_positives), "", "")
        t.add_row("  FP", str(self.n_false_positives), "", "")
        t.add_row("Real anomalies", str(self.n_real), "", "")
        t.add_row("  FN", str(self.n_false_negatives), "", "")

        body: Any = t
        if self.notes:
            nt = Table(title="Notes", show_header=False, show_lines=False)
            nt.add_column("note")
            for n in self.notes:
                nt.add_row(n)
            body = Group(t, nt)

        with console.capture() as cap:
            console.print(Panel(body, border_style="blue"))
        return cap.get()


class EvalRubric:
    """Compute precision / recall / latency / correctness against labels."""

    PRECISION_TARGET = 0.80
    RECALL_TARGET = 0.90
    RESPONSE_CORRECTNESS_TARGET = 0.85
    LATENCY_TARGET_SEC = 30.0

    def evaluate(
        self,
        records: list[PipelineRecord],
        labels: list[dict],  # [{"anomaly_id","start_ts","end_ts","kind"}]
        judge_results: Optional[list[tuple[float, str]]] = None,
    ) -> EvalResult:
        """Compute every metric. See module docstring for matching rules.

        Args:
            records: Flagged :class:`PipelineRecord` objects from the eval
                pipeline run.
            labels: Labeled anomalies, each ``{"anomaly_id", "start_ts",
                "end_ts", "kind"}``.
            judge_results: Optional list of ``(score, reason)`` tuples from
                :class:`eval.judge.ResponseJudge`, one per record (same
                order). When ``None``, ``response_correctness`` defaults to
                ``1.0`` and a note is recorded.

        Returns:
            A fully-populated :class:`EvalResult`.
        """
        n_flagged = len(records)
        n_real = len(labels)

        # TP: flagged record overlapping >=1 label.
        n_true_positives = sum(
            1
            for rec in records
            if any(
                _overlap(rec.window.start_ts, rec.window.end_ts, lbl)
                for lbl in labels
            )
        )
        n_false_positives = n_flagged - n_true_positives

        # FN: label with no overlapping flagged record.
        matched_labels = sum(
            1
            for lbl in labels
            if any(
                _overlap(rec.window.start_ts, rec.window.end_ts, lbl)
                for rec in records
            )
        )
        n_false_negatives = n_real - matched_labels

        precision = (n_true_positives / n_flagged) if n_flagged > 0 else 1.0
        recall = ((n_real - n_false_negatives) / n_real) if n_real > 0 else 1.0

        latencies = [r.e2e_latency_sec for r in records if r.e2e_latency_sec > 0]
        p95 = _pctile(latencies, 95)
        p99 = _pctile(latencies, 99)

        notes: list[str] = []
        if judge_results:
            scores = [s for s, _ in judge_results if s is not None]
            response_correctness = sum(scores) / len(scores) if scores else 0.0
            notes.append(
                f"LLM-as-judge graded {len(judge_results)} record(s); "
                f"mean score {response_correctness:.3f}."
            )
        else:
            response_correctness = 1.0
            notes.append(
                "No LLM-as-judge results supplied — response_correctness "
                "defaulted to 1.0. Pass judge_results or use ResponseJudge "
                "to measure it."
            )

        fp_cost = n_false_positives * _FP_COST_PER_UNIT

        passed = {
            "precision": precision >= self.PRECISION_TARGET,
            "recall": recall >= self.RECALL_TARGET,
            "response_correctness": (
                response_correctness >= self.RESPONSE_CORRECTNESS_TARGET
            ),
            "latency_p95": p95 < self.LATENCY_TARGET_SEC,
        }

        log.info(
            "rubric_evaluated",
            precision=round(precision, 4),
            recall=round(recall, 4),
            response_correctness=round(response_correctness, 4),
            p95_latency=round(p95, 3),
            n_flagged=n_flagged,
            n_real=n_real,
            tp=n_true_positives,
            fp=n_false_positives,
            fn=n_false_negatives,
        )

        return EvalResult(
            precision=precision,
            recall=recall,
            response_correctness=response_correctness,
            p95_latency_sec=p95,
            p99_latency_sec=p99,
            fp_cost=fp_cost,
            n_flagged=n_flagged,
            n_real=n_real,
            n_true_positives=n_true_positives,
            n_false_positives=n_false_positives,
            n_false_negatives=n_false_negatives,
            passed=passed,
            notes=notes,
        )
