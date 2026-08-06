"""Filesystem helpers: reading files, locating relevant source for a traceback."""

from __future__ import annotations

import ast
import re
from pathlib import Path

_MAX_BYTES = 64_000  # cap how much we feed the LLM per file
_MAX_FILES = 8


def read_file(path: Path, max_bytes: int = _MAX_BYTES) -> str:
    """Read a file, truncating to `max_bytes` to protect the LLM context window."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return f"<file not found: {path}>"
    except OSError as exc:
        return f"<read error {exc!r}>"
    if len(data) > max_bytes:
        text = data[:max_bytes].decode("utf-8", errors="replace")
        return text + f"\n\n... [truncated, {len(data) - max_bytes} more bytes]\n"
    return data.decode("utf-8", errors="replace")


# Matches `File "path/to/x.py", line N` (pytest) and `path/to/x.py:N` (some tools).
_TRACEBACK_FILE_RE = re.compile(
    r'(?:File "|^|\s)([^\s"]+\.py)[",:]?\s*(?:line\s+)?(\d+)?', re.MULTILINE
)


def extract_file_lines_from_traceback(tb: str) -> list[tuple[str, int]]:
    """Pull (file, line) pairs out of a Python traceback string."""
    seen: set[tuple[str, int]] = set()
    out: list[tuple[str, int]] = []
    for m in _TRACEBACK_FILE_RE.finditer(tb):
        path, line = m.group(1), m.group(2)
        line_n = int(line) if line else 0
        key = (path, line_n)
        if key not in seen and "<" not in path:
            seen.add(key)
            out.append(key)
    return out


def resolve_imported_sources(repo_path: Path, file_path: Path) -> list[Path]:
    """Parse `file_path` for import statements and resolve them to source files.

    Handles both `import X` and `from X.Y import Z` forms, resolving `X` (or
    `X.Y`) to `<repo>/src/X.py` or `<repo>/src/X/Y.py` or `<repo>/X.py`. This
    is what makes the agent work when a test fails at an assertion (so the
    traceback only references the test file, not the source under test).
    """
    out: list[Path] = []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return out

    search_roots = [repo_path / "src", repo_path]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.extend(_resolve_module(search_roots, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.extend(_resolve_module(search_roots, node.module))
    return out


def _resolve_module(roots: list[Path], dotted: str) -> list[Path]:
    """Resolve a dotted module name to candidate file paths that exist."""
    parts = dotted.split(".")
    out: list[Path] = []
    for root in roots:
        # foo.bar.baz -> root/foo/bar/baz.py  or  root/foo/bar/baz/__init__.py
        pkg_dir = root.joinpath(*parts)
        mod_file = root.joinpath(*parts[:-1], parts[-1] + ".py")
        if mod_file.exists():
            out.append(mod_file)
        if pkg_dir.is_dir():
            init = pkg_dir / "__init__.py"
            if init.exists():
                out.append(init)
    return out


def read_relevant_files(
    repo_path: Path,
    traceback: str,
    *,
    extra_paths: list[Path] | None = None,
    follow_imports: bool = True,
    max_files: int = _MAX_FILES,
) -> dict[str, str]:
    """Read files referenced in a traceback, plus any extras, for the LLM.

    When `follow_imports=True` (default), also parses each discovered file for
    `import` / `from X import` statements and pulls in the referenced source
    files. This is critical for the common case where a test fails at an
    assertion — the traceback only mentions the test file, but the bug lives
    in a module the test imports.

    Returns a dict mapping repo-relative path → file contents.
    """
    out: dict[str, str] = {}

    candidates: list[Path] = []
    for rel, _line in extract_file_lines_from_traceback(traceback):
        # Strip leading `./` or `/`.
        rel = rel.lstrip("./")
        p = (repo_path / rel).resolve()
        try:
            p.relative_to(repo_path.resolve())
        except ValueError:
            continue  # outside repo, skip
        if p.exists() and p.is_file():
            candidates.append(p)

    if extra_paths:
        candidates.extend(extra_paths)

    # Follow imports one level deep (avoids pulling in the whole stdlib).
    if follow_imports:
        seen_for_imports: set[Path] = {p.resolve() for p in candidates}
        import_candidates: list[Path] = []
        for c in list(candidates):
            for imp in resolve_imported_sources(repo_path, c):
                rp = imp.resolve()
                if rp in seen_for_imports:
                    continue
                seen_for_imports.add(rp)
                import_candidates.append(imp)
        candidates.extend(import_candidates)

    # De-dup while preserving order.
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in candidates:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(p)
        if len(uniq) >= max_files:
            break

    for p in uniq:
        try:
            rel = p.relative_to(repo_path.resolve()).as_posix()
        except ValueError:
            rel = str(p)
        out[rel] = read_file(p)

    return out
