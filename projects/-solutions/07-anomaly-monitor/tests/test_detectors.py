"""Tests for the statistical, LLM-stub, and ensemble detectors.

All tests run without external dependencies (no OpenAI API calls). The LLM
detector uses its built-in rule-based stub when no API key is configured.
The ensemble tests inject fake sub-detectors to verify the fusion math.
"""

from __future__ import annotations

import pytest

from anomaly_monitor.config import Severity, Settings
from anomaly_monitor.detection.ensemble import EnsembleDetector
from anomaly_monitor.detection.llm_detector import LLMAnomalyDetector
from anomaly_monitor.detection.statistical import StatisticalDetector
from anomaly_monitor.models import AnomalyScore, Window


def _make_window(
    count: int = 10,
    error_count: int = 0,
    unique_sources: int = 1,
    latency_p95: float = 50.0,
    duration_sec: int = 60,
) -> Window:
    """Build a Window with the given aggregate stats for detector tests."""
    start_ts = 1_000_000.0
    return Window(
        window_id=f"{duration_sec}s:{int(start_ts // duration_sec)}",
        duration_sec=duration_sec,
        start_ts=start_ts,
        end_ts=start_ts + duration_sec,
        count=count,
        error_count=error_count,
        unique_sources=unique_sources,
        latency_p95=latency_p95,
    )


# ---------------------------------------------------------------------------
# StatisticalDetector
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_statistical_detector_normal_window() -> None:
    """A normal-looking window on a fresh detector is not anomalous."""
    det = StatisticalDetector()
    win = _make_window(count=10, error_count=0, unique_sources=2, latency_p95=50.0)
    score = await det.detect(win)
    assert score.detector == "statistical"
    assert score.is_anomaly is False
    assert score.probability < 0.5
    await det.aclose()


@pytest.mark.asyncio
async def test_statistical_detector_spike_window() -> None:
    """A count=500 / error_rate=0.5 window is flagged anomalous after baseline."""
    det = StatisticalDetector()
    # Pre-populate the baseline with normal (varied) windows so the z-score
    # of a spike is large. Use varying counts so std > 0.
    for c in (8, 12, 10, 9, 11, 10, 8, 12, 10, 11):
        det.update_baseline(_make_window(count=c, error_count=0))

    spike = _make_window(count=500, error_count=250, unique_sources=3, latency_p95=200.0)
    score = await det.detect(spike)
    assert score.is_anomaly is True
    assert score.probability >= 0.5
    await det.aclose()


# ---------------------------------------------------------------------------
# LLMAnomalyDetector (stub mode)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_llm_detector_stub_mode() -> None:
    """With no API key, the LLM detector still returns an AnomalyScore."""
    s = Settings(openai_api_key="")
    assert s.llm_enabled is False
    det = LLMAnomalyDetector(settings=s)
    win = _make_window(count=100, error_count=60)
    score = await det.detect(win)
    assert score.detector == "llm"
    assert 0.0 <= score.probability <= 1.0
    assert isinstance(score.is_anomaly, bool)
    await det.aclose()


# ---------------------------------------------------------------------------
# EnsembleDetector — with injected fake sub-detectors
# ---------------------------------------------------------------------------
class _FakeDetector:
    """Minimal duck-typed detector for ensemble injection."""

    def __init__(self, prob: float, name: str = "fake") -> None:
        self._prob = prob
        self._name = name

    async def detect(self, window: Window) -> AnomalyScore:
        return AnomalyScore(
            detector=self._name,
            is_anomaly=self._prob >= 0.5,
            probability=self._prob,
            severity=Severity.CRITICAL if self._prob >= 0.9 else Severity.INFO,
            reason=f"fake({self._name})",
            contributing_features={"fake_prob": self._prob},
            window_id=window.window_id,
        )

    async def aclose(self) -> None:
        pass


@pytest.mark.asyncio
async def test_ensemble_combines_both() -> None:
    """Stat verdict 0.9 + LLM verdict 0.8 → weighted ~0.84, is_anomaly True."""
    s = Settings(stat_weight=0.4, llm_weight=0.6)
    ens = EnsembleDetector(
        settings=s,
        statistical=_FakeDetector(0.9, "stat"),  # type: ignore[arg-type]
        llm=_FakeDetector(0.8, "llm"),  # type: ignore[arg-type]
    )
    win = _make_window()
    score = await ens.detect(win)
    # weighted: (0.4 * 0.9 + 0.6 * 0.8) / 1.0 = 0.84
    assert abs(score.probability - 0.84) < 0.01
    assert score.is_anomaly is True
    await ens.aclose()


@pytest.mark.asyncio
async def test_ensemble_below_threshold_not_anomaly() -> None:
    """Both sub-detectors return 0.2 → ensemble is_anomaly False."""
    s = Settings(stat_weight=0.4, llm_weight=0.6, ensemble_threshold=0.5)
    ens = EnsembleDetector(
        settings=s,
        statistical=_FakeDetector(0.2, "stat"),  # type: ignore[arg-type]
        llm=_FakeDetector(0.2, "llm"),  # type: ignore[arg-type]
    )
    win = _make_window()
    score = await ens.detect(win)
    assert score.probability < 0.5
    assert score.is_anomaly is False
    await ens.aclose()
