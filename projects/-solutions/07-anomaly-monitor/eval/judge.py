"""LLM-as-judge for response correctness.

Asks the configured LLM (``settings.llm_model``, default ``gpt-4o-mini``)
to grade each :class:`PipelineRecord`'s proposed response on a 0–1 scale.
When no ``OPENAI_API_KEY`` is configured, :meth:`ResponseJudge.judge`
returns ``(1.0, "no_llm_judge")`` so the rest of the eval pipeline can run
deterministically without an LLM.

Calls are wrapped in :class:`tenacity.AsyncRetrying` (3 attempts, exp
backoff starting at 1s). On final failure the judge returns
``(0.0, "judge_failed")``.

Batch judging is concurrency-limited to 5 in-flight requests via an
:class:`asyncio.Semaphore`.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import structlog

from anomaly_monitor.config import Settings
from anomaly_monitor.models import PipelineRecord

log = structlog.get_logger()

_SYSTEM_PROMPT = (
    "You are evaluating the appropriateness of an automated anomaly "
    "response chosen by an SRE agent. Consider whether the action kind, "
    "severity, and target match the anomaly, and whether the response is "
    "proportionate (not over- or under-reacting). Respond ONLY with strict "
    'JSON: {"score": float in [0,1], "reason": string}. No prose, no '
    "markdown fences."
)

# Max concurrent LLM judge requests in judge_batch.
_MAX_CONCURRENCY = 5


def _build_human_prompt(record: PipelineRecord) -> str:
    """Render the record into a prompt string for the judge LLM."""
    w = record.window
    a = record.anomaly
    act = record.proposed_action
    lines = [
        "Window stats:",
        f"- count: {w.count}",
        f"- error_rate: {w.error_rate:.4f}",
        f"- unique_sources: {w.unique_sources}",
        f"- latency_p95: {w.latency_p95:.2f}",
        f"- duration_sec: {w.duration_sec}",
        "",
        "Anomaly:",
        f"- detector: {a.detector}",
        f"- probability: {a.probability:.3f}",
        f"- severity: {a.severity.value}",
        f"- reason: {a.reason}",
        "",
        "Proposed action:",
    ]
    if act is None:
        lines.append("- (none — no action was proposed)")
    else:
        lines += [
            f"- kind: {act.kind}",
            f"- severity: {act.severity.value}",
            f"- target: {act.target}",
            f"- dry_run: {act.dry_run}",
            f"- payload: {json.dumps(act.payload, default=str)}",
        ]
    lines += [
        "",
        "On a scale 0-1, how appropriate was this response? 1.0 = perfectly "
        "appropriate, 0.0 = harmful or nonsensical. Return JSON "
        '{"score": float, "reason": string}.',
    ]
    return "\n".join(lines)


def _parse_judge_json(text: Any) -> tuple[float, str]:
    """Parse ``{score, reason}`` from the LLM response, tolerating fences."""
    raw = str(text).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()
    data = json.loads(raw)
    score = float(data.get("score", 0.0))
    score = max(0.0, min(1.0, score))
    reason = str(data.get("reason", ""))[:500]
    return score, reason


class ResponseJudge:
    """LLM-as-judge grading response appropriateness in [0, 1]."""

    def __init__(self, settings: Settings) -> None:
        """Store settings; the LLM client is built lazily on first use."""
        self._settings = settings
        self._llm: Optional[Any] = None  # langchain_openai.ChatOpenAI

    @property
    def enabled(self) -> bool:
        """True iff an OpenAI API key is configured."""
        return self._settings.llm_enabled

    def _get_llm(self) -> Optional[Any]:
        """Lazy-build the ChatOpenAI client; return ``None`` on failure."""
        if self._llm is not None:
            return self._llm
        if not self.enabled:
            return None
        try:
            from langchain_openai import ChatOpenAI  # lazy
        except ImportError as exc:
            log.warning("judge_langchain_unavailable", error=str(exc))
            return None
        try:
            self._llm = ChatOpenAI(
                model=self._settings.llm_model,
                temperature=self._settings.llm_temperature,
                timeout=self._settings.llm_timeout_sec,
                openai_api_key=self._settings.openai_api_key,
                openai_api_base=self._settings.openai_base_url,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("judge_llm_init_failed", error=str(exc))
            return None
        return self._llm

    async def judge(self, record: PipelineRecord) -> tuple[float, str]:
        """Grade one record. Returns ``(score in [0,1], reason)``.

        - ``1.0`` = perfectly appropriate response.
        - Without an API key: ``(1.0, "no_llm_judge")``.
        - On final LLM failure: ``(0.0, "judge_failed")``.
        """
        if not self.enabled:
            return 1.0, "no_llm_judge"
        llm = self._get_llm()
        if llm is None:
            return 1.0, "no_llm_judge"

        try:
            from langchain_core.messages import (  # lazy
                HumanMessage,
                SystemMessage,
            )
            from tenacity import (  # lazy
                AsyncRetrying,
                stop_after_attempt,
                wait_exponential,
            )
        except ImportError as exc:
            log.warning("judge_deps_unavailable", error=str(exc))
            return 0.0, "judge_failed"

        prompt = _build_human_prompt(record)
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        async def _call() -> tuple[float, str]:
            resp = await llm.ainvoke(messages)  # type: ignore[union-attr]
            text = getattr(resp, "content", resp)
            if isinstance(text, list):
                text = "".join(
                    p.get("text", "") if isinstance(p, dict) else str(p)
                    for p in text
                )
            return _parse_judge_json(text)

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                reraise=True,
            ):
                with attempt:
                    return await _call()
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "judge_call_failed",
                error=str(exc),
                record_id=record.record_id,
            )
            return 0.0, "judge_failed"
        return 0.0, "judge_failed"  # pragma: no cover — defensive

    async def judge_batch(
        self, records: list[PipelineRecord]
    ) -> list[tuple[float, str]]:
        """Judge many records concurrently (max 5 in flight).

        Returns a list in the same order as *records*.
        """
        if not records:
            return []
        sem = asyncio.Semaphore(_MAX_CONCURRENCY)

        async def _one(rec: PipelineRecord) -> tuple[float, str]:
            async with sem:
                return await self.judge(rec)

        return await asyncio.gather(*(_one(r) for r in records))
