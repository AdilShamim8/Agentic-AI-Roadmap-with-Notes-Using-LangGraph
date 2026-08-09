"""Statistical detector — z-score + Isolation Forest fusion.

Computes z-scores over ``window.count`` and ``window.error_rate`` against
a rolling baseline of the last ``baseline_size`` windows, and runs an
Isolation Forest over the feature vector ``[count, error_rate,
unique_sources, latency_p95]``. The two flags are combined into a single
anomaly probability.

Degrades gracefully to z-score-only if scikit-learn / numpy are missing.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Optional

import structlog

from anomaly_monitor.config import Settings, settings as _default_settings
from anomaly_monitor.detection.base import Detector
from anomaly_monitor.models import AnomalyScore, Severity, Window

log = structlog.get_logger()

# Lazy-import heavy deps at module top-level; degrade if unavailable.
try:  # pragma: no cover - exercised only in environments without sklearn
    import numpy as np  # type: ignore
    from sklearn.ensemble import IsolationForest  # type: ignore

    _HAS_SKLEARN = True
except ImportError as _exc:  # pragma: no cover
    _HAS_SKLEARN = False
    np = None  # type: ignore
    IsolationForest = None  # type: ignore
    log.warning("statistical_detector_sklearn_unavailable_zscore_only", error=str(_exc))


def _severity_for(prob: float) -> Severity:
    """Map a probability in [0, 1] to a :class:`Severity` bucket."""
    if prob >= 0.9:
        return Severity.CRITICAL
    if prob >= 0.75:
        return Severity.HIGH
    if prob >= 0.5:
        return Severity.WARNING
    return Severity.INFO


def _zscore(value: float, baseline: list[float]) -> float:
    """Return the standard z-score of ``value`` against ``baseline``.

    Returns 0.0 when the baseline has fewer than 2 samples or when its
    standard deviation is zero. Uses numpy when available, else falls
    back to pure-python mean/std.
    """
    if len(baseline) < 2:
        return 0.0
    if _HAS_SKLEARN:
        arr = np.asarray(baseline, dtype=float)  # type: ignore[union-attr]
        mean = float(arr.mean())
        std = float(arr.std())
    else:
        n = len(baseline)
        mean = sum(baseline) / n
        var = sum((v - mean) ** 2 for v in baseline) / n
        std = var ** 0.5
    if std == 0.0:
        return 0.0
    return (value - mean) / std


class StatisticalDetector(Detector):
    """Z-score + Isolation Forest anomaly detector over a single window."""

    name = "statistical"

    def __init__(
        self,
        settings: Optional[Settings] = None,
        baseline_size: int = 50,
        if_buffer_size: int = 100,
        refit_every: int = 20,
    ) -> None:
        """Configure thresholds & rolling buffers.

        Args:
            settings: project settings (defaults to the global ``settings``).
            baseline_size: number of past windows feeding the z-score baseline.
            if_buffer_size: max feature vectors kept for Isolation Forest fits.
            refit_every: re-fit the Isolation Forest every N ``detect`` calls.
        """
        self._settings = settings or _default_settings
        self._baseline_size = baseline_size
        self._if_buffer_size = if_buffer_size
        self._refit_every = refit_every

        self._count_baseline: deque[float] = deque(maxlen=baseline_size)
        self._err_baseline: deque[float] = deque(maxlen=baseline_size)
        self._feature_buffer: deque[list[float]] = deque(maxlen=if_buffer_size)

        self._if_model: Optional[Any] = None  # IsolationForest
        self._calls_since_fit = 0

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def update_baseline(self, window: Window) -> None:
        """Push a window's count/error_rate into the rolling baseline."""
        self._count_baseline.append(float(window.count))
        self._err_baseline.append(float(window.error_rate))

    def _features(self, window: Window) -> list[float]:
        """Build the Isolation Forest feature vector for a window."""
        return [
            float(window.count),
            float(window.error_rate),
            float(window.unique_sources),
            float(window.latency_p95),
        ]

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    async def detect(self, window: Window) -> AnomalyScore:
        """Score the window by combining z-score and Isolation Forest flags."""
        feats = self._features(window)

        z_count = _zscore(feats[0], list(self._count_baseline))
        z_err = _zscore(feats[1], list(self._err_baseline))
        max_z = max(abs(z_count), abs(z_err))
        z_flag = max_z > self._settings.zscore_threshold

        if_flag = self._run_isolation_forest(feats) if _HAS_SKLEARN else False

        if z_flag and if_flag:
            prob = 0.95
        elif z_flag:
            prob = 0.7
        elif if_flag:
            prob = 0.6
        else:
            prob = 0.05

        # Self-update baselines & IF buffer for the next call.
        self.update_baseline(window)
        self._feature_buffer.append(feats)

        triggers: list[str] = []
        if z_flag:
            triggers.append(
                f"zscore(count={z_count:.2f},err={z_err:.2f})>"
                f"{self._settings.zscore_threshold}"
            )
        if if_flag:
            triggers.append("isolation_forest=-1")
        reason = "anomaly: " + ", ".join(triggers) if triggers else "no anomaly"

        return AnomalyScore(
            detector=self.name,
            is_anomaly=prob >= 0.5,
            probability=prob,
            severity=_severity_for(prob),
            reason=reason,
            contributing_features={
                "count": feats[0],
                "error_rate": feats[1],
                "unique_sources": feats[2],
                "latency_p95": feats[3],
                "z_count": z_count,
                "z_error_rate": z_err,
            },
            window_id=window.window_id,
        )

    def _run_isolation_forest(self, feats: list[float]) -> bool:
        """Predict with Isolation Forest; refit periodically. True if anomalous."""
        if len(self._feature_buffer) < 4:
            return False
        self._calls_since_fit += 1
        if self._if_model is None or self._calls_since_fit >= self._refit_every:
            try:
                self._if_model = IsolationForest(  # type: ignore[misc]
                    contamination=self._settings.isolation_contamination,
                    random_state=42,
                    n_estimators=50,
                )
                self._if_model.fit(np.asarray(self._feature_buffer, dtype=float))  # type: ignore[union-attr]
                self._calls_since_fit = 0
            except Exception as exc:  # noqa: BLE001
                log.warning("isolation_forest_fit_failed", error=str(exc))
                self._if_model = None
                return False
        if self._if_model is None:
            return False
        try:
            pred = int(self._if_model.predict(np.asarray([feats], dtype=float))[0])  # type: ignore[union-attr]
            return pred == -1
        except Exception as exc:  # noqa: BLE001
            log.warning("isolation_forest_predict_failed", error=str(exc))
            return False

    async def aclose(self) -> None:
        """Drop the Isolation Forest model and clear buffers."""
        self._if_model = None
        self._feature_buffer.clear()
        self._count_baseline.clear()
        self._err_baseline.clear()
