"""JSONL file replay source for deterministic eval runs.

Reads a file where each line is a JSON document conforming to
:class:`Event` and replays the events in real time (paced by the gap
between consecutive ``ts`` fields). Useful for reproducible eval against
labelled data.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Optional, Union

import structlog

from anomaly_monitor.models import Event
from anomaly_monitor.streaming.base import StreamConsumer

log = structlog.get_logger()

# Maximum inter-event delay (seconds) when catching up on a backlog.
# Prevents an eval replay from stalling for hours when the file has a
# large gap (e.g. overnight pause between samples).
_MAX_CATCHUP_SEC = 0.1


class FileSource(StreamConsumer):
    """Replay a JSONL file of :class:`Event` objects with real-time pacing.

    Args:
        path: Path to a ``.jsonl`` file (one JSON Event per line).
        speed: Replay speed multiplier. ``1.0`` is real time; ``10.0``
            plays 10× faster. ``0`` (or negative) plays as fast as possible.
    """

    def __init__(
        self,
        path: Union[str, Path],
        speed: float = 1.0,
    ) -> None:
        """Configure the file replay source."""
        self._path = Path(path)
        self._speed = max(speed, 0.0)
        self._closed = False
        self._lines: Optional[list[str]] = None

    def _load(self) -> list[str]:
        """Read & cache the file's lines (one event per line)."""
        if self._lines is None:
            log.info("file_source_loading", path=str(self._path))
            with self._path.open("r", encoding="utf-8") as fh:
                self._lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            log.info("file_source_loaded", lines=len(self._lines))
        return self._lines

    async def events(self) -> AsyncIterator[Event]:
        """Yield events from the file, paced by their ``ts`` deltas."""
        lines = self._load()
        prev_ts: Optional[float] = None
        emitted = 0
        try:
            for lineno, raw in enumerate(lines, start=1):
                if self._closed:
                    break
                try:
                    ev = Event.model_validate_json(raw)
                except Exception as exc:  # noqa: BLE001 — skip bad lines
                    log.warning(
                        "file_source_bad_line",
                        lineno=lineno,
                        error=str(exc),
                    )
                    continue

                if prev_ts is not None and ev.ts > prev_ts and self._speed > 0:
                    delta = ev.ts - prev_ts
                    if self._speed != 1.0:
                        delta = delta / self._speed
                    delta = min(delta, _MAX_CATCHUP_SEC)
                    if delta > 0:
                        await asyncio.sleep(delta)

                prev_ts = ev.ts
                yield ev
                emitted += 1
        finally:
            log.info("file_source_done", emitted=emitted, total=len(lines))

    async def aclose(self) -> None:
        """Signal the generator to stop on its next iteration."""
        self._closed = True
