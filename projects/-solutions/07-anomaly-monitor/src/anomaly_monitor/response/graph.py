"""LangGraph async state machine for the response agent.

Graph topology::

    classify_severity → propose_action → [hitl_review] → execute_action → END
                                           (only if severity >= hitl_min)

Every node is an ``async def``; the compiled graph is driven via
``await graph.ainvoke(initial_state)``. ``langgraph`` is lazy-imported inside
:meth:`ResponseGraph.build`.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import structlog

from anomaly_monitor.config import Settings, Severity, settings as _default_settings
from anomaly_monitor.models import AnomalyScore, ActionResult, Window
from anomaly_monitor.response.actions import (
    AlertAction,
    BaseAction,
    BlockAction,
    NoopAction,
    ScaleAction,
    _infer_anomaly_kind,
    build_action,
)
from anomaly_monitor.response.hitl import HITLManager
from anomaly_monitor.response.state import ResponseState

log = structlog.get_logger()

_VALID_KINDS = ("noop", "alert", "scale", "block")

_LLM_SYSTEM_PROMPT = (
    "You are an SRE response agent. Given an anomaly on a time window, pick "
    "exactly ONE action kind from: noop, alert, scale, block. Respond ONLY "
    'with strict JSON: {"kind": "noop"|"alert"|"scale"|"block", '
    '"reason": string}. No prose, no markdown fences.'
)

_CLS_MAP: dict[str, type[BaseAction]] = {
    "noop": NoopAction,
    "alert": AlertAction,
    "scale": ScaleAction,
    "block": BlockAction,
}


class ResponseGraph:
    """Async LangGraph state machine: classify → propose → (HITL) → execute."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        hitl: Optional[HITLManager] = None,
        action_factory: Any = build_action,
    ) -> None:
        """Initialise.

        Args:
            settings: Project settings (defaults to global singleton).
            hitl: Injected :class:`HITLManager` (created if omitted).
            action_factory: ``(kind, anomaly, window, settings) -> BaseAction``.
        """
        self._settings = settings or _default_settings
        self._hitl = hitl or HITLManager(self._settings)
        self._action_factory = action_factory
        self._compiled: Any = None
        self._llm: Any = None

    # ------------------------------------------------------------------
    # Graph construction + entry point
    # ------------------------------------------------------------------
    def build(self) -> Any:
        """Build (and cache) the compiled LangGraph."""
        from langgraph.graph import END, StateGraph  # lazy

        g = StateGraph(ResponseState)
        g.add_node("classify_severity", self._classify_severity)
        g.add_node("propose_action", self._propose_action)
        g.add_node("hitl_review", self._hitl_review)
        g.add_node("execute_action", self._execute_action)
        g.set_entry_point("classify_severity")
        g.add_edge("classify_severity", "propose_action")
        g.add_conditional_edges(
            "propose_action",
            self._route_after_propose,
            {"hitl": "hitl_review", "execute": "execute_action"},
        )
        g.add_edge("hitl_review", "execute_action")
        g.add_edge("execute_action", END)
        self._compiled = g.compile()
        return self._compiled

    async def run(self, window: Window, anomaly: AnomalyScore) -> ResponseState:
        """Run the full graph for one ``(window, anomaly)`` pair."""
        if self._compiled is None:
            self.build()
        initial: ResponseState = {
            "window": window,
            "anomaly": anomaly,
            "severity": anomaly.severity.value,
            "proposed_action": None,
            "approved": None,
            "result": None,
            "feedback": None,
            "trace": [],
            "errors": [],
        }
        return await self._compiled.ainvoke(initial)  # type: ignore[no-any-return,union-attr]

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------
    async def _classify_severity(self, state: ResponseState) -> dict:
        """Copy ``anomaly.severity`` into state and record the trace."""
        anomaly = state["anomaly"]
        sev = anomaly.severity.value
        trace = list(state.get("trace", [])) + [f"classify: {sev}"]
        log.info("response_classified", severity=sev, window_id=anomaly.window_id)
        return {"severity": sev, "trace": trace}

    async def _propose_action(self, state: ResponseState) -> dict:
        """Pick an action kind (rule-based, optionally refined by LLM)."""
        anomaly = state["anomaly"]
        window = state["window"]
        kind = self._pick_kind_rule(anomaly, window)
        if self._settings.llm_enabled:
            kind = await self._pick_kind_llm(anomaly, window, fallback=kind)
        action = self._action_factory(kind, anomaly, window, self._settings)
        trace = list(state.get("trace", [])) + [
            f"propose: {action.kind} (severity={action.severity.value}, "
            f"target={action.target})"
        ]
        log.info("action_proposed", kind=action.kind, target=action.target)
        return {"proposed_action": action, "trace": trace}

    def _pick_kind_rule(self, anomaly: AnomalyScore, window: Window) -> str:
        """Rule-based action-kind selection from severity + anomaly kind."""
        sev = anomaly.severity
        if sev == Severity.CRITICAL:
            return "alert"
        if sev == Severity.HIGH:
            inferred = _infer_anomaly_kind(anomaly, window)
            if inferred == "rate_spike":
                return "scale"
            if inferred == "unusual_source":
                return "block"
            return "alert"  # error_burst or unknown high-severity
        return "noop"

    async def _pick_kind_llm(
        self, anomaly: AnomalyScore, window: Window, fallback: str,
    ) -> str:
        """Ask the LLM to pick an action kind; fall back on any error."""
        try:
            from langchain_core.messages import HumanMessage, SystemMessage  # lazy
            from langchain_openai import ChatOpenAI  # lazy
        except ImportError:
            return fallback

        if self._llm is None:
            try:
                self._llm = ChatOpenAI(
                    model=self._settings.llm_model,
                    temperature=self._settings.llm_temperature,
                    timeout=self._settings.llm_timeout_sec,
                    openai_api_key=self._settings.openai_api_key,
                    openai_api_base=self._settings.openai_base_url,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("llm_action_init_failed_using_rules", error=str(exc))
                return fallback

        human = HumanMessage(content=(
            f"severity={anomaly.severity.value} probability={anomaly.probability:.3f} "
            f"reason={anomaly.reason} window_count={window.count} "
            f"error_rate={window.error_rate:.4f} unique_sources={window.unique_sources} "
            f"latency_p95={window.latency_p95:.2f}"
        ))
        try:
            resp = await self._llm.ainvoke(
                [SystemMessage(content=_LLM_SYSTEM_PROMPT), human]
            )
            text = getattr(resp, "content", resp)
            if isinstance(text, list):
                text = "".join(
                    p.get("text", "") if isinstance(p, dict) else str(p) for p in text
                )
            raw = str(text).strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.lower().startswith("json"):
                    raw = raw[4:].lstrip()
            data = json.loads(raw)
            k = str(data.get("kind", fallback)).lower().strip()
            if k in _VALID_KINDS:
                log.info("llm_picked_action", kind=k, reason=data.get("reason", ""))
                return k
            log.warning("llm_action_invalid_kind_using_fallback", kind=k)
            return fallback
        except Exception as exc:  # noqa: BLE001
            log.warning("llm_action_pick_failed_using_rules", error=str(exc))
            return fallback

    def _route_after_propose(self, state: ResponseState) -> str:
        """Route to HITL when the action severity meets the threshold."""
        action = state.get("proposed_action")
        if action is None:
            return "execute"
        sev = action.severity
        if isinstance(sev, str):
            try:
                sev = Severity(sev)
            except ValueError:
                sev = Severity.INFO
        try:
            return "hitl" if sev >= self._settings.hitl_min_severity else "execute"
        except Exception:  # pragma: no cover
            return "execute"

    async def _hitl_review(self, state: ResponseState) -> dict:
        """Ask the HITL manager to approve / modify / deny the action."""
        action = state.get("proposed_action")
        trace = list(state.get("trace", []))
        if action is None:
            trace.append("hitl: no action → skip")
            return {"trace": trace}

        approved, modified = await self._hitl.request_approval(action)
        if not approved:
            noop = NoopAction(
                kind="noop", severity=action.severity, target=action.target,
                payload={"reason": "hitl denied", "original_kind": str(action.kind)},
                dry_run=True,
            )
            noop._settings = self._settings
            trace.append(f"hitl: denied → noop (was {action.kind})")
            return {"approved": False, "proposed_action": noop, "trace": trace}

        if modified is not None:
            exec_action = self._wrap_modified(modified)
            trace.append(
                f"hitl: approved with modification → {modified.kind} "
                f"(target={modified.target})"
            )
            return {"approved": True, "proposed_action": exec_action, "trace": trace}

        trace.append(f"hitl: approved ({action.kind})")
        return {"approved": True, "trace": trace}

    def _wrap_modified(self, action: Any) -> BaseAction:
        """Wrap a modified pydantic ``Action`` into the right executor subclass."""
        kind = str(getattr(action, "kind", "noop"))
        cls = _CLS_MAP.get(kind, NoopAction)
        new = cls(
            kind=kind,  # type: ignore[arg-type]
            severity=action.severity, target=action.target,
            payload=dict(action.payload), dry_run=action.dry_run,
        )
        new._settings = self._settings
        return new

    async def _execute_action(self, state: ResponseState) -> dict:
        """Run the proposed action and store the :class:`ActionResult`."""
        action = state.get("proposed_action")
        trace = list(state.get("trace", []))
        errors = list(state.get("errors", []))
        if action is None:
            trace.append("execute: no action")
            return {"trace": trace, "errors": errors}

        try:
            result = await action.execute()  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            log.error("action_execute_error", error=str(exc))
            errors.append(f"execute: {exc}")
            result = ActionResult(
                action=action, success=False, output=f"error: {exc}",  # type: ignore[arg-type]
            )

        trace.append(
            f"execute: kind={action.kind} success={result.success} "  # type: ignore[union-attr]
            f"output={result.output}"
        )
        log.info(
            "action_executed", kind=action.kind,  # type: ignore[union-attr]
            success=result.success, latency=result.latency_sec,
        )
        return {"result": result, "trace": trace, "errors": errors}
