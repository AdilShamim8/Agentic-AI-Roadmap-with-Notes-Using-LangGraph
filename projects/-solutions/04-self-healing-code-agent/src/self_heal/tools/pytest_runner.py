"""Pytest runner.

Runs pytest as a subprocess and parses the result into a structured
`PytestResult`. We capture stdout/stderr and the exit code, and we
extract per-test pass/fail counts from the short summary.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from self_heal.logging import get_logger

log = get_logger(__name__)


@dataclass
class TestFailure:
    """A single failing test node."""

    nodeid: str
    traceback: str = ""


@dataclass
class PytestResult:
    """Result of a pytest invocation."""

    exit_code: int
    stdout: str
    stderr: str
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    failures: list[TestFailure] = field(default_factory=list)
    target_passed: bool = False
    target_failed: bool = False

    @property
    def ok(self) -> bool:
        """True if pytest exited 0 (no failures, no errors)."""
        return self.exit_code == 0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors + self.skipped


# ── parsing ───────────────────────────────────────────────────
_SUMMARY_RE = re.compile(
    r"(?:(?P<passed>\d+) passed,?\s*)?"
    r"(?:(?P<failed>\d+) failed,?\s*)?"
    r"(?:(?P<errors>\d+) errors?,?\s*)?"
    r"(?:(?P<skipped>\d+) skipped,?\s*)?"
)
_FAILED_NODE_RE = re.compile(r"^FAILED\s+(.+?)(?:\s+-\s+.*)?$", re.MULTILINE)


def _parse_counts(stdout: str) -> dict[str, int]:
    """Pull pass/fail/error/skipped counts from the pytest summary line."""
    # Take the last line that contains "passed" or "failed" or "error".
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    for line in stdout.splitlines():
        if any(k in line for k in ("passed", "failed", "error", "skipped")):
            m = _SUMMARY_RE.search(line)
            if m:
                for k, v in m.groupdict(default="0").items():
                    if v:
                        counts[k] = int(v)
    return counts


def _extract_failure_blocks(stdout: str) -> list[TestFailure]:
    """Extract per-test tracebacks from pytest's `--tb=long` output."""
    failures: list[TestFailure] = []

    # First, capture nodeids from the FAILED summary lines.
    failed_nodes = _FAILED_NODE_RE.findall(stdout)

    # Then capture each `_ _ _ _`-delimited traceback block.
    # Pytest separates failures with a header line like:
    #   ============ FAILURES ============
    blocks = re.split(r"={5,}\s*FAILURES\s*={5,}", stdout)
    tb_section = blocks[1] if len(blocks) > 1 else ""
    # Each failure starts with a nodeid header followed by underscores.
    tb_chunks = re.split(r"^_+ [^\n]+ _+$", tb_section, flags=re.MULTILINE)
    tb_chunks = [c.strip() for c in tb_chunks if c.strip()]

    for i, nodeid in enumerate(failed_nodes):
        tb = tb_chunks[i] if i < len(tb_chunks) else ""
        failures.append(TestFailure(nodeid=nodeid.strip(), traceback=tb))

    return failures


def run_pytest(
    repo_path: Path,
    test_target: str | None = None,
    *,
    tb: str = "long",
    extra_args: list[str] | None = None,
    timeout: int = 120,
) -> PytestResult:
    """Run pytest in `repo_path`.

    Args:
        repo_path: working directory for pytest.
        test_target: optional nodeid (e.g. `tests/test_calc.py::test_add`).
            If None, runs the whole suite.
        tb: traceback style (`long`, `short`, `line`, `native`).
        extra_args: extra CLI args forwarded to pytest.
        timeout: subprocess timeout in seconds.
    """
    cmd = [
        "python",
        "-m",
        "pytest",
        "-ra",
        f"--tb={tb}",
        "--color=no",
        "-q",
    ]
    if test_target:
        cmd.append(test_target)
    if extra_args:
        cmd.extend(extra_args)

    log.debug("pytest.run", cwd=str(repo_path), cmd=cmd)
    proc = subprocess.run(
        cmd,
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    counts = _parse_counts(proc.stdout)
    failures = _extract_failure_blocks(proc.stdout)
    result = PytestResult(
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        passed=counts["passed"],
        failed=counts["failed"],
        errors=counts["errors"],
        skipped=counts["skipped"],
        failures=failures,
    )

    if test_target:
        for f in failures:
            if f.nodeid.split("::")[0] in test_target or test_target in f.nodeid:
                result.target_failed = True
        # If pytest exited 0 and the target was collected, it passed.
        if proc.returncode == 0 and not result.target_failed:
            result.target_passed = True

    log.debug(
        "pytest.done",
        exit_code=proc.returncode,
        passed=result.passed,
        failed=result.failed,
        errors=result.errors,
        target_passed=result.target_passed,
        target_failed=result.target_failed,
    )
    return result
