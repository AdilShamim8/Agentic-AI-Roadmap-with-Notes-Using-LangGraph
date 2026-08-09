"""Prometheus metrics for the anomaly-monitor pipeline.

Exposes module-level `Counter`/`Histogram`/`Gauge` instances plus a
`MetricsServer` that runs the prometheus HTTP server in a background thread.

Degrades to no-op stand-ins (``_NoopMetric``) if ``prometheus_client`` is not
installed, so the rest of the pipeline can keep calling ``.inc()`` /
``.observe()`` / ``.set()`` without crashing.
"""

from __future__ import annotations

from typing import Any

import structlog

log = structlog.get_logger()

# Lazy-import heavy deps at module top-level; degrade if unavailable.
try:  # pragma: no cover - exercised only without prometheus_client
    from prometheus_client import Counter, Gauge, Histogram, start_http_server

    _HAS_PROM = True
except ImportError:  # pragma: no cover
    _HAS_PROM = False
    log.warning("prometheus_client_unavailable_using_noop_metrics")


class _NoopMetric:
    """Drop-in stand-in for any prometheus metric when the lib is missing."""

    __slots__ = ()

    def labels(self, *args: Any, **kwargs: Any) -> "_NoopMetric":
        return self

    def inc(self, *args: Any, **kwargs: Any) -> None:
        pass

    def observe(self, *args: Any, **kwargs: Any) -> None:
        pass

    def set(self, *args: Any, **kwargs: Any) -> None:
        pass


if _HAS_PROM:
    EVENTS_PROCESSED = Counter(
        "anomaly_events_processed_total", "Total events consumed"
    )
    WINDOWS_BUILT = Counter(
        "anomaly_windows_total", "Windows built", ["window"]
    )
    ANOMALIES_DETECTED = Counter(
        "anomaly_detected_total", "Anomalies flagged", ["kind", "severity"]
    )
    RESPONSE_LATENCY = Histogram(
        "anomaly_response_latency_seconds",
        "End-to-end anomaly to response latency",
        buckets=(0.5, 1, 2, 5, 10, 20, 30, 60),
    )
    HITL_DECISIONS = Counter(
        "anomaly_hitl_decisions_total", "HITL decisions", ["decision"]
    )
    DETECTOR_SCORE = Histogram(
        "anomaly_detector_probability",
        "Detector probability scores",
        ["detector"],
    )
    CONSUMER_LAG = Gauge(
        "anomaly_consumer_lag_seconds", "Consumer lag in seconds"
    )
    PIPELINE_RUNNING = Gauge(
        "anomaly_pipeline_running", "1 if pipeline is running"
    )
else:
    EVENTS_PROCESSED = _NoopMetric()  # type: ignore[assignment]
    WINDOWS_BUILT = _NoopMetric()  # type: ignore[assignment]
    ANOMALIES_DETECTED = _NoopMetric()  # type: ignore[assignment]
    RESPONSE_LATENCY = _NoopMetric()  # type: ignore[assignment]
    HITL_DECISIONS = _NoopMetric()  # type: ignore[assignment]
    DETECTOR_SCORE = _NoopMetric()  # type: ignore[assignment]
    CONSUMER_LAG = _NoopMetric()  # type: ignore[assignment]
    PIPELINE_RUNNING = _NoopMetric()  # type: ignore[assignment]


class MetricsServer:
    """Runs prometheus_client's HTTP server in a background thread."""

    def __init__(self, port: int):
        self._port = port
        self._started = False

    def start(self) -> None:
        """Start prometheus_client HTTP server in a background thread."""
        if not _HAS_PROM:
            log.warning("metrics_server_skipped_prometheus_unavailable")
            return
        if self._started:
            return
        try:
            start_http_server(self._port)
            self._started = True
            log.info("metrics_server_started", port=self._port)
        except Exception as e:  # pragma: no cover - defensive
            log.error(
                "metrics_server_start_failed",
                error=str(e),
                port=self._port,
            )

    def stop(self) -> None:
        """Best-effort stop.

        ``prometheus_client.start_http_server`` runs a daemon thread that
        cannot be cleanly joined from the public API; we just mark the server
        as not-started so it can be restarted if needed. The daemon thread
        will exit with the process.
        """
        if not self._started:
            return
        self._started = False
        log.info("metrics_server_stopped", port=self._port)
