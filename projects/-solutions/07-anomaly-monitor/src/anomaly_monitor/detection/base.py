"""Abstract :class:`Detector` interface.

A detector consumes a :class:`~anomaly_monitor.models.Window` and produces
an :class:`~anomaly_monitor.models.AnomalyScore`. Detectors are async so
that LLM-backed detectors can call out to external services without
blocking the rest of the pipeline.
"""

from __future__ import annotations

import abc

from anomaly_monitor.models import AnomalyScore, Window


class Detector(abc.ABC):
    """A detector scores a single window for anomaly-ness."""

    name: str = "abstract"

    @abc.abstractmethod
    async def detect(self, window: Window) -> AnomalyScore:
        """Return an :class:`AnomalyScore` for this window."""
        ...

    async def aclose(self) -> None:
        """Release any resources held by this detector (default: no-op)."""
        return None
