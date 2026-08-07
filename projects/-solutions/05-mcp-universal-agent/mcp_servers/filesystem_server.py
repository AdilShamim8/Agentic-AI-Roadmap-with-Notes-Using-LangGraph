"""Filesystem MCP server.

Exposes read / write / list / search tools scoped to a single root directory
(default ``./data``). The root is taken from the ``MCP_FS_ROOT`` env var so
the same server binary can be pointed at different sandboxes by the registry.

Run as a stdio MCP server::

    MCP_FS_ROOT=./data python3 -m mcp_servers.filesystem_server
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from mcp.server.fastmcp import FastMCP

# Resolve the sandbox root ONCE at import time. All tools refuse to escape it.
_FS_ROOT = Path(os.environ.get("MCP_FS_ROOT", "./data")).resolve()
_FS_ROOT.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("filesystem")


def _safe(path: str) -> Path:
    """Resolve ``path`` under ``_FS_ROOT`` and reject path-traversal escapes."""
    candidate = (_FS_ROOT / path).resolve()
    if _FS_ROOT not in candidate.parents and candidate != _FS_ROOT:
        raise PermissionError(f"Path '{path}' escapes the filesystem sandbox")
    return candidate


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def list_files(directory: str = ".") -> List[str]:
    """List files (relative to the sandbox root) inside ``directory``.

    Use this first when you don't know which files exist. Returns relative
    paths so the caller can pass them back to ``read_file``.

    Args:
        directory: Sub-directory inside the sandbox to list. Use "." for the
            root. Traversal outside the sandbox (e.g. "../etc") is rejected.

    Returns:
        A list of relative file paths. Empty list if the directory has no
        regular files.
    """
    root = _safe(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"Not a directory: {directory}")
    out: List[str] = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out.append(str(p.relative_to(_FS_ROOT)))
    return out


@mcp.tool()
def read_file(path: str) -> str:
    """Read the full text contents of a UTF-8 file inside the sandbox.

    Args:
        path: Relative path inside the sandbox (e.g. "sample.txt" or
            "notes.md"). Path-traversal escapes are rejected.

    Returns:
        The file contents as a string. Raises FileNotFoundError if the file
        does not exist.
    """
    p = _safe(path)
    if not p.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    return p.read_text(encoding="utf-8")


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write ``content`` to ``path`` inside the sandbox, creating parent
    directories as needed. Overwrites existing files.

    Args:
        path: Relative path inside the sandbox.
        content: The text to write. UTF-8 encoded.

    Returns:
        The absolute path of the written file (within the sandbox).
    """
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return str(p)


@mcp.tool()
def search_files(query: str) -> List[str]:
    """Grep-style case-insensitive substring search across every file in the
    sandbox. Returns the relative paths of files that contain ``query``.

    Use this when the user asks "which file mentions X" or "find the doc that
    talks about Y". Reads every file as UTF-8 text; binary files are skipped.

    Args:
        query: Case-insensitive substring to search for.

    Returns:
        List of relative paths whose contents contain the query. Empty list
        if nothing matches.
    """
    needle = query.lower()
    hits: List[str] = []
    for p in _FS_ROOT.rglob("*"):
        if not p.is_file():
            continue
        try:
            if needle in p.read_text(encoding="utf-8").lower():
                hits.append(str(p.relative_to(_FS_ROOT)))
        except (UnicodeDecodeError, OSError):
            continue
    return hits


@mcp.tool()
def file_stats(path: str) -> dict:
    """Return size (bytes), line count and last-modified timestamp for a file.

    Useful when the user asks "how big is X" or "when was X last updated".

    Args:
        path: Relative path inside the sandbox.

    Returns:
        Dict with keys: ``path``, ``size_bytes``, ``lines``, ``modified``.
    """
    p = _safe(path)
    if not p.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    text = p.read_text(encoding="utf-8")
    return {
        "path": str(p.relative_to(_FS_ROOT)),
        "size_bytes": p.stat().st_size,
        "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        "modified": int(p.stat().st_mtime),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
