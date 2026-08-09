"""Concrete response actions with async ``execute()``.

Each action subclasses the pydantic :class:`~anomaly_monitor.models.Action`
model (carrying ``kind`` / ``severity`` / ``target`` / ``payload`` /
``dry_run``) and adds an :meth:`execute` coroutine. Heavy deps (``httpx``,
``tenacity``) are lazy-imported inside the methods that need them.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import structlog
from pydantic import PrivateAttr

from anomaly_monitor.config import Settings, settings as _default_settings
from anomaly_monitor.models import (
    Action, ActionKind, ActionResult, AnomalyScore, Window,
)

log = structlog.get_logger()


class BaseAction(Action):
    """Base executor: extends pydantic ``Action`` with ``execute()``.

    Settings held in a private attr so they never appear in serialised output
    but are available to ``execute()`` for credential / endpoint lookups.
    """

    _settings: Any = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        if self._settings is None:
            self._settings = _default_settings

    @property
    def settings(self) -> Settings:
        return self._settings if self._settings is not None else _default_settings  # type: ignore[return-value]

    def _snapshot(self) -> Action:
        """Return a plain ``Action`` copy of this executor's public fields."""
        return Action(
            kind=self.kind, severity=self.severity, target=self.target,
            payload=dict(self.payload), dry_run=self.dry_run,
        )

    async def execute(self) -> ActionResult:  # pragma: no cover - abstract
        raise NotImplementedError


class NoopAction(BaseAction):
    """No-op action — always succeeds with output ``"noop"``."""

    kind: ActionKind = "noop"

    async def execute(self) -> ActionResult:
        start = time.time()
        log.info("action_noop", target=self.target, severity=self.severity.value)
        return ActionResult(
            action=self._snapshot(), success=True, output="noop",
            latency_sec=time.time() - start,
        )


class AlertAction(BaseAction):
    """Fire a PagerDuty Events API v2 alert (or dry-run).

    If ``pagerduty_api_key`` is empty or ``dry_run`` is true, logs and returns
    success with output ``(dry-run) alert would fire``.
    """

    kind: ActionKind = "alert"

    async def execute(self) -> ActionResult:
        start = time.time()
        routing_key = self.settings.pagerduty_api_key
        if self.dry_run or not routing_key:
            log.warning("alert_dry_run", target=self.target,
                        severity=self.severity.value,
                        summary=self.payload.get("summary", ""),
                        reason="dry_run" if self.dry_run else "no_routing_key")
            return ActionResult(action=self._snapshot(), success=True,
                                output="(dry-run) alert would fire",
                                latency_sec=time.time() - start)
        return await self._fire(routing_key, start)

    async def _fire(self, routing_key: str, start: float) -> ActionResult:
        """POST to PagerDuty with tenacity retries (3 attempts)."""
        import httpx  # lazy
        from tenacity import (AsyncRetrying, stop_after_attempt,  # lazy
                              wait_exponential)

        dedup_key = f"am-{self.target}-{int(time.time())}"
        body = {
            "routing_key": routing_key, "event_action": "trigger",
            "dedup_key": dedup_key,
            "payload": {
                "summary": str(self.payload.get("summary", "anomaly detected")),
                "severity": self.severity.value, "source": self.target,
                "custom_details": self.payload,
            },
        }

        async def _post() -> dict:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=body, timeout=10.0)
                r.raise_for_status()
                return r.json() if r.content else {}

        try:
            resp: dict = {}
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                reraise=True,
            ):
                with attempt:
                    resp = await _post()
            log.info("alert_fired", target=self.target, dedup_key=dedup_key)
            return ActionResult(action=self._snapshot(), success=True,
                                output=f"pagerduty accepted: {resp.get('status', 'ok')}",
                                latency_sec=time.time() - start)
        except Exception as exc:  # noqa: BLE001
            log.error("alert_failed", error=str(exc))
            return ActionResult(action=self._snapshot(), success=False,
                                output=f"alert failed: {exc}",
                                latency_sec=time.time() - start)


class ScaleAction(BaseAction):
    """Patch a K8s Deployment replica count via the scale subresource.

    If ``k8s_api_url`` is empty or ``dry_run`` is true, logs the intent.
    """

    kind: ActionKind = "scale"

    async def execute(self) -> ActionResult:
        start = time.time()
        api_url = self.settings.k8s_api_url
        ns = str(self.payload.get("namespace", self.settings.k8s_namespace))
        replicas = int(self.payload.get("replicas", 1))
        if self.dry_run or not api_url:
            log.warning("scale_dry_run", target=self.target, namespace=ns,
                        replicas=replicas,
                        reason="dry_run" if self.dry_run else "no_k8s_api_url")
            return ActionResult(action=self._snapshot(), success=True,
                                output=f"(dry-run) scale to {replicas} replicas",
                                latency_sec=time.time() - start)
        return await self._patch(api_url, ns, replicas, start)

    async def _patch(self, api_url: str, ns: str, replicas: int,
                     start: float) -> ActionResult:
        import httpx  # lazy
        url = (f"{api_url.rstrip('/')}/apis/apps/v1/namespaces/{ns}"
               f"/deployments/{self.target}/scale")
        headers = {"Content-Type": "application/merge-patch+json"}
        if self.settings.k8s_token:
            headers["Authorization"] = f"Bearer {self.settings.k8s_token}"
        body = {"spec": {"replicas": replicas}}
        try:
            async with httpx.AsyncClient() as client:
                r = await client.patch(url, json=body, headers=headers, timeout=10.0)
                r.raise_for_status()
            log.info("scale_done", target=self.target, replicas=replicas)
            return ActionResult(action=self._snapshot(), success=True,
                                output=f"scaled {self.target} to {replicas} replicas",
                                latency_sec=time.time() - start)
        except Exception as exc:  # noqa: BLE001
            log.error("scale_failed", error=str(exc))
            return ActionResult(action=self._snapshot(), success=False,
                                output=f"scale failed: {exc}",
                                latency_sec=time.time() - start)


