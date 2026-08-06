"""High-level agent orchestrator.

Wraps the compiled LangGraph runnable in a friendly Python API:

    from self_heal.agent import SelfHealAgent, RunConfig

    agent = SelfHealAgent()
    result = agent.run(RunConfig(repo_path=..., test_target=...))
    print(result.summary())
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from self_heal.config import Settings, get_settings
from self_heal.graph.builder import build_agent_graph
from self_heal.graph.state import AgentState, Status
from self_heal.llm.base import LLMProvider, provider_factory
from self_heal.logging import get_logger
from self_heal.observability import maybe_enable_tracing

log = get_logger(__name__)


@dataclass
class RunConfig:
    """Per-run configuration."""

    repo_path: str | Path
    test_target: str
    max_iterations: int | None = None
    work_branch: str = "self-heal/patch"
    open_pr: bool = False
    dry_run: bool = False

    def to_state(self, settings: Settings) -> AgentState:
        return AgentState(  # type: ignore[typeddict-item]
            repo_path=str(Path(self.repo_path).resolve()),
            test_target=self.test_target,
            work_branch=self.work_branch,
            max_iterations=self.max_iterations or settings.max_iterations,
            open_pr=self.open_pr,
            dry_run=self.dry_run,
            iteration=0,
            status="running",
            history=[],
            llm_calls=0,
            cost_usd=0.0,
            pr_url=None,
            error=None,
        )


@dataclass
class RunResult:
    """Final result of an agent run."""

    status: Status
    iterations: int
    llm_calls: int
    cost_usd: float
    pr_url: str | None
    final_state: dict[str, Any]

    def summary(self) -> str:
        lines = [
            f"status:       {self.status}",
            f"iterations:   {self.iterations}",
            f"llm_calls:    {self.llm_calls}",
            f"cost_usd:     ${self.cost_usd:.4f}",
            f"pr_url:       {self.pr_url or '-'}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SelfHealAgent:
    """The user-facing agent."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider = provider or provider_factory(self.settings)
        maybe_enable_tracing()
        self.graph = build_agent_graph(provider=self.provider)

    def run(self, config: RunConfig) -> RunResult:
        """Run the agent end-to-end and return a `RunResult`."""
        initial = config.to_state(self.settings)
        log.info(
            "agent.run.start",
            repo=initial["repo_path"],
            target=initial["test_target"],
            max_iter=initial["max_iterations"],
            provider=self.provider.name,
            dry_run=initial["dry_run"],
        )
        try:
            final_state = self.graph.invoke(initial, config={"recursion_limit": 50})
        except Exception as exc:
            log.error("agent.run.failed", error=str(exc))
            return RunResult(
                status="error",
                iterations=initial.get("iteration", 0),
                llm_calls=initial.get("llm_calls", 0),
                cost_usd=initial.get("cost_usd", 0.0),
                pr_url=None,
                final_state={"error": str(exc)},
            )

        status: Status = final_state.get("status", "failed")
        if status == "running":
            # Loop ended without explicit pass → exhausted.
            status = "exhausted"

        result = RunResult(
            status=status,
            iterations=final_state.get("iteration", 0),
            llm_calls=final_state.get("llm_calls", 0),
            cost_usd=final_state.get("cost_usd", 0.0),
            pr_url=final_state.get("pr_url"),
            final_state=dict(final_state),
        )
        log.info(
            "agent.run.done",
            status=result.status,
            iterations=result.iterations,
            llm_calls=result.llm_calls,
            cost_usd=round(result.cost_usd, 6),
        )
        return result
