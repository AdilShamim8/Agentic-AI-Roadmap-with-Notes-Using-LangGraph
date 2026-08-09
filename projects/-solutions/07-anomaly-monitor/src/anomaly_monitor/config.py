"""Centralised configuration via pydantic-settings.

All settings are loaded from environment variables (or a local `.env` file).
Every setting has a sensible default so the project runs out-of-the-box in
synthetic local mode with no external infrastructure.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Mode(str, Enum):
    LOCAL = "local"
    KAFKA = "kafka"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"

    def __ge__(self, other: "Severity") -> bool:
        order = [Severity.INFO, Severity.WARNING, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) >= order.index(other)

    def __gt__(self, other: "Severity") -> bool:
        order = [Severity.INFO, Severity.WARNING, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) > order.index(other)

    def __lt__(self, other: "Severity") -> bool:
        return not self >= other


class HitlBackend(str, Enum):
    CLI = "cli"
    SLACK = "slack"


class Settings(BaseSettings):
    """All runtime configuration. See `.env.example` for documentation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Runtime mode -------------------------------------------------------
    mode: Mode = Mode.LOCAL

    # ---- LLM ----------------------------------------------------------------
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_timeout_sec: float = 20.0

    # ---- Streaming (Kafka) --------------------------------------------------
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "anomaly.events"
    kafka_consumer_group: str = "anomaly-monitor"
    kafka_auto_offset_reset: str = "earliest"

    # ---- State (Redis) ------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    window_ttl_sec: int = 3600

    # ---- Windowing ----------------------------------------------------------
    window_1m_sec: int = 60
    window_5m_sec: int = 300

    # ---- Detection thresholds ----------------------------------------------
    zscore_threshold: float = 3.0
    isolation_contamination: float = 0.05
    llm_weight: float = 0.6
    stat_weight: float = 0.4
    ensemble_threshold: float = 0.5

    # ---- Response policy ----------------------------------------------------
    hitl_min_severity: Severity = Severity.HIGH

    # ---- Alerting (PagerDuty) ----------------------------------------------
    pagerduty_api_key: str = ""
    pagerduty_service_id: str = ""

    # ---- Scaling (Kubernetes) ----------------------------------------------
    k8s_api_url: str = ""
    k8s_namespace: str = "default"
    k8s_deployment: str = "anomaly-target"
    k8s_token: str = ""

    # ---- Blocking (firewall) -----------------------------------------------
    firewall_rules_file: str = "./.runtime/firewall_rules.jsonl"

    # ---- HITL (Slack) -------------------------------------------------------
    slack_webhook_url: str = ""
    hitl_backend: HitlBackend = HitlBackend.CLI

    # ---- Observability ------------------------------------------------------
    langsmith_api_key: str = ""
    langsmith_project: str = "anomaly-monitor"
    prometheus_port: int = 9001

    # ---- Feedback store (SQLite) -------------------------------------------
    feedback_db: str = "./.runtime/feedback.db"

    # ---- Logging ------------------------------------------------------------
    log_level: str = "INFO"

    # ---- Synthetic source (local mode) -------------------------------------
    synthetic_events_per_sec: float = 5.0
    synthetic_anomaly_rate: float = 0.02

    @field_validator("llm_weight", "stat_weight")
    @classmethod
    def _non_negative_weights(cls, v: float) -> float:
        if v < 0:
            raise ValueError("weights must be non-negative")
        return v

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def langsmith_enabled(self) -> bool:
        return bool(self.langsmith_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance. Use `get_settings.cache_clear()` to reload."""
    return Settings()


# Convenience module-level accessor
settings = get_settings()