class BlockAction(BaseAction):
    """Append a JSONL block rule to ``settings.firewall_rules_file``.

    Rule shape: ``{"ts":float,"source":target,"action":"block","reason":str,
    "ttl_sec":3600}``. Parent dir is created if missing. Dry-run logs only.
    """

    kind: ActionKind = "block"

    async def execute(self) -> ActionResult:
        start = time.time()
        if self.dry_run:
            log.warning("block_dry_run", target=self.target,
                        reason=self.payload.get("reason", ""))
            return ActionResult(action=self._snapshot(), success=True,
                                output=f"(dry-run) block {self.target}",
                                latency_sec=time.time() - start)
        return await self._write_rule(start)

    async def _write_rule(self, start: float) -> ActionResult:
        rules_file = Path(self.settings.firewall_rules_file)
        rule = {
            "ts": time.time(), "source": self.target, "action": "block",
            "reason": str(self.payload.get("reason", "anomaly detected")),
            "ttl_sec": int(self.payload.get("ttl_sec", 3600)),
        }
        try:
            rules_file.parent.mkdir(parents=True, exist_ok=True)
            with rules_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rule) + "\n")
            log.info("block_rule_written", target=self.target, file=str(rules_file))
            return ActionResult(action=self._snapshot(), success=True,
                                output=f"blocked {self.target}",
                                latency_sec=time.time() - start)
        except Exception as exc:  # noqa: BLE001
            log.error("block_failed", error=str(exc))
            return ActionResult(action=self._snapshot(), success=False,
                                output=f"block failed: {exc}",
                                latency_sec=time.time() - start)


# ---------------------------------------------------------------------------
# Anomaly-kind inference + factory
# ---------------------------------------------------------------------------
def _infer_anomaly_kind(anomaly: AnomalyScore, window: Window) -> str:
    """Heuristic: infer ``error_burst`` / ``unusual_source`` / ``rate_spike``.

    Inspects the reason text, window metrics, and z-score features since
    detectors don't always emit a structured ``anomaly_kind``.
    """
    reason = (anomaly.reason or "").lower()
    features = anomaly.contributing_features
    if "error" in reason or "burst" in reason or window.error_rate > 0.3:
        return "error_burst"
    if "source" in reason or "unusual" in reason or window.unique_sources >= 10:
        return "unusual_source"
    if features.get("z_error_rate", 0) >= 3.0:
        return "error_burst"
    return "rate_spike"


def build_action(kind: ActionKind, anomaly: AnomalyScore, window: Window,
                 settings: Settings) -> BaseAction:
    """Factory: create the right :class:`BaseAction` subclass for *kind*.

    Sets sensible ``target`` / ``payload`` from the anomaly + window. All
    actions default to ``dry_run=True`` (safe); production callers flip
    ``action.dry_run = False`` after construction.
    """
    common = {"severity": anomaly.severity, "dry_run": True}
    reason = (anomaly.reason or "anomaly detected")[:200]
    wid = window.window_id

    if kind == "alert":
        action: BaseAction = AlertAction(
            kind="alert",
            target=settings.pagerduty_service_id or "pagerduty",
            payload={"summary": f"[{anomaly.severity.value}] anomaly: {reason}",
                     "severity": anomaly.severity.value, "window_id": wid,
                     "probability": anomaly.probability, "detector": anomaly.detector},
            **common)
    elif kind == "scale":
        replicas = min(20, max(3, window.count // 50 + 1))
        action = ScaleAction(
            kind="scale", target=settings.k8s_deployment,
            payload={"namespace": settings.k8s_namespace, "replicas": replicas,
                     "window_id": wid, "reason": reason},
            **common)
    elif kind == "block":
        target = str(anomaly.contributing_features.get("source", f"window:{wid}"))
        action = BlockAction(
            kind="block", target=target,
            payload={"reason": reason, "ttl_sec": 3600, "window_id": wid},
            **common)
    else:
        action = NoopAction(
            kind="noop", target=wid,
            payload={"reason": reason, "window_id": wid}, **common)

    action._settings = settings
    return action
