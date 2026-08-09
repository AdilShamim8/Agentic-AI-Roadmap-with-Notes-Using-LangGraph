"""Ensemble detector — combines statistical + LLM detectors.

The ensemble runs :class:`StatisticalDetector` and
:class:`LLMAnomalyDetector` concurrently via :func:`asyncio.gather` and
fuses their probabilities with configurable weights, taking the more
severe of the two sub-scores as the combined severity.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import structlog

from anomaly_monitor.config import Settings, settings as _default_settings
from anomaly_monitor.detection.base import Detector
from anomaly_monitor.detection.llm_detector import LLMAnomalyDetector
from anomaly_monitor.detection.statistical import StatisticalDetector
from anomaly_monitor.models import AnomalyScore, Severity, Window

log = structlog.get_logger()


class EnsembleDetector(Detector):
    """Combine statistical + LLM detectors into a single fused verdict."""

    name = "ensemble"

    def __init__(
        self,
        settings: Optional[Settings] = None,
        statistical: Optional[StatisticalDetector] = None,
        llm: Optional[LLMAnomalyDetector] = None,
    ) -> None:
        """Build the ensemble.

        Args:
            settings: project settings (defaults to global ``settings``).
            statistical: injected statistical detector (created if omitted —
                useful for tests that want to substitute a mock).
            llm: injected LLM detector (created if omitted).
        """
        self._settings = settings or _default_settings
        self._stat = statistical or StatisticalDetector(self._settings)
        self._llm = llm or LLMAnomalyDetector(self._settings)

    async def detect(self, window: Window) -> AnomalyScore:
        """Run both sub-detectors concurrently and fuse their scores.

        - ``combined_prob = (stat_weight*stat.prob + llm_weight*llm.prob) / total_weight``
        - ``is_anomaly = combined_prob >= settings.ensemble_threshold``
        - ``severity`` = the more severe of the two sub-scores
        - ``reason`` = ``"stat: {stat.reason} | llm: {llm.reason}"``
        - ``contributing_features`` = merge of both
        """
        stat_score, llm_score = await asyncio.gather(
            self._stat.detect(window),
            self._llm.detect(window),
        )

        stat_w = self._settings.stat_weight
        llm_w = self._settings.llm_weight
        total = stat_w + llm_w
        if total <= 0:  # defensive: never divide by zero
            stat_w, llm_w, total = 1.0, 0.0, 1.0
        combined_prob = (stat_w * stat_score.probability + llm_w * llm_score.probability) / total
        combined_prob = max(0.0, min(1.0, combined_prob))

        is_anom = combined_prob >= self._settings.ensemble_threshold
        severity = self._max_severity(stat_score.severity, llm_score.severity)

        contributing = {
            **stat_score.contributing_features,
            **llm_score.contributing_features,
        }
        reason = f"stat: {stat_score.reason} | llm: {llm_score.reason}"

        return AnomalyScore(
            detector=self.name,
            is_anomaly=is_anom,
            probability=combined_prob,
            severity=severity,
            reason=reason,
            contributing_features=contributing,
            window_id=window.window_id,
        )

    @staticmethod
    def _max_severity(a: Severity, b: Severity) -> Severity:
        """Return the more severe of two :class:`Severity` values.

        Uses the ordering defined on :class:`Severity` itself (``__gt__``);
        falls back to the explicit ``order`` list if comparison raises.
        """
        try:
            return a if a >= b else b
        except Exception:  # pragma: no cover - defensive only
            order = [
                Severity.INFO,
                Severity.WARNING,
                Severity.HIGH,
                Severity.CRITICAL,
            ]
            return a if order.index(a) >= order.index(b) else b

    async def aclose(self) -> None:
        """Close both sub-detectors (best-effort)."""
        await asyncio.gather(
            self._stat.aclose(),
            self._llm.aclose(),
            return_exceptions=True,
        )
