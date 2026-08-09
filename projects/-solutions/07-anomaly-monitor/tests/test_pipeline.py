"""End-to-end smoke test for the AnomalyPipeline in synthetic local mode.

Runs the full pipeline (stream → window → detect → respond → feedback) with
a bounded SyntheticStreamConsumer (max_events=20) and asserts that the
Prometheus ``EVENTS_PROCESSED`` counter incremented and no exceptions were
raised. No external services are required.
"""

from __future__ import annotations

import pytest

from anomaly_monitor.config import Mode, Settings
from anomaly_monitor.streaming.synthetic_source import SyntheticStreamConsumer


@pytest.mark.asyncio
async def test_pipeline_runs_few_events(monkeypatch, tmp_path) -> None:
    """Process 20 synthetic events through the full pipeline without errors."""
    from prometheus_client import REGISTRY

    from anomaly_monitor.observability.metrics import EVENTS_PROCESSED  # noqa: F401
    from anomaly_monitor.pipeline import AnomalyPipeline

    s = Settings(
        mode=Mode.LOCAL,
        feedback_db=str(tmp_path / "feedback.db"),
        prometheus_port=0,
        synthetic_events_per_sec=100.0,
        synthetic_anomaly_rate=0.0,
        openai_api_key="",
    )

    before = REGISTRY.get_sample_value("anomaly_events_processed_total") or 0

    # Patch _build_consumer so the pipeline uses a bounded synthetic source.
    def _fake_build_consumer(settings):
        return SyntheticStreamConsumer(settings=settings, max_events=20, seed=42)

    monkeypatch.setattr("anomaly_monitor.pipeline._build_consumer", _fake_build_consumer)

    pipeline = AnomalyPipeline(settings=s)
    # run() calls start() → consume loop → stop(). If it returns without
    # raising, no exceptions occurred during processing.
    await pipeline.run()

    after = REGISTRY.get_sample_value("anomaly_events_processed_total") or 0
    assert after - before >= 20
