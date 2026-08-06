"""Eval case discovery and per-case execution.

Each fixture case is a directory under `fixtures/` with this layout:

    case_XX_name/
      src/...                # buggy source
      tests/test_*.py        # failing test(s)
      pyproject.toml         # sets pythonpath = ["src"]
      expected_patch.diff    # gold patch (informational)
      case.json              # case metadata (target test, etc.)

The eval runner copies each case into a temp dir, inits a git repo, runs the
agent, and records the outcome.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from self_heal.agent import RunConfig, RunResult, SelfHealAgent
from self_heal.logging import get_logger
from self_heal.tools.git import init_repo
from self_heal.tools.pytest_runner import run_pytest

log = get_logger(__name__)


@dataclass
class CaseResult:
    """Outcome of running the agent on a single fixture case."""

    name: str
    target_test: str
    passed: bool
    no_regression: bool
    iterations: int
    llm_calls: int
    cost_usd: float
    status: str
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvalCase:
    """A discovered fixture case."""

    name: str
    path: Path
    target_test: str
    expected_pass: bool = True  # all our fixtures are expected to be fixable


def discover_cases(fixtures_dir: Path) -> list[EvalCase]:
    """Find all `case_*/` subdirectories that contain a `case.json`."""
    cases: list[EvalCase] = []
    if not fixtures_dir.exists():
        return cases
    for sub in sorted(fixtures_dir.iterdir()):
        if not sub.is_dir() or not sub.name.startswith("case_"):
            continue
        meta = sub / "case.json"
        if meta.exists():
            data = json.loads(meta.read_text())
            target = data.get("target_test", "")
        else:
            # Infer: take the first test file's first test function name.
            target = _infer_target_test(sub)
        cases.append(
            EvalCase(
                name=sub.name,
                path=sub,
                target_test=target,
            )
        )
    return cases


def _infer_target_test(case_dir: Path) -> str:
    """Best-effort: derive a pytest nodeid from a case without case.json."""
    tests_dir = case_dir / "tests"
    if not tests_dir.exists():
        return ""
    test_files = sorted(tests_dir.glob("test_*.py"))
    if not test_files:
        return ""
    tf = test_files[0]
    # Find the first `def test_...` in the file.
    for line in tf.read_text().splitlines():
        line = line.strip()
        if line.startswith("def test_"):
            fn = line.split("(")[0][len("def ") :]
            rel = tf.relative_to(case_dir).as_posix()
            return f"{rel}::{fn}"
    return tf.relative_to(case_dir).as_posix()


class EvalRunner:
    """Runs the agent over a set of fixture cases."""

    def __init__(self, agent: SelfHealAgent | None = None) -> None:
        self.agent = agent or SelfHealAgent()

    def run_case(self, case: EvalCase, max_iterations: int = 3) -> CaseResult:
        """Run a single case in a fresh temp copy."""
        with tempfile.TemporaryDirectory(prefix=f"selfheal-eval-{case.name}-") as tmp:
            tmp_path = Path(tmp)
            case_copy = tmp_path / case.name
            shutil.copytree(case.path, case_copy)

            # Init git so the agent can branch + commit.
            init_repo(case_copy)
            # Make an initial commit so the branch has a base.
            try:
                from self_heal.tools.git import commit_all

                commit_all(case_copy, "baseline")
            except Exception as exc:
                log.warning("eval.case.git_init_failed", case=case.name, error=str(exc))

            # Baseline: confirm the target test actually fails.
            baseline = run_pytest(case_copy, case.target_test)
            if baseline.target_passed:
                log.warning(
                    "eval.case.already_passing",
                    case=case.name,
                    target=case.target_test,
                )

            cfg = RunConfig(
                repo_path=case_copy,
                test_target=case.target_test,
                max_iterations=max_iterations,
                open_pr=False,
                dry_run=False,
            )

            try:
                result: RunResult = self.agent.run(cfg)
            except Exception as exc:
                log.error("eval.case.crashed", case=case.name, error=str(exc))
                return CaseResult(
                    name=case.name,
                    target_test=case.target_test,
                    passed=False,
                    no_regression=False,
                    iterations=0,
                    llm_calls=0,
                    cost_usd=0.0,
                    status="error",
                    error=str(exc),
                )

            # Confirm: target passes AND no other tests broke.
            post = run_pytest(case_copy, None, tb="short")
            passed = (
                result.status == "passed" and post.target_passed
                if case.target_test
                else result.status == "passed"
            )
            # `post.target_passed` only set when a target was given; check exit code instead.
            passed = result.status == "passed" and post.exit_code == 0
            no_regression = post.exit_code == 0

            return CaseResult(
                name=case.name,
                target_test=case.target_test,
                passed=passed,
                no_regression=no_regression,
                iterations=result.iterations,
                llm_calls=result.llm_calls,
                cost_usd=result.cost_usd,
                status=result.status,
                error=None,
            )

    def run_all(
        self,
        cases: list[EvalCase],
        max_iterations: int = 3,
    ) -> list[CaseResult]:
        return [self.run_case(c, max_iterations=max_iterations) for c in cases]
