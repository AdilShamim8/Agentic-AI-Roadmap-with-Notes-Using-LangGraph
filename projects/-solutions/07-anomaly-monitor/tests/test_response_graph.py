"""Tests for the LangGraph response agent (response/graph.py).

Uses fake HITLManager subclasses to test routing without real human interaction.
All tests run without external services (no Slack, no PagerDuty, no K8s).
"""

from __future__ import annotations

from typing import Optional

import pytest

from anomaly_monitor.config import Severity, Settings
from anomaly_monitor.models import Action, AnomalyScore, Window
from anomaly_monitor.response.graph import ResponseGraph
from anomaly_monitor.response.hitl import HITLManager


class _AutoApproveHITL(HITLManager):
    """HITL manager that always approves without modification."""

    async def request_approval(self, action: Action) -> tuple[bool, Optional[Action]]:
        return True, None


class _DenyHITL(HITLManager):
    """HITL manager that always denies."""

    async def request_approval(self, action: Action) -> tuple[bool, Optional[Action]]:
        return False, None


def _make_window() -> Window:
    """Build a minimal Window for response-graph tests."""
    ts = 1_000_000.0
    return Window(
        window_id="60s:16666",
        duration_sec=60,
        start_ts=ts,
        end_ts=ts + 60,
        count=100,
        error_count=50,
        unique_sources=3,
        latency_p95=200.0,
    )


def _make_anomaly(severity: Severity) -> AnomalyScore:
    """Build an AnomalyScore with the given severity."""
    prob = {"info": 0.1, "warning": 0.6, "high": 0.8, "critical": 0.95}[severity.value]
    return AnomalyScore(
        detector="ensemble",
        is_anomaly=True,
        probability=prob,
        severity=severity,
        reason="test anomaly",
        contributing_features={"count": 100.0, "error_rate": 0.5},
        window_id="60s:16666",
    )


@pytest.mark.asyncio
async def test_warning_routes_directly_to_execute() -> None:
    """Warning severity skips HITL; action is noop."""
    s = Settings(openai_api_key="", hitl_min_severity=Severity.HIGH)
    graph = ResponseGraph(settings=s, hitl=_AutoApproveHITL(s))
    state = await graph.run(_make_window(), _make_anomaly(Severity.WARNING))

    assert state["proposed_action"].kind == "noop"
    # HITL was skipped, so approved should be None.
    assert state["approved"] is None
    assert state["result"].success is True


@pytest.mark.asyncio
async def test_critical_routes_through_hitl() -> None:
    """Critical severity routes through HITL; with auto-approve, action is alert."""
    s = Settings(openai_api_key="", hitl_min_severity=Severity.HIGH)
    graph = ResponseGraph(settings=s, hitl=_AutoApproveHITL(s))
    state = await graph.run(_make_window(), _make_anomaly(Severity.CRITICAL))

    assert state["proposed_action"].kind == "alert"
    assert state["approved"] is True
    assert state["result"].success is True


@pytest.mark.asyncio
async def test_hitl_denied_replaces_with_noop() -> None:
    """When HITL denies a critical action, the final action is noop."""
    s = Settings(openai_api_key="", hitl_min_severity=Severity.HIGH)
    graph = ResponseGraph(settings=s, hitl=_DenyHITL(s))
    state = await graph.run(_make_window(), _make_anomaly(Severity.CRITICAL))

    assert state["proposed_action"].kind == "noop"
    assert state["approved"] is False
    assert state["result"].success is True


@pytest.mark.asyncio
async def test_info_routes_to_noop() -> None:
    """Info severity produces a noop action (no real response)."""
    s = Settings(openai_api_key="", hitl_min_severity=Severity.HIGH)
    graph = ResponseGraph(settings=s, hitl=_AutoApproveHITL(s))
    state = await graph.run(_make_window(), _make_anomaly(Severity.INFO))

    assert state["proposed_action"].kind == "noop"
    assert state["approved"] is None
