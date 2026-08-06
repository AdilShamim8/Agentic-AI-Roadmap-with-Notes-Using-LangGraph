"""Unit tests for the unified-diff parser and applier."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from self_heal.patches.diff import DiffError, apply_diff, extract_diff, parse_diff


# ── extraction ───────────────────────────────────────────────
def test_extract_diff_from_fence() -> None:
    text = "Here is the patch:\n```diff\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n```\nDone."
    out = extract_diff(text)
    assert out.startswith("--- a/x.py")
    assert out.endswith("+b")


def test_extract_diff_no_fence_returns_as_is() -> None:
    text = "--- a/x.py\n+++ b/x.py\n"
    assert extract_diff(text) == text.strip()


# ── parsing ──────────────────────────────────────────────────
def test_parse_single_file_single_hunk() -> None:
    diff = """\
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,3 @@
 line1
-old
+new
 line3
"""
    patches = parse_diff(diff)
    assert len(patches) == 1
    p = patches[0]
    assert p.old_path == "foo.py"
    assert p.new_path == "foo.py"
    assert len(p.hunks) == 1
    h = p.hunks[0]
    assert h.old_start == 1
    assert h.old_count == 3
    assert h.new_start == 1
    assert h.new_count == 3
    assert h.lines == [" line1", "-old", "+new", " line3"]


def test_parse_multi_file() -> None:
    diff = """\
--- a/a.py
+++ b/a.py
@@ -1,3 +1,3 @@
 x
-y
+z1
 x
--- a/b.py
+++ b/b.py
@@ -1,3 +1,3 @@
 x
-y
+z2
 x
"""
    patches = parse_diff(diff)
    assert len(patches) == 2
    assert {p.old_path for p in patches} == {"a.py", "b.py"}


def test_parse_strips_a_b_prefix() -> None:
    diff = """\
--- a/src/pkg/mod.py
+++ b/src/pkg/mod.py
@@ -1,1 +1,1 @@
-a
+b
"""
    p = parse_diff(diff)[0]
    assert p.old_path == "src/pkg/mod.py"


def test_parse_new_file() -> None:
    diff = """\
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+def hello():
+    return "hi"
"""
    p = parse_diff(diff)[0]
    assert p.is_new_file
    assert not p.is_deleted


def test_parse_malformed_raises() -> None:
    with pytest.raises(DiffError):
        parse_diff("not a diff at all")


# ── application ──────────────────────────────────────────────
def test_apply_single_line_change(tmp_repo: Path) -> None:
    f = tmp_repo / "foo.py"
    f.write_text("a\nb\nc\n")
    diff = """\
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,3 @@
 a
-b
+B
 c
"""
    apply_diff(tmp_repo, diff)
    assert f.read_text() == "a\nB\nc\n"


def test_apply_multi_file_atomic(tmp_repo: Path) -> None:
    a = tmp_repo / "a.py"
    b = tmp_repo / "b.py"
    a.write_text("x\ny\nx\n")
    b.write_text("x\ny\nx\n")
    diff = """\
--- a/a.py
+++ b/a.py
@@ -1,3 +1,3 @@
 x
-y
+Z1
 x
--- a/b.py
+++ b/b.py
@@ -1,3 +1,3 @@
 x
-y
+Z2
 x
"""
    apply_diff(tmp_repo, diff)
    assert a.read_text() == "x\nZ1\nx\n"
    assert b.read_text() == "x\nZ2\nx\n"


def test_apply_new_file(tmp_repo: Path) -> None:
    target = tmp_repo / "new.py"
    diff = """\
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+def hello():
+    return "hi"
"""
    apply_diff(tmp_repo, diff)
    assert target.exists()
    assert "def hello" in target.read_text()


def test_apply_fuzzy_match_when_line_drift(tmp_repo: Path) -> None:
    f = tmp_repo / "foo.py"
    f.write_text("header\n\na\nb\nc\n")
    # Hunk claims old_start=3 but the actual context starts at line 4.
    diff = """\
--- a/foo.py
+++ b/foo.py
@@ -3,3 +3,3 @@
 a
-b
+B
 c
"""
    apply_diff(tmp_repo, diff)
    assert f.read_text() == "header\n\na\nB\nc\n"


def test_apply_failure_raises(tmp_repo: Path) -> None:
    f = tmp_repo / "foo.py"
    f.write_text("a\nb\nc\n")
    diff = """\
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,3 @@
 NOT_THERE
-b
+B
 c
"""
    with pytest.raises(DiffError):
        apply_diff(tmp_repo, diff)


def test_apply_dry_run_does_not_write(tmp_repo: Path) -> None:
    f = tmp_repo / "foo.py"
    f.write_text("a\nb\nc\n")
    diff = """\
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,3 @@
 a
-b
+B
 c
"""
    apply_diff(tmp_repo, diff, dry_run=True)
    assert f.read_text() == "a\nb\nc\n"


# ── end-to-end on the bundled expected patches ───────────────
def test_expected_patch_case_01_applies(fixtures_dir: Path, tmp_path: Path) -> None:
    case = tmp_path / "case"
    shutil.copytree(fixtures_dir / "case_01_off_by_one", case)
    diff = (case / "expected_patch.diff").read_text()
    touched = apply_diff(case, diff)
    assert any(p.name == "calc.py" for p in touched)
    content = (case / "src" / "calc.py").read_text()
    assert "range(start, end + 1)" in content


def test_expected_patch_case_03_applies(fixtures_dir: Path, tmp_path: Path) -> None:
    import shutil

    case = tmp_path / "case"
    shutil.copytree(fixtures_dir / "case_03_multifile", case)
    diff = (case / "expected_patch.diff").read_text()
    apply_diff(case, diff)
    content = (case / "src" / "mathlib" / "stats.py").read_text()
    assert "rank - 1" in content
