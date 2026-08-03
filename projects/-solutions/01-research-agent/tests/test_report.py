import unittest

from research_agent.report import build_numbered_excerpts, compile_markdown_report, register_source
from research_agent.state import Finding, SearchResult, new_state


class TestRegisterSource(unittest.TestCase):
    def test_new_source_gets_incrementing_ids(self):
        state = new_state("topic")
        id1 = register_source(state, "Title A", "https://a.com")
        id2 = register_source(state, "Title B", "https://b.com")
        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)
        self.assertEqual(len(state["sources"]), 2)

    def test_duplicate_url_reuses_id(self):
        state = new_state("topic")
        id1 = register_source(state, "Title A", "https://a.com/page")
        id2 = register_source(state, "Title A again", "https://a.com/page/")
        self.assertEqual(id1, id2)
        self.assertEqual(len(state["sources"]), 1)

    def test_duplicate_url_with_tracking_params_reuses_id(self):
        state = new_state("topic")
        id1 = register_source(state, "A", "https://a.com/page")
        id2 = register_source(state, "A", "https://a.com/page?utm_source=x")
        self.assertEqual(id1, id2)


class TestBuildNumberedExcerpts(unittest.TestCase):
    def test_excerpts_reference_registered_ids(self):
        state = new_state("topic")
        results = [
            SearchResult(title="First", url="https://a.com", snippet="snippet a"),
            SearchResult(title="Second", url="https://b.com", snippet="snippet b"),
        ]
        excerpts = build_numbered_excerpts(state, results)
        self.assertEqual(len(excerpts), 2)
        self.assertTrue(excerpts[0].startswith("[1] First"))
        self.assertTrue(excerpts[1].startswith("[2] Second"))

    def test_prefers_content_over_snippet(self):
        state = new_state("topic")
        result = SearchResult(title="X", url="https://x.com", snippet="short", content="long content body")
        excerpts = build_numbered_excerpts(state, [result])
        self.assertIn("long content body", excerpts[0])


class TestCompileMarkdownReport(unittest.TestCase):
    def test_report_contains_title_findings_and_references(self):
        state = new_state("Solar energy")
        state["sources"] = []
        state["findings"] = {
            "What is solar energy?": Finding(
                question="What is solar energy?",
                answer="Solar energy is energy from the sun [1].",
                citation_ids=[1],
            )
        }
        register_source(state, "Solar Basics", "https://example.com/solar")

        report = compile_markdown_report(state, title="Solar Energy Overview")

        self.assertIn("# Solar Energy Overview", report)
        self.assertIn("What is solar energy?", report)
        self.assertIn("Solar energy is energy from the sun [1].", report)
        self.assertIn("## References", report)
        self.assertIn("[Solar Basics](https://example.com/solar)", report)

    def test_report_handles_no_sources(self):
        state = new_state("Empty topic")
        report = compile_markdown_report(state)
        self.assertIn("No sources were collected", report)

    def test_local_document_reference_formatted_without_link(self):
        state = new_state("Topic")
        register_source(state, "notes.txt", "file:///tmp/notes.txt", source_type="local_document")
        report = compile_markdown_report(state)
        self.assertIn("notes.txt *(local document)*", report)


if __name__ == "__main__":
    unittest.main()
