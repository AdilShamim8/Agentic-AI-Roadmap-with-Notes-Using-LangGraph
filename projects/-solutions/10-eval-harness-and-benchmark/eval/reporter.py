"""Reporter — turns a `RunReport` into Markdown + JSON.

The Markdown report has four sections:

1. Header (agent, dataset, pattern, pass-rate badge)
2. Per-row table (id, pass/fail, evaluator scores, duration)
3. Per-evaluator aggregate scores
4. Baseline delta (if `--baseline` was supplied)
5. Reproducibility meta (seed, provider, host)

The JSON report is the `RunReport` model serialised with Pydantic — it
can be loaded back into the harness as a baseline.
"""

from __future__ import annotations

import json
import os
import platform
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.schemas import RunReport


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_report(
    report: RunReport,
    md_path: str | Path,
    json_path: str | Path | None = None,
) -> tuple[Path, Path]:
    """Write the report as Markdown + JSON.

    Returns the (md_path, json_path) actually written.
    """

    md_path = Path(md_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    if json_path is None:
        json_path = md_path.with_suffix(".json")
    else:
        json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(render_json(report), encoding="utf-8")
    return md_path, json_path


def render_markdown(report: RunReport) -> str:
    """Render a RunReport as a Markdown string."""

    s = report.summary
    lines: list[str] = []

    # 1. Header
    lines.append(f"# Eval report — {s.dataset}")
    lines.append("")
    lines.append(f"- **Agent**: `{s.agent}`")
    lines.append(f"- **Dataset**: `{s.dataset}` (pattern: `{s.pattern}`)")
    lines.append(
        f"- **Pass rate**: {s.n_passed}/{s.n_rows} = "
        f"**{s.pass_rate * 100:.1f}%** "
        + _badge(s.pass_rate)
    )
    if s.adversarial_pass_rate is not None:
        lines.append(
            f"- **Adversarial pass rate**: {s.adversarial_pass_rate * 100:.1f}%"
        )
    if s.total_duration_ms is not None:
        lines.append(f"- **Total runtime**: {s.total_duration_ms / 1000:.2f}s")
    lines.append(f"- **Generated**: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    lines.append(f"- **Host**: `{socket.gethostname()}` ({platform.system()} {platform.release()})")
    lines.append(f"- **Seed**: `{s.seed}`  ·  **LLM provider**: `{s.llm_provider}`")
    lines.append("")

    # 2. Per-row table
    lines.append("## Per-row results")
    lines.append("")
    # Build column headers from evaluators present in the report.
    evaluator_names: list[str] = []
    for rr in report.rows:
        for er in rr.results:
            if er.evaluator not in evaluator_names and er.evaluator != "__runner__":
                evaluator_names.append(er.evaluator)
    header = ["#", "id", "pass", "tags", "dur (ms)"] + [
        f"{e}" for e in evaluator_names
    ] + ["notes"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for i, rr in enumerate(report.rows, 1):
        ev_map = {er.evaluator: er for er in rr.results}
        cells = [
            str(i),
            f"`{rr.row.id}`",
            "✅" if rr.passed else "❌",
            ",".join(rr.row.tags) or "-",
            f"{(rr.duration_ms or 0):.0f}",
        ]
        for ev in evaluator_names:
            er = ev_map.get(ev)
            if er is None:
                cells.append("-")
            else:
                cells.append(f"{er.score:.2f}")
        if rr.error:
            cells.append(f"**error**: {rr.error[:60]}")
        else:
            # Show the rationale of the first failing evaluator (or first passing).
            note = ""
            for er in rr.results:
                if er.evaluator == "__runner__":
                    continue
                if not er.passed:
                    note = (er.rationale or "")[:80]
                    break
            cells.append(note)
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # 3. Per-evaluator aggregates
    lines.append("## Per-evaluator aggregate")
    lines.append("")
    lines.append("| evaluator | mean score | pass rate |")
    lines.append("|---|---|---|")
    for ev, score in s.evaluator_scores.items():
        pr = s.evaluator_pass_rates.get(ev, 0.0)
        lines.append(f"| `{ev}` | {score:.3f} | {pr * 100:.1f}% |")
    lines.append("")

    # 4. Baseline delta
    if s.baseline_diff:
        lines.append("## Baseline delta")
        lines.append("")
        lines.append("| metric | current | baseline | Δ |")
        lines.append("|---|---|---|---|")
        for metric, delta in s.baseline_diff.items():
            arrow = "📈" if delta > 0 else ("📉" if delta < 0 else "→")
            lines.append(
                f"| `{metric}` | - | - | {arrow} {delta:+.3f} |"
            )
        lines.append("")

    # 5. Reproducibility
    lines.append("## Reproducibility")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report.config, indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def render_json(report: RunReport) -> str:
    """Render a RunReport as a JSON string (Pydantic serialisation)."""

    return report.model_dump_json(indent=2)


def load_baseline(path: str | Path) -> dict[str, Any]:
    """Load a baseline JSON report and return its summary dict."""

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("summary", data)


def diff_against_baseline(
    report: RunReport, baseline_path: str | Path
) -> dict[str, float]:
    """Compute deltas vs baseline for the headline metrics.

    Returns a dict like:
        {"pass_rate": +0.05, "exact_match": +0.1, ...}
    """

    base = load_baseline(baseline_path)
    diff: dict[str, float] = {}

    cur_pr = report.summary.pass_rate
    base_pr = base.get("pass_rate", cur_pr)
    diff["pass_rate"] = round(cur_pr - base_pr, 4)

    base_scores: dict[str, float] = base.get("evaluator_scores", {})
    for ev, score in report.summary.evaluator_scores.items():
        if ev in base_scores:
            diff[ev] = round(score - base_scores[ev], 4)
    return diff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _badge(pass_rate: float) -> str:
    if pass_rate >= 0.9:
        return "![pass](https://img.shields.io/badge/pass-green)"
    if pass_rate >= 0.7:
        return "![pass](https://img.shields.io/badge/pass-yellow)"
    if pass_rate >= 0.5:
        return "![pass](https://img.shields.io/badge/pass-orange)"
    return "![pass](https://img.shields.io/badge/pass-red)"
