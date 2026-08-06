"""Tools the agent uses: git, pytest, filesystem, unified-diff applier."""

from __future__ import annotations

from self_heal.patches.diff import apply_diff, extract_diff, parse_diff
from self_heal.tools.fs import read_file, read_relevant_files
from self_heal.tools.git import (
    checkout_new_branch,
    clean_working_tree,
    commit_all,
    current_branch,
    init_repo,
)
from self_heal.tools.pytest_runner import PytestResult, run_pytest

__all__ = [
    "PytestResult",
    "apply_diff",
    "checkout_new_branch",
    "clean_working_tree",
    "commit_all",
    "current_branch",
    "extract_diff",
    "init_repo",
    "parse_diff",
    "read_file",
    "read_relevant_files",
    "run_pytest",
]
