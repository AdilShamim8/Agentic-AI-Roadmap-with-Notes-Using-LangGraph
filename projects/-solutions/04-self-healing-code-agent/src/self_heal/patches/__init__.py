"""Patch / unified-diff helpers (re-exported)."""

from self_heal.patches.diff import (
    DiffError,
    FilePatch,
    Hunk,
    apply_diff,
    extract_diff,
    parse_diff,
)

__all__ = [
    "DiffError",
    "FilePatch",
    "Hunk",
    "apply_diff",
    "extract_diff",
    "parse_diff",
]
