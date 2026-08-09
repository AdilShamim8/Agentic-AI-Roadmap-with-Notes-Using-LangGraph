"""Pydantic domain models shared across the pipeline.

Every model is serialisable to JSON (via `.model_dump_json()`) so it can flow
through Kafka, be persisted to Redis, and be replayed from JSONL files for eval.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .config import Severity


# =============================================================================
# Event — the atomic unit produced by the stream
# =============================================================================
class Event(BaseModel):
    """A single observation from the monitored system (log line, metric, txn)."""

    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    ts: float = Field(default_factory=time.time)
    source: str = "host-1"
    event_type: str = "log"
    severity: str = "info"
    message: str = ""
    # Arbitrary numeric features for the statistical detector
    features: dict[str, float] = Field(default_factory=dict)
    # Whether this event was an injected anomaly (only set in synthetic mode
    # and in labeled eval data; never set in production)
    is_anomaly: bool = False
    anomaly_kind: Optional[str] = None


# =============================================================================
# Window — aggregated view over a time bucket
# =============================================================================
class Window(BaseModel):
    """Aggregated stats over a tumbling time window."""

    window_id: str  # e.g. "1m:1700000000"
    duration_sec: int
    start_ts: float
    end_ts: float

    count: int = 0
    error_count: int = 0
    unique_sources: int = 0
    event_types: dict[str, int] = Field(default_factory=dict)
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0

    # All raw event ids in this window (capped to avoid unbounded growth)
    event_ids: list[str] = Field(default_factory=list)

    @property
    def error_rate(self) -> float:
        return self.error_count / self.count if self.count > 0 else 0.0

    def add_event(self, event: Event) -> None:
        self.count += 1
        self.event_types[event.event_type] = self.event_types.get(event.event_type, 0) + 1
        if event.severity in ("error", "critical"):
            self.error_count += 1
        if len(self.event_ids) < 1000:
            self.event_ids.append(event.id)


# =============================================================================
# AnomalyScore — output of a detector
# =============================================================================
class AnomalyScore(BaseModel):
    """The verdict from a detector on a single window."""

    detector: str  # "statistical" | "llm" | "ensemble"
    is_anomaly: bool
    probability: float = Field(ge=0.0, le=1.0)
    severity: Severity = Severity.INFO
    reason: str = ""
    contributing_features: dict[str, float] = Field(default_factory=dict)

    # Link back to the window this scored
    window_id: str = ""
    ts: float = Field(default_factory=time.time)


# =============================================================================
# Action — what the response agent decided to do
# =============================================================================
ActionKind = Literal["noop", "alert", "scale", "block"]


class Action(BaseModel):
    """A response action proposed by the response agent."""

    kind: ActionKind
    severity: Severity = Severity.INFO
    target: str = ""  # e.g. deployment name, source IP, service id
    payload: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True  # safe default; flipped to False only in production mode

    def describe(self) -> str:
        bits = [self.kind.upper()]
        if self.target:
            bits.append(f"target={self.target}")
        if self.payload:
            bits.append(f"payload={self.payload}")
        if self.dry_run:
            bits.append("(dry-run)")
        return " ".join(bits)


class ActionResult(BaseModel):
    action: Action
    success: bool
    output: str = ""
    latency_sec: float = 0.0
    ts: float = Field(default_factory=time.time)


# =============================================================================
# Feedback — operator input on whether a response was correct
# =============================================================================
class Feedback(BaseModel):
    """Operator feedback on a detected anomaly + the response taken."""

    anomaly_id: str
    is_real_anomaly: bool
    action_correct: Optional[bool] = None
    operator_note: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


# =============================================================================
# Pipeline record — one full trip through the system, for eval / replay
# =============================================================================
class PipelineRecord(BaseModel):
    """End-to-end record of one anomaly → response cycle, for eval & replay."""

    record_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:12]}")
    window: Window
    anomaly: AnomalyScore
    proposed_action: Optional[Action] = None
    approved: Optional[bool] = None
    result: Optional[ActionResult] = None
    feedback: Optional[Feedback] = None
    detect_ts: float = 0.0
    response_ts: float = 0.0

    @property
    def e2e_latency_sec(self) -> float:
        return self.response_ts - self.detect_ts
