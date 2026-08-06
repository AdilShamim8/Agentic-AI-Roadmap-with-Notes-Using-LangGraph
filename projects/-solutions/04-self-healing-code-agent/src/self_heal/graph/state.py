"""Agent state schema (LangGraph TypedDict) and supporting dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict

from self_heal.llm.base import TokenUsage
from self_heal.tools.pytest_runner import PytestResult

Status = Literal["running", "passed", "failed", "exhausted", "error"]


@dataclass
class IterationRecord:
    """One pass through diagnose → patch → verify."""

    iteration: int
    diagnosis: str = ""
    patch_text: str = ""
    patch_files: list[str] = field(default_factory=list)
    verify: PytestResult | None = None
    reflexion: str = ""
    llm_calls: int = 0
    cost_usd: float = 0.0

    @property
    def passed(self) -> bool:
        return bool(
            self.verify
            and self.verify.target_passed
            and not self.verify.failed
            and not self.verify.errors
        )


class AgentState(TypedDict, total=False):
    """The mutable state passed between graph nodes.

    `total=False` because nodes only write the keys they care about; LangGraph
    merges per-node returns into this dict.
    """

    # ── inputs (set once at start) ─────────────────────────────
    repo_path: str
    test_target: str
    work_branch: str
    max_iterations: int
    open_pr: bool
    dry_run: bool

    # ── loop bookkeeping ───────────────────────────────────────
    iteration: int
    status: Status
    history: list[IterationRecord]

    # ── per-iteration artifacts (overwritten each loop) ────────
    # Field names are deliberately distinct from node names (reproduce/verify/
    # reflexion) because LangGraph forbids a node name colliding with a state key.
    repro_result: PytestResult
    diagnosis: str
    patch_text: str
    patch_files: list[str]
    verify_result: PytestResult
    reflexion_notes: str

    # ── accounting ─────────────────────────────────────────────
    llm_calls: int
    cost_usd: float
    tokens: TokenUsage

    # ── output ─────────────────────────────────────────────────
    pr_url: str | None
    error: str | None
