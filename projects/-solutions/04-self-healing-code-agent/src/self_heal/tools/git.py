"""Git operations, run as subprocesses in the target repo.

We use the `git` CLI (not GitPython) to keep the dependency surface small
and to make the agent's git behavior trivially auditable from logs.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from self_heal.logging import get_logger

log = get_logger(__name__)


class GitError(RuntimeError):
    """Raised when a git command fails."""


def _run(cwd: Path, *args: str) -> str:
    log.debug("git.run", cwd=str(cwd), args=list(args))
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed (exit {proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def init_repo(path: Path) -> None:
    """Initialize a git repo if not already in one, and configure a dummy user."""
    if not (path / ".git").exists():
        _run(path, "init", "-q")
    # Set a local identity so commits don't fail in CI.
    try:
        _run(path, "config", "user.email", "self-heal-agent@example.com")
        _run(path, "config", "user.name", "Self-heal Agent")
    except GitError:
        pass  # already set globally


def current_branch(path: Path) -> str:
    return _run(path, "rev-parse", "--abbrev-ref", "HEAD").strip()


def checkout_new_branch(path: Path, branch: str) -> None:
    """Create and switch to `branch`. If it exists, just switch to it."""
    branches = _run(path, "branch", "--list", branch).strip()
    if branches:
        _run(path, "checkout", branch)
    else:
        _run(path, "checkout", "-b", branch)


def commit_all(path: Path, message: str) -> str:
    """Stage everything and commit; return the commit SHA."""
    _run(path, "add", "-A")
    # Don't fail if there's nothing to commit.
    proc = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=path,
        check=False,
    )
    if proc.returncode == 0:
        log.debug("git.commit.skipped", reason="nothing_staged")
        return _run(path, "rev-parse", "HEAD").strip()
    _run(path, "commit", "-q", "-m", message)
    return _run(path, "rev-parse", "HEAD").strip()


def clean_working_tree(path: Path) -> bool:
    """True if `git status --porcelain` is empty."""
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and proc.stdout.strip() == ""


def head_sha(path: Path) -> str:
    return _run(path, "rev-parse", "HEAD").strip()
