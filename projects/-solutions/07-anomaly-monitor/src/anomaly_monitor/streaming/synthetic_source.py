"""Synthetic event source for local / demo / load-test mode.

Generates a Poisson-arriving stream of mostly-normal events with
occasional injected anomalies (rate spikes, error bursts, unusual
sources) so that downstream detectors have something realistic to find.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import AsyncIterator, Optional

import structlog

from anomaly_monitor.config import Settings, settings as _default_settings
from anomaly_monitor.models import Event
from anomaly_monitor.streaming.base import StreamConsumer

log = structlog.get_logger()

# A small pool of plausible hostnames / event types for "normal" traffic.
_HOSTS = [f"host-{i}" for i in range(1, 6)]
_EVENT_TYPES = ["http_request", "db_query", "cache_lookup", "background_job"]
_SEVERITIES = ["info", "info", "info", "info", "warning"]  # weighted normal


class SyntheticStreamConsumer(StreamConsumer):
    """Generate a synthetic, Poisson-arriving stream of :class:`Event` objects.

    By default the stream runs forever. Pass ``max_events`` to stop after a
    fixed number of events (useful in tests). Anomalies are injected at
    ``settings.synthetic_anomaly_rate`` and tagged with
    ``is_anomaly=True`` and a descriptive ``anomaly_kind``.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        max_events: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> None:
        """Configure the synthetic source.

        Args:
            settings: Project settings (defaults to the global ``settings``).
            max_events: If set, stop after yielding this many events.
            seed: Optional RNG seed for deterministic output (useful in tests).
        """
        self._settings = settings or _default_settings
        self._max_events = max_events
        self._rng = random.Random(seed)
        self._closed = False

    # ---- internal helpers -------------------------------------------------

    def _normal_event(self) -> Event:
        """Build a typical, non-anomalous event."""
        sev = self._rng.choice(_SEVERITIES)
        latency = max(1.0, self._rng.gauss(50.0, 15.0))
        return Event(
            ts=time.time(),
            source=self._rng.choice(_HOSTS),
            event_type=self._rng.choice(_EVENT_TYPES),
            severity=sev,
            message=self._rng.choice(
                ["GET /api/users", "SELECT * FROM orders", "cache hit", "job completed"]
            ),
            features={
                "latency_ms": latency,
                "payload_bytes": self._rng.randint(100, 5000),
                "status_code": float(self._rng.choice([200, 200, 200, 404, 500])),
            },
        )

    def _anomaly_event(self, kind: str) -> Event:
        """Build an event that is part of an injected anomaly."""
        ev = self._normal_event()
        ev.is_anomaly = True
        ev.anomaly_kind = kind
        if kind == "rate_spike":
            ev.message = "GET /api/search (burst)"
        elif kind == "error_burst":
            ev.severity = "error"
            ev.message = "upstream timeout"
            ev.features["status_code"] = 500.0
            ev.features["latency_ms"] = self._rng.gauss(2000.0, 500.0)
        elif kind == "unusual_source":
            ev.source = f"unknown-host-{self._rng.randint(1000, 9999)}"
            ev.message = "unexpected source connection"
        return ev

    async def _emit_anomaly_burst(self, kind: str) -> AsyncIterator[Event]:
        """Yield a short burst of anomaly events of the given kind.

        Rate spikes last ~5s at ~10× the normal rate; other kinds yield a
        handful of events quickly.
        """
        rate = self._settings.synthetic_events_per_sec
        if kind == "rate_spike":
            duration = 5.0
            burst_rate = max(rate * 10.0, 50.0)
            end = time.monotonic() + duration
            while time.monotonic() < end and not self._closed:
                yield self._anomaly_event(kind)
                await asyncio.sleep(1.0 / burst_rate)
        else:
            n = self._rng.randint(3, 8)
            for _ in range(n):
                if self._closed:
                    return
                yield self._anomaly_event(kind)
                await asyncio.sleep(self._rng.uniform(0.01, 0.05))

    # ---- public API -------------------------------------------------------

    async def events(self) -> AsyncIterator[Event]:
        """Yield synthetic events with Poisson-like inter-arrival times.

        At each step, with probability ``synthetic_anomaly_rate`` an anomaly
        burst is injected instead of a single normal event.
        """
        rate = max(self._settings.synthetic_events_per_sec, 0.01)
        emitted = 0
        log.info("synthetic_source_started", rate=rate, max_events=self._max_events)
        try:
            while not self._closed:
                if self._max_events is not None and emitted >= self._max_events:
                    break
                if self._rng.random() < self._settings.synthetic_anomaly_rate:
                    kind = self._rng.choice(
                        ["rate_spike", "error_burst", "unusual_source"]
                    )
                    log.info("synthetic_anomaly_injected", kind=kind)
                    async for ev in self._emit_anomaly_burst(kind):
                        yield ev
                        emitted += 1
                        if (
                            self._max_events is not None
                            and emitted >= self._max_events
                        ):
                            return
                else:
                    yield self._normal_event()
                    emitted += 1
                # Poisson-like pacing: exponential inter-arrival with mean 1/rate.
                delay = self._rng.expovariate(rate)
                await asyncio.sleep(delay)
        finally:
            log.info("synthetic_source_stopped", emitted=emitted)

    async def aclose(self) -> None:
        """Signal the generator to stop on its next iteration."""
        self._closed = True
