"""Tests for the SQLite feedback store (feedback/store.py).

Each test uses a tmp_path for the SQLite DB to avoid polluting the default
``./.runtime/feedback.db``.
"""

from __future__ import annotations

import time

import pytest

from anomaly_monitor.config import Settings
from anomaly_monitor.feedback.store import FeedbackStore
from anomaly_monitor.models import Feedback


def _settings_for(tmp_path) -> Settings:
    """Build Settings pointing the feedback DB at *tmp_path*."""
    return Settings(feedback_db=str(tmp_path / "test_feedback.db"))


@pytest.mark.asyncio
async def test_record_and_get(tmp_path) -> None:
    """Record a Feedback, fetch it back, assert fields match."""
    s = _settings_for(tmp_path)
    store = FeedbackStore(settings=s)
    await store.start()
    try:
        fb = Feedback(
            anomaly_id="anom-test-001",
            is_real_anomaly=True,
            action_correct=False,
            operator_note="false alarm — known deploy",
            created_at=1700000000.0,
        )
        fb_id = await store.record(fb)
        assert fb_id > 0

        got = await store.get("anom-test-001")
        assert got is not None
        assert got.anomaly_id == "anom-test-001"
        assert got.is_real_anomaly is True
        assert got.action_correct is False
        assert got.operator_note == "false alarm — known deploy"
    finally:
        await store.aclose()


@pytest.mark.asyncio
async def test_recent_returns_in_order(tmp_path) -> None:
    """recent() returns rows newest-first (by id descending)."""
    s = _settings_for(tmp_path)
    store = FeedbackStore(settings=s)
    await store.start()
    try:
        ids = []
        for i in range(3):
            fb = Feedback(
                anomaly_id=f"anom-{i:03d}",
                is_real_anomaly=True,
                created_at=time.time() + i,
            )
            rid = await store.record(fb)
            ids.append(rid)

        recent = await store.recent(limit=10)
        assert len(recent) == 3
        # Newest-first means the last-recorded anomaly should be first.
        assert recent[0].anomaly_id == "anom-002"
        assert recent[1].anomaly_id == "anom-001"
        assert recent[2].anomaly_id == "anom-000"
    finally:
        await store.aclose()


@pytest.mark.asyncio
async def test_stats_aggregates_correctly(tmp_path) -> None:
    """Record 5 with a mix of real/not-real and check stats."""
    s = _settings_for(tmp_path)
    store = FeedbackStore(settings=s)
    await store.start()
    try:
        # 3 real anomalies (2 with action_correct=True, 1 with False)
        # 2 false alarms (1 with action_correct=False, 1 with None)
        rows = [
            Feedback(anomaly_id="a1", is_real_anomaly=True, action_correct=True),
            Feedback(anomaly_id="a2", is_real_anomaly=True, action_correct=True),
            Feedback(anomaly_id="a3", is_real_anomaly=True, action_correct=False),
            Feedback(anomaly_id="a4", is_real_anomaly=False, action_correct=False),
            Feedback(anomaly_id="a5", is_real_anomaly=False, action_correct=None),
        ]
        for fb in rows:
            await store.record(fb)

        stats = await store.stats()
        assert stats["total"] == 5.0
        assert stats["real_pct"] == 3 / 5
        # action_correct_pct = correct / total = 2 / 5
        assert abs(stats["action_correct_pct"] - 2 / 5) < 1e-6
        assert stats["by_kind"]["real_anomaly"] == 3.0
        assert stats["by_kind"]["false_alarm"] == 2.0
        assert stats["by_kind"]["action_correct_true"] == 2.0
        assert stats["by_kind"]["action_correct_false"] == 2.0
        assert stats["by_kind"]["action_correct_none"] == 1.0
    finally:
        await store.aclose()
