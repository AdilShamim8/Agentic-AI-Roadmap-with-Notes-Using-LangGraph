"""End-to-end async pipeline that wires every layer together.

The pipeline consumes events from a stream, builds tumbling windows, runs the
ensemble detector on each window, and feeds any flagged anomalies into the
LangGraph response agent. All steps are traced (LangSmith) and metered
(Prometheus).

Designed to be the single entry point for both local and Kafka modes — the
only difference is the stream source and whether Redis is used.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

import structlog

from anomaly_monitor.aggregation.windower import Windower
from anomaly_monitor.config import Mode, Settings, settings as default_settings
from anomaly_monitor.detection.ensemble import EnsembleDetector
from anomaly_monitor.detection.llm_detector import LLMAnomalyDetector
from anomaly_monitor.detection.statistical import StatisticalDetector
from anomaly_monitor.feedback.store import FeedbackStore
from anomaly_monitor.observability.metrics import (
    ANOMALIES_DETECTED,
    CONSUMER_LAG,
    DETECTOR_SCORE,
    EVENTS_PROCESSED,
    HITL_DECISIONS,
    PIPELINE_RUNNING,
    RESPONSE_LATENCY,
    WINDOWS_BUILT,
    MetricsServer,
)
from anomaly_monitor.observability.tracing import configure_tracing, traced
from anomaly_monitor.response.graph import ResponseGraph
from anomaly_monitor.response.hitl import HITLManager

log = structlog.get_logger()


def _build_consumer(settings: Settings):
    """Build the appropriate stream consumer based on settings.mode."""
    if settings.mode == Mode.KAFKA:
        from anomaly_monitor.streaming.kafka_consumer import KafkaStreamConsumer

        return KafkaStreamConsumer(settings=settings)
    # local / default
    from anomaly_monitor.streaming.synthetic_source import SyntheticStreamConsumer

    return SyntheticStreamConsumer(settings=settings)


class AnomalyPipeline:
    """End-to-end pipeline orchestrating every layer."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or default_settings
        configure_tracing(self._settings)

        # Components are constructed lazily in `start()` so the pipeline can be
        # instantiated cheaply (e.g. for tests or for `--help`).
        self.windower: Optional[Windower] = None
        self.detector: Optional[EnsembleDetector] = None
        self.response_graph: Optional[ResponseGraph] = None
        self.feedback_store: Optional[FeedbackStore] = None
        self.metrics_server: Optional[MetricsServer] = None
        self._consumer = None
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Initialise all components."""
        s = self._settings
        log.info("pipeline_starting", mode=s.mode.value, llm_enabled=s.llm_enabled)

        # Windower (Redis or in-memory)
        self.windower = Windower(settings=s)
        await self.windower.start()

        # Detectors
        stat = StatisticalDetector(settings=s)
        llm = LLMAnomalyDetector(settings=s)
        self.detector = EnsembleDetector(settings=s, statistical=stat, llm=llm)

        # Response agent (LangGraph)
        hitl = HITLManager(settings=s)
        self.response_graph = ResponseGraph(settings=s, hitl=hitl)

        # Feedback
        self.feedback_store = FeedbackStore(settings=s)
        await self.feedback_store.start()

        # Metrics
        self.metrics_server = MetricsServer(port=s.prometheus_port)
        self.metrics_server.start()
        PIPELINE_RUNNING.set(1)

        # Stream consumer
        self._consumer = _build_consumer(s)

        log.info("pipeline_ready")

    async def stop(self) -> None:
        """Tear down all components."""
        log.info("pipeline_stopping")
        self._stop_event.set()
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

        if self._consumer is not None:
            await self._consumer.aclose()
        if self.windower is not None:
            await self.windower.aclose()
        if self.detector is not None:
            await self.detector.aclose()
        if self.feedback_store is not None:
            await self.feedback_store.aclose()

        if self.metrics_server is not None:
            self.metrics_server.stop()
        PIPELINE_RUNNING.set(0)
        log.info("pipeline_stopped")

    async def run(self) -> None:
        """Run the pipeline until cancelled or stop() is called."""
        await self.start()
        assert self._consumer is not None
        assert self.windower is not None
        assert self.detector is not None
        assert self.response_graph is not None

        # Background task: expire old windows every 60s.
        self._tasks.append(asyncio.create_task(self._expire_loop()))

        try:
            async for event in self._consumer.events():
                if self._stop_event.is_set():
                    break
                EVENTS_PROCESSED.inc()
                CONSUMER_LAG.set(time.time() - event.ts)

                windows = await self.windower.add_event(event)
                # Score each window the event landed in.
                for dur, window in windows.items():
                    WINDOWS_BUILT.labels(window=dur).inc()
                    await self._score_and_respond(window)
        finally:
            await self.stop()

    async def _expire_loop(self) -> None:
        """Periodically expire old windows so the baseline doesn't grow unbounded."""
        assert self.windower is not None
        while not self._stop_event.is_set():
            try:
                n = await self.windower.expire_old()
                if n > 0:
                    log.debug("windows_expired", count=n)
            except Exception as exc:  # pragma: no cover - defensive
                log.warning("expire_failed", error=str(exc))
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=60.0)
            except asyncio.TimeoutError:
                continue

    @traced("pipeline.score_and_respond")
    async def _score_and_respond(self, window) -> None:
        """Run the detector on a window; if anomalous, run the response graph."""
        assert self.detector is not None
        assert self.response_graph is not None
        assert self.feedback_store is not None

        detect_t0 = time.time()
        try:
            score = await self.detector.detect(window)
        except Exception as exc:  # pragma: no cover - defensive
            log.error("detector_failed", error=str(exc), window_id=window.window_id)
            return

        DETECTOR_SCORE.labels(detector=score.detector).observe(score.probability)

        if not score.is_anomaly:
            log.debug(
                "window_scored_normal",
                window_id=window.window_id,
                prob=round(score.probability, 3),
            )
            return

        ANOMALIES_DETECTED.labels(
            kind=score.detector, severity=score.severity.value
        ).inc()
        log.warning(
            "anomaly_detected",
            window_id=window.window_id,
            detector=score.detector,
            prob=round(score.probability, 3),
            severity=score.severity.value,
            reason=score.reason,
        )

        # Run the LangGraph response agent.
        try:
            state = await self.response_graph.run(window, score)
        except Exception as exc:  # pragma: no cover - defensive
            log.error("response_graph_failed", error=str(exc))
            return

        response_t = time.time()
        latency = response_t - detect_t0
        RESPONSE_LATENCY.observe(latency)

        approved = state.get("approved")
        if approved is not None:
            HITL_DECISIONS.labels(
                decision="approved" if approved else "denied"
            ).inc()

        proposed = state.get("proposed_action")
        result = state.get("result")
        log.info(
            "response_complete",
            window_id=window.window_id,
            action=getattr(proposed, "kind", None),
            severity=getattr(proposed, "severity", None),
            success=getattr(result, "success", None),
            output=getattr(result, "output", "")[:200],
            latency_sec=round(latency, 3),
            trace=state.get("trace", []),
        )

        # Best-effort feedback record (auto — operator can correct later).
        from anomaly_monitor.models import Feedback

        try:
            await self.feedback_store.record(
                Feedback(
                    anomaly_id=f"{window.window_id}:{score.detector}",
                    is_real_anomaly=True,  # tentative; operator can correct via CLI subcommand
                    action_correct=getattr(result, "success", None),
                    operator_note="auto-recorded",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("feedback_record_failed", error=str(exc))
