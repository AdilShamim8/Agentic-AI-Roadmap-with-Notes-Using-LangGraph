"""Unit tests for filesystem helpers (traceback file extraction)."""

from __future__ import annotations

from pathlib import Path

from self_heal.tools.fs import extract_file_lines_from_traceback, read_relevant_files


def test_extract_file_lines_basic() -> None:
    tb = """
Traceback (most recent call last):
  File "tests/test_calc.py", line 5, in test_add
    assert add(2, 3) == 5
  File "src/calc.py", line 2, in add
    return a - b
AssertionError
"""
    pairs = extract_file_lines_from_traceback(tb)
    paths = [p for p, _ in pairs]
    assert "tests/test_calc.py" in paths
    assert "src/calc.py" in paths


def test_read_relevant_files_skips_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "calc.py").write_text("def add(a,b): return a+b\n")
    tb = 'File "src/calc.py", line 2'
    files = read_relevant_files(repo, tb)
    assert "src/calc.py" in files
    assert "def add" in files["src/calc.py"]


def test_read_relevant_files_truncates_huge(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    big = repo / "big.py"
    big.write_text("x = 0\n" * 20_000)
    files = read_relevant_files(repo, 'File "big.py", line 1')
    assert "truncated" in files["big.py"]
