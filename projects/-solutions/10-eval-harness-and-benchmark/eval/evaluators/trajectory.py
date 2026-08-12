"""Trajectory evaluator.

Compares an agent's executed trajectory to a hand-labeled reference
trajectory (stored in `benchmarks/trajectories/*.jsonl`).

Three checks are run, each contributing to the score:

1. **Step count** — penalty if the agent took a wildly different number of
   steps than the reference.
2. **Tool-call sequence** — Jaccard overlap of the ordered tool-call names.
3. **Final state** — exact match of the agent's final answer against the
   reference's final answer (normalised).

The final score is a weighted average (0.2 / 0.4 / 0.4 by default).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eval.evaluators.base import BaseEvaluator
from eval.schemas import (
    AgentOutput,
    DatasetRow,
    EvalResult,
    Trajectory,
    TrajectoryStep,
)
from eval.utils import answer_to_str, normalize_answer
from eval.config import get_settings


class TrajectoryMatchEvaluator(BaseEvaluator):
    """Compare the agent's trajectory to a hand-labeled reference.

    Params:
        trajectories_dir: override the directory for reference trajectories.
        weight_steps: weight for the step-count sub-score. Default 0.2.
        weight_tools: weight for the tool-sequence sub-score. Default 0.4.
        weight_final: weight for the final-answer sub-score. Default 0.4.
        step_tolerance: how many steps off is "no penalty". Default 1.
    """

    name = "trajectory_match"

    def __init__(self, **params: Any) -> None:
        super().__init__(**params)
        s = get_settings()
        self.trajectories_dir = Path(
            params.get("trajectories_dir", str(s.trajectories_dir))
        )
        self.w_steps = float(params.get("weight_steps", 0.2))
        self.w_tools = float(params.get("weight_tools", 0.4))
        self.w_final = float(params.get("weight_final", 0.4))
        self.step_tolerance = int(params.get("step_tolerance", 1))
        self._cache: dict[str, Trajectory] = {}

    # ----- reference loading ---------------------------------------------

    def _load_reference(self, ref_id: str) -> Trajectory | None:
        if ref_id in self._cache:
            return self._cache[ref_id]
        # Look for any trajectories/*.jsonl that contains this id.
        if not self.trajectories_dir.exists():
            return None
        for path in self.trajectories_dir.glob("*.jsonl"):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    obj = json.loads(line)
                    if obj.get("id") == ref_id:
                        steps = [TrajectoryStep(**s) for s in obj.get("steps", [])]
                        traj = Trajectory(steps=steps, metadata=obj.get("metadata", {}))
                        traj.metadata["final_answer"] = obj.get("final_answer")
                        self._cache[ref_id] = traj
                        return traj
        return None

    # ----- main ----------------------------------------------------------

    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        if trajectory is None:
            trajectory = output.trajectory

        ref_id = row.trajectory_ref or row.id
        ref = self._load_reference(ref_id)
        if ref is None:
            # No reference trajectory for this row → neutral score.
            return EvalResult(
                evaluator=self.display_name(),
                row_id=row.id,
                passed=True,
                score=1.0,
                rationale=f"No reference trajectory for id={ref_id}; skipping.",
                details={"reference_found": False},
            )

        s_steps = _score_step_count(
            len(trajectory.steps), len(ref.steps), self.step_tolerance
        )
        s_tools = _score_tool_sequence(trajectory.steps, ref.steps)
        s_final = _score_final_answer(
            answer_to_str(output.answer),
            answer_to_str(ref.metadata.get("final_answer")),
        )

        score = (
            self.w_steps * s_steps + self.w_tools * s_tools + self.w_final * s_final
        )
        score = max(0.0, min(1.0, score))
        passed = score >= 0.7
        return EvalResult(
            evaluator=self.display_name(),
            row_id=row.id,
            passed=passed,
            score=score,
            rationale=(
                f"steps={s_steps:.2f} tools={s_tools:.2f} final={s_final:.2f} "
                f"(weights {self.w_steps}/{self.w_tools}/{self.w_final})."
            ),
            details={
                "reference_found": True,
                "reference_id": ref_id,
                "step_count": {"got": len(trajectory.steps), "ref": len(ref.steps)},
                "subscores": {
                    "steps": s_steps,
                    "tools": s_tools,
                    "final": s_final,
                },
            },
        )


# ---------------------------------------------------------------------------
# Sub-scorers
# ---------------------------------------------------------------------------


def _score_step_count(got: int, ref: int, tol: int) -> float:
    """1.0 if within tol steps, linearly decays to 0 at 3x tol off."""

    if ref == 0:
        return 1.0 if got == 0 else 0.0
    diff = abs(got - ref)
    if diff <= tol:
        return 1.0
    return max(0.0, 1.0 - (diff - tol) / max(1.0, 3.0 * tol))


def _score_tool_sequence(got: list[TrajectoryStep], ref: list[TrajectoryStep]) -> float:
    """Jaccard overlap of the *ordered* tool-call name sequences.

    If neither trajectory has tool calls, returns 1.0 (vacuously equal).
    """

    g_tools = [s.tool_call.name for s in got if s.tool_call is not None]
    r_tools = [s.tool_call.name for s in ref if s.tool_call is not None]
    if not g_tools and not r_tools:
        return 1.0
    # Sequence-aware Jaccard: count positional matches first, then fall
    # back to set overlap.
    pos = sum(1 for a, b in zip(g_tools, r_tools) if a == b)
    set_g = set(g_tools)
    set_r = set(r_tools)
    union = set_g | set_r
    inter = set_g & set_r
    jaccard = len(inter) / max(1, len(union))
    positional = pos / max(1, max(len(g_tools), len(r_tools)))
    return 0.5 * jaccard + 0.5 * positional


def _score_final_answer(got: str, ref: str) -> float:
    if not ref:
        return 1.0
    g = normalize_answer(got)
    r = normalize_answer(ref)
    if g == r:
        return 1.0
    # Fall back to token overlap so partial-credit works.
    g_tokens = set(g.split())
    r_tokens = set(r.split())
    if not r_tokens:
        return 0.0
    return len(g_tokens & r_tokens) / len(r_tokens)
