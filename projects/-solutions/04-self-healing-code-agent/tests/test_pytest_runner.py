"""Unit tests for the pytest runner."""

from __future__ import annotations

from pathlib import Path

from self_heal.tools.pytest_runner import run_pytest


def _write_repo(tmp_path: Path, *, buggy: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "r"\nversion = "0"\nrequires-python = ">=3.10"\n'
        '[tool.pytest.ini_options]\npythonpath = ["src"]\n'
    )
    if buggy:
        (repo / "src" / "calc.py").write_text("def add(a, b):\n    return a - b  # bug\n")
    else:
        (repo / "src" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (repo / "tests" / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )
    return repo


def test_run_pytest_detects_failure(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path, buggy=True)
    result = run_pytest(repo, "tests/test_calc.py::test_add")
    assert result.exit_code != 0
    assert result.failed >= 1
    assert result.target_failed
    assert not result.target_passed
    assert len(result.failures) >= 1
    assert (
        "assert" in result.failures[0].traceback or "AssertionError" in result.failures[0].traceback
    )


def test_run_pytest_detects_pass(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path, buggy=False)
    result = run_pytest(repo, "tests/test_calc.py::test_add")
    assert result.exit_code == 0
    assert result.target_passed
    assert not result.target_failed


def test_run_pytest_full_suite(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path, buggy=False)
    result = run_pytest(repo, None)
    assert result.exit_code == 0
    assert result.passed >= 1


def test_run_pytest_on_fixture(copy_fixture) -> None:
    case = copy_fixture("case_01_off_by_one")
    result = run_pytest(case, "tests/test_calc.py::test_sum_range_basic")
    assert result.target_failed
    assert result.failed >= 1
