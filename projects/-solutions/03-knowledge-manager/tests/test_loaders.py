"""Tests for the loaders (no OpenAI needed)."""
from __future__ import annotations

from pathlib import Path

from knowledge_manager.ingestion.loader import iter_supported, load


def test_load_markdown(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("# My Title\n\nFirst paragraph.\n\nSecond paragraph.\n")
    doc = load(p)
    assert doc.kind == "md"
    assert doc.title == "My Title"
    assert "First paragraph" in doc.text
    assert doc.content_hash  # non-empty


def test_load_html(tmp_path: Path) -> None:
    p = tmp_path / "x.html"
    p.write_text(
        "<html><head><title>HTML Title</title></head>"
        "<body><h1>HTML H1</h1><p>Hello.</p></body></html>"
    )
    doc = load(p)
    assert doc.kind == "html"
    # title can come from <title> or <h1>; both contain "HTML"
    assert "HTML" in doc.title
    assert "Hello" in doc.text


def test_load_text(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("plain text content")
    doc = load(p)
    assert doc.kind == "txt"
    assert doc.text == "plain text content"


def test_load_pdf(tmp_path: Path) -> None:
    pytest = __import__("pytest")
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.platypus import Paragraph, SimpleDocTemplate
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        pytest.skip("reportlab not installed")

    p = tmp_path / "x.pdf"
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(p), pagesize=LETTER)
    doc.build([Paragraph("Hello PDF world.", styles["BodyText"])])

    loaded = load(p)
    assert loaded.kind == "pdf"
    assert "Hello" in loaded.text


def test_iter_supported(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("a")
    (tmp_path / "b.html").write_text("<p>b</p>")
    (tmp_path / "c.txt").write_text("c")
    (tmp_path / "d.json").write_text("{}")  # unsupported
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "e.md").write_text("e")

    files = iter_supported(tmp_path)
    names = sorted(p.name for p in files)
    assert names == ["a.md", "b.html", "c.txt", "e.md"]


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text("{}")
    pytest = __import__("pytest")
    with pytest.raises(ValueError):
        load(p)
