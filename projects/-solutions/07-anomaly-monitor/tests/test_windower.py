"""Tests for the in-memory windower (aggregation/windower.py).

These tests exercise the in-memory fallback path exclusively — no Redis is
required. They cover the core windower contract: event counting, time-based
roll-over, recent-window retrieval, TTL expiry, and cross-duration aggregation.
"""

from __future__ import annotations

import time

import pytest

from anomaly_monitor.aggregation.windower import Windower
from anomaly_monitor.config import Settings
from anomaly_monitor.models import Event


@pytest.mark.asyncio
async def test_add_event_increments_count() -> None:
    """Adding 5 events populates count, event_types, and error_count."""
    w = Windower()  # in-memory mode (no start() needed)
    base_ts = 1_000_000.0
    for i in range(5):
        sev = "error" if i >= 3 else "info"
        ev = Event(
            ts=base_ts,
            source=f"host-{i}",
            event_type="log",
            severity=sev,
            message="test event",
        )
        await w.add_event(ev)

    win = await w.get_window(60, base_ts)
    assert win.count == 5
    assert win.event_types.get("log") == 5
    # Events 3 and 4 have severity="error" → error_count should be 2.
    assert win.error_count == 2
    assert win.error_rate == 2 / 5


@pytest.mark.asyncio
async def test_window_rolls_over_time() -> None:
    """Events 120 s apart land in different 1-minute windows."""
    w = Windower()
    ev1 = Event(ts=1000.0, source="host-1", event_type="log", severity="info")
    ev2 = Event(ts=1120.0, source="host-2", event_type="log", severity="info")
    await w.add_event(ev1)
    await w.add_event(ev2)

    win1 = await w.get_window(60, 1000.0)
    win2 = await w.get_window(60, 1120.0)
    assert win1.window_id != win2.window_id
    assert win1.count == 1
    assert win2.count == 1


@pytest.mark.asyncio
async def test_get_recent_windows_returns_n() -> None:
    """get_recent_windows(n) returns exactly n windows (including empty ones)."""
    w = Windower()
    windows = await w.get_recent_windows(60, 5)
    assert len(windows) == 5
    # All should be valid Window objects (empty, since no events were added).
    for win in windows:
        assert win.duration_sec == 60


@pytest.mark.asyncio
async def test_expire_old_returns_count() -> None:
    """expire_old removes windows older than TTL and returns the count removed."""
    s = Settings(window_ttl_sec=1)
    w = Windower(settings=s)
    # Add an event far in the past so its window is well past the 1 s TTL.
    old_ts = time.time() - 600
    ev = Event(ts=old_ts, source="host-1", event_type="log", severity="info")
    await w.add_event(ev)

    n = await w.expire_old()
    assert n > 0


@pytest.mark.asyncio
async def test_5m_window_aggregates_across_1m_boundaries() -> None:
    """Events spread across 3 minutes all land in the same 5-minute window."""
    w = Windower()
    timestamps = [0.0, 60.0, 120.0]
    for i, t in enumerate(timestamps):
        ev = Event(
            ts=t,
            source=f"host-{i}",
            event_type="log",
            severity="info",
        )
        await w.add_event(ev)

    # The 5-minute window at any of these timestamps should contain all 3.
    win5m = await w.get_window(300, 60.0)
    assert win5m.count == 3

    # The three 1-minute windows should each contain exactly 1 event.
    for t in timestamps:
        win1m = await w.get_window(60, t)
        assert win1m.count == 1

    # Verify the 1-minute window IDs are all different.
    ids = {(await w.get_window(60, t)).window_id for t in timestamps}
    assert len(ids) == 3
