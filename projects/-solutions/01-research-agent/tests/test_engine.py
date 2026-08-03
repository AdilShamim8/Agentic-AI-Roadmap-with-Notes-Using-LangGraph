import json
import unittest

from research_agent.engine import run_research
from research_agent.llm import FakeLLM
from research_agent.state import SearchResult
from research_agent.tools.web_search import FakeSearch


class TestRunResearchSingleRound(unittest.TestCase):
    """A critique that immediately says "sufficient" should produce a
    complete report in a single iteration."""

    def setUp(self):
        def llm_responder(prompt, system):
            if "Break this into exactly" in prompt:
                return json.dumps(["What is X?", "Why does X matter?"])
            if "Decide whether these findings" in prompt:
                return '{"sufficient": true, "gaps": ""}'
            if prompt.startswith("Write a concise"):
                return "X: A Complete Overview"
            # synthesis prompt
            return "X is a thing that matters a lot [1]."

        def search_responder(query, max_results):
            return [SearchResult(title=f"About {query}", url=f"https://example.com/{hash(query)}", snippet="info")]

        self.llm = FakeLLM(llm_responder)
        self.search_tool = FakeSearch(search_responder)

    def test_produces_report_with_expected_sections(self):
        steps = []
        state = run_research(
            topic="X",
            llm=self.llm,
            search_tool=self.search_tool,
            max_results_per_query=3,
            max_iterations=2,
            on_step=lambda name, s: steps.append(name),
        )

        self.assertIn("# X: A Complete Overview", state["report"])
        self.assertIn("What is X?", state["report"])
        self.assertIn("Why does X matter?", state["report"])
        self.assertIn("## References", state["report"])
        self.assertEqual(state["iteration"], 0)
        self.assertEqual(len(state["sources"]), 2)
        # exactly one pass through the loop body before compiling
        self.assertEqual(steps.count("plan"), 1)
        self.assertEqual(steps[-1], "compile_report")


class TestRunResearchMultiRound(unittest.TestCase):
    """A critique that says "insufficient" once should trigger exactly
    one extra research round, then stop."""

    def setUp(self):
        self.critique_calls = {"n": 0}

        def llm_responder(prompt, system):
            if "Break this into exactly" in prompt:
                return json.dumps(["Initial question?"])
            if "Write exactly" in prompt and "follow-up" in prompt:
                return json.dumps(["Follow-up question?"])
            if "Decide whether these findings" in prompt:
                self.critique_calls["n"] += 1
                if self.critique_calls["n"] == 1:
                    return '{"sufficient": false, "gaps": "missing recent developments"}'
                return '{"sufficient": true, "gaps": ""}'
            if prompt.startswith("Write a concise"):
                return "Multi-Round Report"
            return "Some synthesized answer [1]."

        def search_responder(query, max_results):
            return [SearchResult(title=query, url=f"https://example.com/{query}", snippet="info")]

        self.llm = FakeLLM(llm_responder)
        self.search_tool = FakeSearch(search_responder)

    def test_runs_two_rounds_then_stops(self):
        steps = []
        state = run_research(
            topic="Y",
            llm=self.llm,
            search_tool=self.search_tool,
            max_iterations=3,
            on_step=lambda name, s: steps.append(name),
        )

        self.assertIn("Initial question?", state["report"])
        self.assertIn("Follow-up question?", state["report"])
        self.assertEqual(state["iteration"], 1)
        self.assertEqual(steps.count("plan"), 2)
        self.assertEqual(self.critique_calls["n"], 2)

    def test_respects_hard_iteration_cap_even_if_never_sufficient(self):
        def always_insufficient(prompt, system):
            if "Break this into exactly" in prompt:
                return json.dumps(["Q0?"])
            if "Write exactly" in prompt and "follow-up" in prompt:
                return json.dumps(["Another follow-up?"])
            if "Decide whether these findings" in prompt:
                return '{"sufficient": false, "gaps": "always more to learn"}'
            return "answer [1]."

        llm = FakeLLM(always_insufficient)
        steps = []
        state = run_research(
            topic="Z",
            llm=llm,
            search_tool=self.search_tool,
            max_iterations=2,
            on_step=lambda name, s: steps.append(name),
        )
        # must terminate (no infinite loop) and still produce a report
        self.assertIn("report", state)
        self.assertTrue(state["report"])
        self.assertEqual(steps.count("plan"), 2)  # capped at max_iterations


class TestRunResearchWithLocalDocuments(unittest.TestCase):
    def test_local_documents_flow_into_findings(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            doc_path = Path(tmp) / "internal.txt"
            doc_path.write_text("Confidential internal figures about X.", encoding="utf-8")

            def llm_responder(prompt, system):
                if "Break this into exactly" in prompt:
                    return json.dumps(["What are the internal figures?"])
                if "Decide whether these findings" in prompt:
                    return '{"sufficient": true, "gaps": ""}'
                if prompt.startswith("Write a concise"):
                    return "Internal Report"
                return "Referenced local doc content [1]."

            llm = FakeLLM(llm_responder)
            search_tool = FakeSearch(lambda q, m: [])

            state = run_research(
                topic="X internal figures",
                llm=llm,
                search_tool=search_tool,
                local_document_paths=[str(doc_path)],
                max_iterations=1,
            )

            self.assertEqual(len(state["local_documents"]), 1)
            self.assertIn("internal.txt", [s.title for s in state["sources"]])


if __name__ == "__main__":
    unittest.main()
