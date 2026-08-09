"""Windower — maintains tumbling time windows for anomaly detection.

Two simultaneous tumbling windows are kept per timestamp: a 1-minute and
a 5-minute window (durations configurable via ``settings.window_*_sec``).
Backed by Redis when available; falls back to in-memory transparently.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import structlog

from anomaly_monitor.config import Settings, settings as _default_settings
from anomaly_monitor.models import Event, Window

log = structlog.get_logger()

_WINDOW_PREFIX = "am:window"
_BASELINE_MAX = 100


def _window_id(duration_sec: int, ts: float) -> str:
    """Compute the tumbling window id for ``ts`` at the given duration."""
    return f"{duration_sec}s:{int(ts // duration_sec)}"


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Pick the q-th percentile from a pre-sorted, non-empty list."""
    n = len(sorted_vals)
    idx = min(n - 1, int(n * q))
    return sorted_vals[idx]


class Windower:
    """Maintain 1m and 5m tumbling windows of :class:`Event` objects.

    Backed by Redis (sorted set per window, members are event JSON) with
    an automatic in-memory fallback when Redis is unreachable. Also keeps
    a small rolling baseline cache of previously completed windows' count
    and error_rate per (duration, metric) for the statistical detector.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Create a windower. ``settings`` defaults to the global settings."""
        self._settings = settings or _default_settings
        self._redis: Optional[Any] = None  # redis.asyncio.Redis
        self._use_redis = False
        # In-memory state (used as fallback and as a local cache).
        self._windows: dict[str, Window] = {}
        self._sources: dict[str, set[str]] = {}
        self._latencies: dict[str, list[float]] = {}
        self._baselines: dict[str, list[float]] = {}
        # Track the last window id seen per duration, for baseline roll-over.
        self._last_window_id: dict[int, str] = {}

    @property
    def _durations(self) -> list[int]:
        return [self._settings.window_1m_sec, self._settings.window_5m_sec]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Try to connect to Redis; fall back to in-memory on any failure."""
        try:
            import redis.asyncio as aioredis  # type: ignore

            self._redis = aioredis.from_url(
                self._settings.redis_url, decode_responses=True
            )
            await self._redis.ping()
            self._use_redis = True
            log.info("windower_redis_connected", url=self._settings.redis_url)
        except Exception as exc:  # noqa: BLE001
            log.warning("windower_redis_unavailable_fallback_memory", error=str(exc))
            self._redis = None
            self._use_redis = False

    async def aclose(self) -> None:
        """Close the Redis connection if any (idempotent)."""
        if self._redis is not None:
            try:
                await self._redis.aclose()  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                log.warning("windower_redis_close_failed", error=str(exc))
            finally:
                self._redis = None
                self._use_redis = False

    # ------------------------------------------------------------------
    # Baseline maintenance
    # ------------------------------------------------------------------

    def _push_baseline(self, duration_sec: int, window: Window) -> None:
        """Record a closed window's count & error_rate into the baseline cache."""
        for metric, value in (
            ("count", float(window.count)),
            ("error_rate", float(window.error_rate)),
        ):
            key = f"{duration_sec}s:{metric}"
            buf = self._baselines.setdefault(key, [])
            buf.append(value)
            if len(buf) > _BASELINE_MAX:
                del buf[: len(buf) - _BASELINE_MAX]

    def _maybe_roll_baseline(self, duration_sec: int, window_id: str) -> None:
        """If ``window_id`` differs from the last seen, snapshot the old window."""
        prev = self._last_window_id.get(duration_sec)
        if prev is not None and prev != window_id and prev in self._windows:
            self._push_baseline(duration_sec, self._windows[prev])
        self._last_window_id[duration_sec] = window_id

    def get_baseline(self, duration_sec: int, metric: str) -> list[float]:
        """Return a copy of the cached baseline values for (duration, metric)."""
        return list(self._baselines.get(f"{duration_sec}s:{metric}", []))

    # ------------------------------------------------------------------
    # Core ops
    # ------------------------------------------------------------------

    async def add_event(self, event: Event) -> dict[str, Window]:
        """Add an event to both 1m and 5m windows. Return the windows it landed in."""
        out: dict[str, Window] = {}
        for dur in self._durations:
            wid = _window_id(dur, event.ts)
            self._maybe_roll_baseline(dur, wid)
            if self._use_redis:
                await self._redis_add_event(wid, event)
            else:
                self._mem_add_event(wid, dur, event)
            out[f"{dur}s"] = await self.get_window(dur, event.ts)
        return out

    def _mem_add_event(self, wid: str, dur: int, event: Event) -> None:
        """Append an event to an in-memory window (creating it if needed)."""
        if wid not in self._windows:
            start = int(event.ts // dur) * dur
            self._windows[wid] = Window(
                window_id=wid,
                duration_sec=dur,
                start_ts=float(start),
                end_ts=float(start + dur),
            )
            self._sources[wid] = set()
            self._latencies[wid] = []
        win = self._windows[wid]
        win.add_event(event)
        self._sources[wid].add(event.source)
        lat = event.features.get("latency_ms")
        if lat is not None:
            self._latencies[wid].append(float(lat))

    async def _redis_add_event(self, wid: str, event: Event) -> None:
        """Add an event to a Redis sorted set for the window (with TTL)."""
        assert self._redis is not None
        key = f"{_WINDOW_PREFIX}:{wid}"
        member = event.model_dump_json()
        pipe = self._redis.pipeline()
        pipe.zadd(key, {member: event.ts})
        pipe.expire(key, self._settings.window_ttl_sec)
        await pipe.execute()

    def _finalise_window(self, win: Window, wid: str) -> Window:
        """Populate ``unique_sources`` and latency percentiles on a Window."""
        win.unique_sources = len(self._sources.get(wid, set()))
        lats = self._latencies.get(wid, [])
        if lats:
            sl = sorted(lats)
            win.latency_p50 = _percentile(sl, 0.50)
            win.latency_p95 = _percentile(sl, 0.95)
            win.latency_p99 = _percentile(sl, 0.99)
        return win

    async def get_window(self, duration_sec: int, ts: Optional[float] = None) -> Window:
        """Return the (possibly empty) window for ``duration_sec`` at ``ts``."""
        ts = ts if ts is not None else time.time()
        wid = _window_id(duration_sec, ts)
        if self._use_redis:
            return await self._redis_get_window(wid, duration_sec, ts)
        win = self._windows.get(wid)
        if win is None:
            start = int(ts // duration_sec) * duration_sec
            return Window(
                window_id=wid,
                duration_sec=duration_sec,
                start_ts=float(start),
                end_ts=float(start + duration_sec),
            )
        return self._finalise_window(win, wid)

    async def _redis_get_window(self, wid: str, dur: int, ts: float) -> Window:
        """Aggregate a Redis sorted set into a :class:`Window`."""
        assert self._redis is not None
        start = int(ts // dur) * dur
        win = Window(
            window_id=wid,
            duration_sec=dur,
            start_ts=float(start),
            end_ts=float(start + dur),
        )
        members = await self._redis.zrange(f"{_WINDOW_PREFIX}:{wid}", 0, -1)
        sources: set[str] = set()
        lats: list[float] = []
        for raw in members:
            try:
                ev = Event.model_validate_json(raw)
            except Exception:  # noqa: BLE001
                continue
            win.add_event(ev)
            sources.add(ev.source)
            lat = ev.features.get("latency_ms")
            if lat is not None:
                lats.append(float(lat))
        win.unique_sources = len(sources)
        if lats:
            sl = sorted(lats)
            win.latency_p50 = _percentile(sl, 0.50)
            win.latency_p95 = _percentile(sl, 0.95)
            win.latency_p99 = _percentile(sl, 0.99)
        return win

    async def get_window_by_id(self, window_id: str) -> Optional[Window]:
        """Look up a window by its id (e.g. ``"60s:1700000000"``).

        Returns ``None`` if the window has expired or was never created.
        Works for both in-memory and Redis modes (in Redis mode it parses
        the window_id to recover ``duration_sec`` and ``ts``).
        """
        if self._use_redis:
            try:
                parts = window_id.split(":")
                dur = int(parts[0].rstrip("s"))
                bucket = int(parts[1])
                return await self.get_window(dur, float(bucket * dur) + 0.001)
            except (IndexError, ValueError):
                return None
        win = self._windows.get(window_id)
        if win is None:
            return None
        return self._finalise_window(win, window_id)

    async def get_recent_windows(
        self, duration_sec: int, n: int = 10
    ) -> list[Window]:
        """Return the last ``n`` windows of this duration (for baseline computation)."""
        bucket = int(time.time() // duration_sec)
        out: list[Window] = []
        for i in range(n - 1, -1, -1):
            out.append(await self.get_window(duration_sec, (bucket - i) * duration_sec + 0.001))
        return out

    async def expire_old(self) -> int:
        """Expire in-memory windows older than TTL. Return count expired.

        Redis windows expire automatically via ``EXPIRE``; this only cleans
        the in-memory fallback dictionaries.
        """
        cutoff = time.time() - self._settings.window_ttl_sec
        stale = [wid for wid, win in self._windows.items() if win.end_ts < cutoff]
        for wid in stale:
            self._windows.pop(wid, None)
            self._sources.pop(wid, None)
            self._latencies.pop(wid, None)
        if stale:
            log.info("windower_expired", count=len(stale))
        return len(stale)
