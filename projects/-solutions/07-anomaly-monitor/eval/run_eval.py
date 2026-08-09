"""CLI: replay data through the pipeline in eval mode and score it.

Usage::

    python -m eval.run_eval --data data/samples/anomalous.jsonl \\
                            --labels data/samples/labels.jsonl

Eval mode is a stripped-down version of :class:`AnomalyPipeline`
(`option (a)` from the task spec — construct components directly rather
than adding an ``eval_mode`` flag to the main pipeline):

  * :class:`FileSource` replays the JSONL data file (fast by default —
    ``--speed 100`` means 100× real-time).
  * In-memory :class:`Windower` (Redis is not needed for eval; the
    windower falls back to in-memory automatically).
  * Real :class:`EnsembleDetector` (statistical + LLM with rule-based
    stub fallback when no API key is set).
  * :class:`ResponseGraph` with an **auto-approving** HITL manager
    (:class:`AutoApproveHITL`) so the eval never blocks on a human.

**HITL auto-approve choice:** rather than tweaking
``settings.hitl_min_severity`` and capping detector severity (which would
distort the detector's output), we subclass :class:`HITLManager` and
override ``request_approval`` to always return ``(True, None)``. This
keeps the response graph's routing logic intact (the ``hitl_review`` node
still runs and the trace still records "hitl: approved") while making the
eval fully unattended.

Each flagged anomaly becomes a :class:`PipelineRecord` (window + anomaly +
proposed action + result + detect/response timestamps). The LLM-as-judge
(:class:`eval.judge.ResponseJudge`) grades each record; the rubric
(:class:`eval.rubric.EvalRubric`) is then computed and printed + written
to ``--out`` (default ``./.runtime/eval_result.json``).

Exit code is 0 if all gated metrics pass, 1 otherwise (useful for CI).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Optional

import structlog

from anomaly_monitor.aggregation.windower import Windower
from anomaly_monitor.config import Settings, settings as default_settings
from anomaly_monitor.detection.ensemble import EnsembleDetector
from anomaly_monitor.detection.llm_detector import LLMAnomalyDetector
from anomaly_monitor.detection.statistical import StatisticalDetector
from anomaly_monitor.models import Action, PipelineRecord, Window
from anomaly_monitor.response.graph import ResponseGraph
from anomaly_monitor.response.hitl import HITLManager
from anomaly_monitor.streaming.file_source import FileSource

from eval.judge import ResponseJudge
from eval.rubric import EvalRubric

log = structlog.get_logger()


class AutoApproveHITL(HITLManager):
    """HITL manager that always approves without modification.

    Eval must run unattended, so we substitute this for the real
    :class:`HITLManager`. The response graph still routes through the
    ``hitl_review`` node (preserving the trace) but approval is instant.
    """

    async def request_approval(
        self, action: Action
    ) -> tuple[bool, Optional[Action]]:
        """Always return ``(True, None)`` — approve, no modification."""
        log.debug("eval_hitl_auto_approved", kind=action.kind)
        return True, None


def _load_labels(path: str | Path) -> list[dict]:
    """Load a JSONL labels file.

    Each line: ``{"anomaly_id", "start_ts", "end_ts", "kind"}``.
    """
    p = Path(path)
    out: list[dict] = []
    with p.open("r", encoding="utf-8") as fh:
        for ln in fh.read().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError as exc:
                log.warning("bad_label_line_skipped", error=str(exc))
    log.info("labels_loaded", count=len(out), path=str(p))
    return out


def _to_action(proposed: object | None) -> Optional[Action]:
    """Convert a response-graph proposed action (BaseAction) to plain Action.

    The graph stores a :class:`BaseAction` executor subclass; the
    :class:`PipelineRecord` only needs the plain :class:`Action` public
    fields. This explicit conversion avoids any pydantic re-validation
    surprises with private attrs.
    """
    if proposed is None:
        return None
    return Action(
        kind=getattr(proposed, "kind", "noop"),  # type: ignore[arg-type]
        severity=getattr(proposed, "severity", "info"),
        target=getattr(proposed, "target", ""),
        payload=dict(getattr(proposed, "payload", {}) or {}),
        dry_run=bool(getattr(proposed, "dry_run", True)),
    )


async def _run_eval_pipeline(
    data_path: str,
    speed: float,
    settings: Settings,
) -> list[PipelineRecord]:
    """Replay data file through windower+detector+response; collect records.

    Each window is scored **once, at completion** (when the next window starts)
    so the detector sees the full window contents and its rolling baseline is
    not polluted by partial windows. The final in-progress windows are scored
    at the end of the replay.
    """
    source = FileSource(path=data_path, speed=speed)
    windower = Windower(settings=settings)
    await windower.start()
    stat = StatisticalDetector(settings=settings)
    llm_det = LLMAnomalyDetector(settings=settings)
    detector = EnsembleDetector(settings=settings, statistical=stat, llm=llm_det)
    hitl = AutoApproveHITL(settings=settings)
    graph = ResponseGraph(settings=settings, hitl=hitl)

    records: list[PipelineRecord] = []
    current_ids: dict[str, str] = {}  # "60s" | "300s" -> current window_id
    scored_ids: set[str] = set()  # window_ids already scored

    async def _score_window(window: Window) -> None:
        """Run detector + response graph for a (completed) window, record if anomalous."""
        wid = window.window_id
        if wid in scored_ids or window.count == 0:
            return
        scored_ids.add(wid)
        detect_t0 = time.time()
        try:
            score = await detector.detect(window)
        except Exception as exc:  # noqa: BLE001
            log.error("eval_detector_failed", error=str(exc), window_id=wid)
            return
        if not score.is_anomaly:
            log.debug(
                "eval_window_normal",
                window_id=wid,
                count=window.count,
                prob=round(score.probability, 3),
            )
            return
        try:
            state = await graph.run(window, score)
        except Exception as exc:  # noqa: BLE001
            log.error("eval_response_failed", error=str(exc), window_id=wid)
            return
        response_t = time.time()
        records.append(
            PipelineRecord(
                window=window,
                anomaly=score,
                proposed_action=_to_action(state.get("proposed_action")),
                approved=state.get("approved"),
                result=state.get("result"),
                detect_ts=detect_t0,
                response_ts=response_t,
            )
        )
        log.info(
            "eval_record_collected",
            window_id=wid,
            count=window.count,
            action=getattr(state.get("proposed_action"), "kind", None),
            severity=score.severity.value,
            latency_sec=round(response_t - detect_t0, 3),
        )

    try:
        async for event in source.events():
            windows = await windower.add_event(event)
            # Detect window transitions: when the current window_id for a
            # duration changes, the previous window is complete — score it.
            for dur_key, window in windows.items():
                prev_id = current_ids.get(dur_key)
                wid = window.window_id
                if prev_id is not None and prev_id != wid:
                    prev_window = await windower.get_window_by_id(prev_id)
                    if prev_window is not None:
                        await _score_window(prev_window)
                current_ids[dur_key] = wid
    finally:
        # Score any remaining in-progress windows at end of replay.
        for dur_key, wid in current_ids.items():
            final_window = await windower.get_window_by_id(wid)
            if final_window is not None:
                await _score_window(final_window)
        await source.aclose()
        await windower.aclose()
        await detector.aclose()

    return records


async def _run(args: argparse.Namespace) -> int:
    """Top-level async entry: load data, run pipeline, judge, score, write."""
    settings = default_settings
    labels = _load_labels(args.labels)

    log.info(
        "eval_start",
        data=args.data,
        labels=args.labels,
        speed=args.speed,
        judge=not args.no_judge,
        llm_enabled=settings.llm_enabled,
    )

    records = await _run_eval_pipeline(args.data, args.speed, settings)
    log.info("eval_records_collected", count=len(records))

    judge_results: list[tuple[float, str]] = []
    if not args.no_judge and records:
        judge = ResponseJudge(settings)
        judge_results = await judge.judge_batch(records)
        log.info(
            "eval_judge_done",
            n=len(judge_results),
            mean=(
                sum(s for s, _ in judge_results) / len(judge_results)
                if judge_results
                else 0.0
            ),
        )
    elif args.no_judge:
        log.info("eval_judge_skipped")

    rubric = EvalRubric()
    result = rubric.evaluate(records, labels, judge_results=judge_results)

    print(result.pretty())

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(result.to_dict(), fh, indent=2, default=str)
    log.info("eval_result_written", path=str(out_path))

    return 0 if all(result.passed.values()) else 1


def main() -> None:
    """argparse entry point — parses CLI args and runs the async eval."""
    parser = argparse.ArgumentParser(
        prog="python -m eval.run_eval",
        description=(
            "Replay a JSONL data file through the anomaly pipeline in eval "
            "mode and score precision/recall/latency/correctness."
        ),
    )
    parser.add_argument(
        "--data", required=True, help="JSONL data file (one Event per line)."
    )
    parser.add_argument(
        "--labels",
        required=True,
        help="JSONL labels file (anomaly_id/start_ts/end_ts/kind per line).",
    )
    parser.add_argument(
        "--out",
        default="./.runtime/eval_result.json",
        help="Path to write the JSON result (default ./.runtime/eval_result.json).",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=100.0,
        help="Replay speed multiplier (default 100 = 100x real-time).",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Skip the LLM-as-judge step (response_correctness defaults to 1.0).",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
