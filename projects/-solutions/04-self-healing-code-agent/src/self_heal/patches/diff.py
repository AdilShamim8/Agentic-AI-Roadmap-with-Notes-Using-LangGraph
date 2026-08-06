"""Unified-diff parsing and application.

This module supports multi-file unified diffs (the stretch goal), i.e. a single
diff blob that touches more than one file. Each `---`/`+++` pair delimits a
per-file hunk group. Hunk application uses fuzzy context matching with a small
fallback window so the agent can still apply patches when line numbers drift.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from self_heal.logging import get_logger

log = get_logger(__name__)


class DiffError(ValueError):
    """Raised when a diff cannot be parsed or applied."""


@dataclass
class Hunk:
    """One `@@ ... @@` block within a file."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str] = field(default_factory=list)  # each: ' context' | '-removed' | '+added'


@dataclass
class FilePatch:
    """One `---`/`+++` block within a diff."""

    old_path: str
    new_path: str
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def is_new_file(self) -> bool:
        return self.old_path == "/dev/null"

    @property
    def is_deleted(self) -> bool:
        return self.new_path == "/dev/null"


# ── extraction ───────────────────────────────────────────────
_FENCE_RE = re.compile(r"```(?:diff|patch)?\s*\n(.*?)```", re.DOTALL)


def extract_diff(text: str) -> str:
    """Pull a unified diff out of an LLM response that may wrap it in a fence.

    If the text contains a ```diff``` or ```patch``` block, return the inside.
    Otherwise return the text as-is (we'll try to parse it).
    """
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


# ── parsing ──────────────────────────────────────────────────
_HUNK_HEADER_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")


def parse_diff(diff_text: str) -> list[FilePatch]:
    """Parse a (possibly multi-file) unified diff into `FilePatch` objects."""
    # Normalize line endings.
    lines = diff_text.replace("\r\n", "\n").split("\n")

    patches: list[FilePatch] = []
    current: FilePatch | None = None
    current_hunk: Hunk | None = None

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("--- "):
            # Start a new file patch.
            old_path = _strip_path(line[4:])
            # Look ahead for the +++ line.
            new_path = old_path
            if i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
                new_path = _strip_path(lines[i + 1][4:])
                i += 1
            current = FilePatch(old_path=old_path, new_path=new_path)
            patches.append(current)
            current_hunk = None

        elif line.startswith("@@"):
            if current is None:
                raise DiffError(f"Hunk header outside file patch: {line!r}")
            m = _HUNK_HEADER_RE.match(line)
            if not m:
                raise DiffError(f"Malformed hunk header: {line!r}")
            old_start = int(m.group(1))
            old_count = int(m.group(2) or "1")
            new_start = int(m.group(3))
            new_count = int(m.group(4) or "1")
            current_hunk = Hunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
            )
            current.hunks.append(current_hunk)

        elif current_hunk is not None and (
            line.startswith(" ") or line.startswith("+") or line.startswith("-")
        ):
            # Hunk body line. Store the full line including the sign prefix
            # (' ' context, '-' removed, '+' added). Bare empty lines (no
            # leading space) are NOT treated as context — they're either
            # separators between hunks or trailing-newline artifacts, and
            # falling through to "skip" is the safe choice. Real `git diff`
            # always prefixes context lines with a space.
            current_hunk.lines.append(line)

        # Skip `diff --git`, `index`, `new file mode`, `deleted file mode`, etc.

        i += 1

    if not patches:
        raise DiffError("No `---`/`+++` file header found in diff")

    return patches


def _strip_path(raw: str) -> str:
    """Strip the leading `a/` or `b/` and a trailing tab+timestamp."""
    # Strip trailing tab and timestamp, e.g. `b/foo.py\t2024-01-01 12:00:00`.
    raw = raw.split("\t", 1)[0]
    # Strip a/ b/ prefixes used by git.
    if raw.startswith("a/") or raw.startswith("b/"):
        raw = raw[2:]
    return raw.strip()


# ── application ──────────────────────────────────────────────
def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _apply_hunk(file_lines: list[str], hunk: Hunk) -> list[str]:
    """Apply a single hunk to a list of file lines, return the new list.

    Uses exact context match anchored at `hunk.old_start`; if that fails, falls
    back to a fuzzy search within a ±20-line window.
    """
    # The "old" side of the hunk = context + removed lines.
    old_block = [ln[1:] for ln in hunk.lines if ln.startswith((" ", "-"))]
    new_block = [ln[1:] for ln in hunk.lines if ln.startswith((" ", "+"))]

    # 1-indexed → 0-indexed. Hunk headers can be 0 for empty files; clamp.
    start = max(0, hunk.old_start - 1)

    # Try exact match at the recorded position.
    if _matches_at(file_lines, start, old_block):
        return file_lines[:start] + new_block + file_lines[start + len(old_block) :]

    # Fuzzy: search a window around `start`.
    window = 20
    lo = max(0, start - window)
    hi = min(len(file_lines), start + window)
    for cand in range(lo, hi):
        if _matches_at(file_lines, cand, old_block):
            log.debug("diff.hunk.fuzzy_match", expected=start, found=cand)
            return file_lines[:cand] + new_block + file_lines[cand + len(old_block) :]

    raise DiffError(
        f"Could not apply hunk @@ -{hunk.old_start},{hunk.old_count} "
        f"+{hunk.new_start},{hunk.new_count} @@: context not found"
    )


def _matches_at(file_lines: list[str], pos: int, block: list[str]) -> bool:
    if pos < 0 or pos + len(block) > len(file_lines):
        return False
    return all(file_lines[pos + i].rstrip() == bl.rstrip() for i, bl in enumerate(block))


def apply_diff(repo_path: Path, diff_text: str, *, dry_run: bool = False) -> list[Path]:
    """Parse and apply a (possibly multi-file) diff to `repo_path`.

    Returns the list of paths that were modified or created.
    Raises `DiffError` on any failure (no partial application across files:
    if one file fails, earlier files are still written — caller should `git checkout`).
    """
    diff_text = extract_diff(diff_text)
    patches = parse_diff(diff_text)
    touched: list[Path] = []

    for patch in patches:
        target = repo_path / patch.new_path
        if patch.is_new_file:
            # Construct from new lines of all hunks.
            new_lines: list[str] = []
            for h in patch.hunks:
                new_lines.extend(ln[1:] for ln in h.lines if ln.startswith((" ", "+")))
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            touched.append(target)
            log.info("diff.file.created", path=str(target), lines=len(new_lines))
            continue

        if patch.is_deleted:
            if not dry_run and target.exists():
                target.unlink()
            touched.append(target)
            log.info("diff.file.deleted", path=str(target))
            continue

        file_lines = _read_lines(target)
        original = list(file_lines)
        for hunk in patch.hunks:
            file_lines = _apply_hunk(file_lines, hunk)
        if file_lines == original:
            log.warning("diff.file.noop", path=str(target))
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(file_lines) + "\n", encoding="utf-8")
        touched.append(target)
        log.info("diff.file.modified", path=str(target), hunks=len(patch.hunks))

    return touched
