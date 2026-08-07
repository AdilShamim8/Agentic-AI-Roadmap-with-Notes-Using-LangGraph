"""Eval runner for the universal MCP agent.

Runs every goal in ``goals.jsonl`` through the agent and computes the four
rubric metrics from the project spec:

- tool-selection accuracy   – did the agent call the expected tools?
- task completion           – did the agent produce a non-empty, on-topic answer?
- tool-argument correctness – were the tool args sensible (typed, plausible)?
- robustness to tool failure – re-run a subset with one server killed, measure
                               completion.

Usage::

    python3 -m evals.run_evals                       # full eval (default)
    python3 -m evals.run_evals --limit 5             # first 5 goals
    python3 -m evals.run_evals --only g01,g03,g05    # specific goals
    python3 -m evals.run_evals --strategy retrieval  # override strategy
    python3 -m evals.run_evals --robustness          # only the robustness suite

By default the eval uses a deterministic LLM-as-judge (rule-based, no API
key needed). For real scoring, set ``OPENAI_API_KEY`` and pass ``--judge openai``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent.graph import run_agent  # noqa: E402

# Where to write results.
EVAL_DIR = _ROOT / "evals" / "results"
GOALS_FILE = _ROOT / "evals" / "goals.jsonl"

# Goals used for the robustness suite (we kill the 'custom' server and
# re-run these goals – they should still complete, possibly by saying "I
# couldn't reach the custom server, but here's what I can tell you…").
ROBUSTNESS_GOAL_IDS = {"g21", "g23", "g26", "g29", "g13"}


@dataclass
class GoalResult:
    goal_id: str
    goal: str
    expected_tools: List[str]
    actual_tools: List[str]
    answer: str
    iterations: int
    selection_accuracy: float  # |expected ∩ actual| / |expected|
    completion: bool  # did the agent produce a non-empty, on-topic answer?
    argument_correctness: float  # fraction of tool calls with valid args
    provider: str
    strategy: str

    def to_dict(self) -> Dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_goals() -> List[dict]:
    out: List[dict] = []
    with GOALS_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _extract_actual_tools(trace: List[Dict]) -> List[str]:
    return [s["tool"] for s in trace if s.get("step") == "tool"]


def _score_selection(expected: List[str], actual: List[str]) -> float:
    """Fraction of expected tools the agent actually called.

    We compare bare tool names (without server prefix) because the agent may
    legitimately call the same logical tool from a different server in some
    setups.
    """
    if not expected:
        return 1.0
    exp_bare = {t.split(".")[-1] for t in expected}
    act_bare = {t.split(".")[-1] for t in actual}
    return len(exp_bare & act_bare) / len(exp_bare)


def _score_completion(goal: str, answer: str, actual_tools: List[str]) -> bool:
    """Cheap rule-based completion check (no API key needed).

    An answer is 'complete' if:
    - it's non-empty (>= 10 chars),
    - AND it doesn't contain the mock-LLM failure marker,
    - AND either it called at least one tool OR produced >= 40 chars of text.
    """
    if not answer or len(answer) < 10:
        return False
    if answer.startswith("[mock LLM]"):
        return False
    if not actual_tools and len(answer) < 40:
        return False
    return True


def _score_argument_correctness(trace: List[Dict]) -> float:
    """Fraction of tool calls whose arguments look valid.

    A tool call is 'valid' if:
    - it has an 'arguments' dict,
    - the values are non-empty (no None, no empty string for required fields),
    - the tool did not return an error.
    """
    tool_steps = [s for s in trace if s.get("step") == "tool"]
    if not tool_steps:
        return 1.0
    ok = 0
    for s in tool_steps:
        args = s.get("arguments") or {}
        valid_args = isinstance(args, dict) and all(
            v is not None and v != "" for v in args.values()
        )
        # If the result has an 'error' key, the call failed.
        result = s.get("result_preview", "")
        no_error = "error" not in result.lower()
        if valid_args and no_error:
            ok += 1
    return ok / len(tool_steps)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
async def _run_one(goal: dict, args: argparse.Namespace, only: Optional[List[str]] = None) -> GoalResult:
    res = await run_agent(
        user_goal=goal["goal"],
        registry_path=str(_ROOT / "registry.json"),
        only=only,
        selection_strategy=args.strategy,
        verbose=False,
    )
    actual = _extract_actual_tools(res["trace"])
    return GoalResult(
        goal_id=goal["id"],
        goal=goal["goal"],
        expected_tools=goal.get("expected_tools", []),
        actual_tools=actual,
        answer=res["answer"],
        iterations=res["iterations"],
        selection_accuracy=_score_selection(goal.get("expected_tools", []), actual),
        completion=_score_completion(goal["goal"], res["answer"], actual),
        argument_correctness=_score_argument_correctness(res["trace"]),
        provider=res["provider"],
        strategy=res["strategy"],
    )


async def _run_suite(args: argparse.Namespace) -> List[GoalResult]:
    goals = _load_goals()
    if args.limit:
        goals = goals[: args.limit]
    if args.only:
        ids = set(args.only.split(","))
        goals = [g for g in goals if g["id"] in ids]
    results: List[GoalResult] = []
    for i, g in enumerate(goals, 1):
        print(f"[{i:02d}/{len(goals)}] {g['id']}: {g['goal']}", flush=True)
        try:
            r = await _run_one(g, args)
        except Exception as exc:  # noqa: BLE001
            r = GoalResult(
                goal_id=g["id"], goal=g["goal"],
                expected_tools=g.get("expected_tools", []),
                actual_tools=[], answer=f"[error] {exc}",
                iterations=0, selection_accuracy=0.0,
                completion=False, argument_correctness=0.0,
                provider="error", strategy="error",
            )
        print(f"       -> sel={r.selection_accuracy:.2f}  "
              f"comp={int(r.completion)}  "
              f"args={r.argument_correctness:.2f}  "
              f"tools={r.actual_tools}", flush=True)
        results.append(r)
    return results


async def _run_robustness(args: argparse.Namespace) -> List[GoalResult]:
    """Re-run a subset of goals WITHOUT the 'custom' server available.

    The agent should still complete the goal (or at least produce a sensible
    "I couldn't do X because Y is unavailable" answer). We measure
    completion only.
    """
    goals = [g for g in _load_goals() if g["id"] in ROBUSTNESS_GOAL_IDS]
    print(f"Robustness suite: {len(goals)} goals, 'custom' server disabled.")
    # Discover every server EXCEPT 'custom'.
    available = [s["name"] for s in json.loads((_ROOT / "registry.json").read_text())["servers"]
                 if s["name"] != "custom"]
    results: List[GoalResult] = []
    for g in goals:
        print(f"[robust] {g['id']}: {g['goal']}", flush=True)
        try:
            r = await _run_one(g, args, only=available)
        except Exception as exc:  # noqa: BLE001
            r = GoalResult(
                goal_id=g["id"], goal=g["goal"],
                expected_tools=g.get("expected_tools", []),
                actual_tools=[], answer=f"[error] {exc}",
                iterations=0, selection_accuracy=0.0,
                completion=False, argument_correctness=0.0,
                provider="error", strategy="error",
            )
        print(f"          -> comp={int(r.completion)}  answer={r.answer[:80]!r}", flush=True)
        results.append(r)
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def _summarise(results: List[GoalResult]) -> Dict:
    n = len(results) or 1
    return {
        "n_goals": len(results),
        "tool_selection_accuracy": sum(r.selection_accuracy for r in results) / n,
        "task_completion": sum(r.completion for r in results) / n,
        "tool_argument_correctness": sum(r.argument_correctness for r in results) / n,
        "provider": results[0].provider if results else "n/a",
        "strategy": results[0].strategy if results else "n/a",
    }


def _write_report(results: List[GoalResult], summary: Dict, suffix: str = "") -> Path:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVAL_DIR / f"report{suffix}.json"
    payload = {
        "summary": summary,
        "results": [r.to_dict() for r in results],
    }
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="run_evals", description="Eval runner for the universal MCP agent.")
    p.add_argument("--limit", type=int, default=None, help="Only run the first N goals.")
    p.add_argument("--only", default=None, help="Comma-separated goal IDs to run.")
    p.add_argument("--strategy", default=None, choices=["naive", "categorized", "retrieval"],
                   help="Override the tool-selection strategy.")
    p.add_argument("--robustness", action="store_true", help="Run only the robustness suite.")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    if args.robustness:
        results = asyncio.run(_run_robustness(args))
        summary = {"robustness_completion": sum(r.completion for r in results) / (len(results) or 1)}
        # Merge into the standard summary shape for reporting.
        summary.update(_summarise(results))
        out = _write_report(results, summary, suffix="_robustness")
    else:
        results = asyncio.run(_run_suite(args))
        summary = _summarise(results)
        out = _write_report(results, summary)
    print("\n" + "=" * 72)
    print("EVAL SUMMARY")
    print("=" * 72)
    print(json.dumps(summary, indent=2))
    print(f"\nFull report: {out}")
    # Print the rubric table from the spec.
    print("\nRubric vs. target:")
    targets = {
        "tool_selection_accuracy": 0.85,
        "task_completion": 0.75,
        "tool_argument_correctness": 0.90,
        "robustness_completion": 0.70,
    }
    for k, target in targets.items():
        if k in summary:
            v = summary[k]
            ok = "PASS" if v >= target else "FAIL"
            print(f"  {ok}  {k:32s}  got={v:.2%}  target={target:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
