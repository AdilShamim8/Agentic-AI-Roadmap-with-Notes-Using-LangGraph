"""LangGraph response-agent state definition.

The :class:`ResponseState` ``TypedDict`` is the mutable bag that flows through
every node of the response state graph. All keys are optional
(``total=False``) so the initial state only needs to carry the ``window`` and
``anomaly`` — every other field is populated by a downstream node.
"""

from __future__ import annotations

from typing import Optional, TypedDict

from anomaly_monitor.models import (
    Action,
    ActionResult,
    AnomalyScore,
    Feedback,
    Window,
)


class ResponseState(TypedDict, total=False):
    """Mutable state flowing through the LangGraph response agent.

    Attributes:
        window: The aggregated window that triggered the response.
        anomaly: The detector's verdict on that window.
        severity: String form of the anomaly severity (``"info"`` …
            ``"critical"``). Copied from ``anomaly.severity`` by the
            ``classify_severity`` node for easy conditional routing.
        proposed_action: The action chosen by ``propose_action`` (possibly
            modified by ``hitl_review``).
        approved: ``True``/``False``/``None`` — set by the HITL node.
        result: The :class:`ActionResult` produced by ``execute_action``.
        feedback: Optional operator feedback attached after the fact.
        trace: Human-readable step-by-step trace for debugging / eval.
        errors: Non-fatal errors collected along the way.
    """

    window: Window
    anomaly: AnomalyScore
    severity: str  # "info" | "warning" | "high" | "critical"
    proposed_action: Optional[Action]
    approved: Optional[bool]
    result: Optional[ActionResult]
    feedback: Optional[Feedback]
    trace: list[str]  # human-readable step trace
    errors: list[str]
