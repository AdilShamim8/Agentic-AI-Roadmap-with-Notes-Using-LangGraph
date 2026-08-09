"""LLM-backed anomaly detector with a rule-based stub fallback.

When ``settings.llm_enabled`` is False (no OpenAI key configured) the
detector falls back to a deterministic rule-based stub so the pipeline
still runs end-to-end. When enabled, it prompts ``gpt-4o-mini``
(temperature=0) for a strict-JSON verdict and wraps the call in
``tenacity`` retries (3 attempts, exponential backoff starting at 1s).
On final failure it returns ``reason="llm_unavailable"``.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import structlog

from anomaly_monitor.config import Settings, settings as _default_settings
from anomaly_monitor.detection.base import Detector
from anomaly_monitor.models import AnomalyScore, Severity, Window

log = structlog.get_logger()

_SYSTEM_PROMPT = (
    "You are an expert site-reliability engineer analysing a single time "
    "window of telemetry. Anomalies include sudden rate changes (count far "
    "above the baseline mean), error-rate spikes (>0.3), unusual source "
    "diversity, or latency regressions. Respond ONLY with strict JSON of "
    'shape: {"is_anomaly": bool, "probability": float in [0,1], '
    '"reason": string}. No prose, no markdown fences.'
)


def _severity_for(prob: float) -> Severity:
    """Map a probability in [0, 1] to a :class:`Severity` bucket."""
    if prob >= 0.9:
        return Severity.CRITICAL
    if prob >= 0.75:
        return Severity.HIGH
    if prob >= 0.5:
        return Severity.WARNING
    return Severity.INFO


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _parse_llm_json(text: Any) -> dict[str, Any]:
    """Parse the LLM response into a dict, tolerating markdown fences."""
    if isinstance(text, list):
        text = "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in text
        )
    raw = str(text).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass
        log.warning("llm_detector_bad_json", text=raw[:200])
        return {"is_anomaly": False, "probability": 0.0, "reason": "bad_json"}


class LLMAnomalyDetector(Detector):
    """LLM (or rule-based stub) anomaly detector."""

    name = "llm"

    def __init__(
        self,
        settings: Optional[Settings] = None,
        baseline_size: int = 50,
    ) -> None:
        """Initialise the detector.

        Args:
            settings: project settings (defaults to global ``settings``).
            baseline_size: how many past window counts to remember for the
                stub's baseline-mean-count comparison.
        """
        self._settings = settings or _default_settings
        self._baseline_size = baseline_size
        # Duration-keyed baselines so 1m and 5m windows don't pollute each other.
        self._count_baselines: dict[int, list[float]] = {}
        self._llm: Optional[Any] = None  # langchain_openai.ChatOpenAI
        if self._settings.llm_enabled:
            try:
                from langchain_openai import ChatOpenAI  # type: ignore

                self._llm = ChatOpenAI(
                    model=self._settings.llm_model,
                    temperature=self._settings.llm_temperature,
                    timeout=self._settings.llm_timeout_sec,
                    openai_api_key=self._settings.openai_api_key,
                    openai_api_base=self._settings.openai_base_url,
                )
                log.info("llm_detector_ready", model=self._settings.llm_model)
            except Exception as exc:  # noqa: BLE001
                log.warning("llm_detector_init_failed_using_stub", error=str(exc))
                self._llm = None
        else:
            log.info("llm_detector_disabled_using_stub")

    # ------------------------------------------------------------------
    # Baseline (used by the stub path & surfaced to the LLM prompt)
    # ------------------------------------------------------------------
    def update_baseline(self, window: Window) -> None:
        """Append a window's count to the duration-keyed rolling baseline."""
        dur = window.duration_sec
        bl = self._count_baselines.setdefault(dur, [])
        bl.append(float(window.count))
        if len(bl) > self._baseline_size:
            del bl[: len(bl) - self._baseline_size]

    def _baseline_mean_count(self, duration_sec: Optional[int] = None) -> float:
        """Return the mean baseline count for the given window duration.

        If ``duration_sec`` is None, returns 0.0 (no baseline)."""
        if duration_sec is None:
            return 0.0
        bl = self._count_baselines.get(duration_sec, [])
        if not bl:
            return 0.0
        return sum(bl) / len(bl)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    async def detect(self, window: Window) -> AnomalyScore:
        """Score the window via the LLM, or via the stub if LLM is off."""
        mean_count = self._baseline_mean_count(window.duration_sec)
        if self._llm is None:
            score = self._stub_detect(window, mean_count)
        else:
            score = await self._llm_detect(window, mean_count)
        self.update_baseline(window)  # update AFTER scoring to avoid self-bias
        score.window_id = window.window_id
        return score

    def _stub_detect(self, window: Window, mean_count: float) -> AnomalyScore:
        """Deterministic rule-based fallback used when the LLM is unavailable.

        Flags as anomalous if **any** of:
          - error_rate > 0.3 (error burst)
          - count > 2.0 × baseline mean (rate spike — lowered from 5× so short
            bursts inside a 60s window still register)
          - unique_sources > 10 (unusual source diversity)
        Probability is a soft blend of all three signals.
        """
        err = window.error_rate
        ratio = (window.count / mean_count) if mean_count > 0 else 0.0
        srcs = window.unique_sources
        err_flag = err > 0.3
        rate_flag = mean_count > 0 and window.count > 2.0 * mean_count
        src_flag = srcs > 10
        is_anom = bool(err_flag or rate_flag or src_flag)
        prob = _clamp(err * 1.5 + max(0.0, ratio - 1.0) * 0.4 + max(0.0, srcs - 5) * 0.02)
        if not is_anom and prob >= 0.5:
            prob = 0.05  # don't flag non-anomalies as anomalies from the clamp
        flags = []
        if err_flag:
            flags.append(f"error_rate={err:.3f}")
        if rate_flag:
            flags.append(f"count_ratio={ratio:.2f}")
        if src_flag:
            flags.append(f"unique_sources={srcs}")
        reason = "stub: " + (", ".join(flags) if flags else "normal")
        return AnomalyScore(
            detector=self.name,
            is_anomaly=is_anom,
            probability=prob,
            severity=_severity_for(prob),
            reason=reason,
            contributing_features={
                "error_rate": float(err),
                "count": float(window.count),
                "baseline_mean_count": mean_count,
                "count_ratio": ratio,
                "unique_sources": float(srcs),
            },
        )

    async def _llm_detect(self, window: Window, mean_count: float) -> AnomalyScore:
        """Call the LLM with retries; on final failure return a safe score."""
        try:
            from langchain_core.messages import (  # type: ignore
                HumanMessage,
                SystemMessage,
            )
            from tenacity import (  # type: ignore
                AsyncRetrying,
                stop_after_attempt,
                wait_exponential,
            )
        except ImportError as exc:  # pragma: no cover
            log.warning("llm_detector_deps_missing_using_stub", error=str(exc))
            return self._stub_detect(window, mean_count)

        user_payload = (
            f"Window id={window.window_id} duration={window.duration_sec}s "
            f"count={window.count} error_rate={window.error_rate:.4f} "
            f"unique_sources={window.unique_sources} "
            f"latency_p95={window.latency_p95:.2f} "
            f"baseline_mean_count={mean_count:.2f}"
        )
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_payload),
        ]

        async def _call() -> dict[str, Any]:
            resp = await self._llm.ainvoke(messages)  # type: ignore[union-attr]
            content = getattr(resp, "content", resp)
            return _parse_llm_json(content)

        try:
            verdict: dict[str, Any] = {}
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                reraise=True,
            ):
                with attempt:
                    verdict = await _call()
            return self._score_from_verdict(verdict, window, mean_count)
        except Exception as exc:  # noqa: BLE001
            log.warning("llm_detector_unavailable", error=str(exc))
            return AnomalyScore(
                detector=self.name,
                is_anomaly=False,
                probability=0.0,
                severity=Severity.INFO,
                reason="llm_unavailable",
                contributing_features={
                    "error_rate": float(window.error_rate),
                    "count": float(window.count),
                },
                window_id=window.window_id,
            )

    def _score_from_verdict(
        self, verdict: dict[str, Any], window: Window, mean_count: float
    ) -> AnomalyScore:
        """Convert the parsed LLM JSON dict into an :class:`AnomalyScore`."""
        is_anom = bool(verdict.get("is_anomaly", False))
        prob = _clamp(float(verdict.get("probability", 0.0)))
        reason = str(verdict.get("reason", ""))[:500]
        return AnomalyScore(
            detector=self.name,
            is_anomaly=is_anom,
            probability=prob,
            severity=_severity_for(prob),
            reason=reason or "llm verdict",
            contributing_features={
                "error_rate": float(window.error_rate),
                "count": float(window.count),
                "baseline_mean_count": mean_count,
            },
        )

    async def aclose(self) -> None:
        """Release the LLM client (best-effort)."""
        self._llm = None
        self._count_baselines.clear()
