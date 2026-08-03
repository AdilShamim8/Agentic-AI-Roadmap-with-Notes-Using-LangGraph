import tempfile
import unittest
from pathlib import Path

from research_agent.llm import FakeLLM
from research_agent.tools.documents import load_local_documents
from research_agent.tools.fetch import extract_main_text
from research_agent.tools.web_search import FakeSearch
from research_agent.state import SearchResult


class TestFakeLLM(unittest.TestCase):
    def test_records_calls_and_returns_responder_output(self):
        llm = FakeLLM(lambda prompt, system: f"echo:{prompt}")
        result = llm.generate("hello", system="sys")
        self.assertEqual(result, "echo:hello")
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(llm.calls[0]["system"], "sys")

    def test_default_responder_returns_empty_string(self):
        llm = FakeLLM()
        self.assertEqual(llm.generate("anything"), "")


class TestFakeSearch(unittest.TestCase):
    def test_records_calls_and_returns_responder_output(self):
        def responder(query, max_results):
            return [SearchResult(title="T", url="https://x.com", snippet="s")][:max_results]

        tool = FakeSearch(responder)
        results = tool.search("query", max_results=2)
        self.assertEqual(len(results), 1)
        self.assertEqual(tool.calls[0]["query"], "query")


class TestLoadLocalDocuments(unittest.TestCase):
    def test_loads_txt_and_md_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            txt_path = Path(tmp) / "notes.txt"
            txt_path.write_text("Some important research notes.", encoding="utf-8")
            md_path = Path(tmp) / "readme.md"
            md_path.write_text("# Heading\n\nSome markdown content.", encoding="utf-8")

            results = load_local_documents([str(txt_path), str(md_path)])

            self.assertEqual(len(results), 2)
            names = {r.title for r in results}
            self.assertEqual(names, {"notes.txt", "readme.md"})
            for r in results:
                self.assertEqual(r.source_type, "local_document")
                self.assertTrue(r.url.startswith("file://"))

    def test_missing_file_is_skipped_not_raised(self):
        results = load_local_documents(["/this/path/does/not/exist.txt"])
        self.assertEqual(results, [])

    def test_empty_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty_path = Path(tmp) / "empty.txt"
            empty_path.write_text("   \n  ", encoding="utf-8")
            results = load_local_documents([str(empty_path)])
            self.assertEqual(results, [])


class TestExtractMainText(unittest.TestCase):
    def test_strips_scripts_and_nav(self):
        html = """
        <html><body>
            <nav>Home | About</nav>
            <script>trackUser();</script>
            <article><p>This is the real content.</p></article>
            <footer>Copyright 2026</footer>
        </body></html>
        """
        text = extract_main_text(html)
        self.assertIn("This is the real content.", text)
        self.assertNotIn("trackUser", text)
        self.assertNotIn("Home | About", text)
        self.assertNotIn("Copyright", text)

    def test_falls_back_to_body_without_article_tag(self):
        html = "<html><body><p>Just a plain page.</p></body></html>"
        text = extract_main_text(html)
        self.assertIn("Just a plain page.", text)


if __name__ == "__main__":
    unittest.main()
