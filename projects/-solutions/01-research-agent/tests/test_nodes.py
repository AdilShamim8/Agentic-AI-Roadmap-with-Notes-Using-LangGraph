import unittest

from research_agent.llm import FakeLLM
from research_agent.nodes import (
    compile_report_node,
    critique_node,
    load_documents_node,
    plan_node,
    route_after_critique,
    search_node,
    synthesize_node,
)
from research_agent.state import SearchResult, new_state
from research_agent.tools.web_search import FakeSearch


def planner_llm(questions):
    import json

    return FakeLLM(lambda prompt, system: json.dumps(questions))


class TestPlanNode(unittest.TestCase):
    def test_first_round_parses_llm_questions(self):
        state = new_state("Solar energy")
        llm = planner_llm(["Q1?", "Q2?"])
        plan_node(state, llm)
        self.assertEqual(state["sub_questions"], ["Q1?", "Q2?"])
        self.assertEqual(state["iteration"], 0)

    def test_falls_back_to_topic_on_bad_llm_output(self):
        state = new_state("Solar energy")
        llm = FakeLLM(lambda prompt, system: "not valid json")
        plan_node(state, llm)
        self.assertEqual(state["sub_questions"], ["Solar energy"])

    def test_follow_up_round_uses_follow_up_questions_and_increments_iteration(self):
        state = new_state("Solar energy")
        state["follow_up_questions"] = ["Follow up Q?"]
        llm = FakeLLM(lambda prompt, system: "SHOULD NOT BE CALLED")
        plan_node(state, llm)
        self.assertEqual(state["sub_questions"], ["Follow up Q?"])
        self.assertEqual(state["iteration"], 1)
        self.assertEqual(state["follow_up_questions"], [])


class TestSearchNode(unittest.TestCase):
    def test_searches_each_sub_question(self):
        state = new_state("Topic")
        state["sub_questions"] = ["Q1?", "Q2?"]

        def responder(query, max_results):
            return [SearchResult(title=f"Result for {query}", url=f"https://x.com/{query}", snippet="s")]

        tool = FakeSearch(responder)
        search_node(state, tool)

        self.assertEqual(set(state["search_results"].keys()), {"Q1?", "Q2?"})
        self.assertEqual(len(tool.calls), 2)

    def test_skips_already_searched_question(self):
        state = new_state("Topic")
        state["sub_questions"] = ["Q1?"]
        state["search_results"] = {"Q1?": []}
        tool = FakeSearch(lambda q, m: [SearchResult(title="new", url="https://x.com", snippet="s")])
        search_node(state, tool)
        self.assertEqual(tool.calls, [])  # never called, already had a result

    def test_search_exception_does_not_crash(self):
        state = new_state("Topic")
        state["sub_questions"] = ["Q1?"]

        class BrokenSearch:
            def search(self, query, max_results=4):
                raise RuntimeError("network down")

        search_node(state, BrokenSearch())
        self.assertEqual(state["search_results"]["Q1?"], [])


class TestSynthesizeNode(unittest.TestCase):
    def test_produces_finding_per_sub_question(self):
        state = new_state("Topic")
        state["sub_questions"] = ["Q1?"]
        state["search_results"] = {
            "Q1?": [SearchResult(title="Source", url="https://x.com", snippet="the answer is 42")]
        }
        llm = FakeLLM(lambda prompt, system: "The answer is 42 [1].")

        synthesize_node(state, llm)

        self.assertIn("Q1?", state["findings"])
        self.assertEqual(state["findings"]["Q1?"].answer, "The answer is 42 [1].")
        self.assertEqual(state["findings"]["Q1?"].citation_ids, [1])
        self.assertEqual(len(state["sources"]), 1)

    def test_includes_local_documents_alongside_web_results(self):
        state = new_state("Topic")
        state["sub_questions"] = ["Q1?"]
        state["search_results"] = {"Q1?": []}
        state["local_documents"] = [
            SearchResult(title="notes.txt", url="file:///tmp/notes.txt", snippet="local info", source_type="local_document")
        ]
        seen_prompts = []
        llm = FakeLLM(lambda prompt, system: seen_prompts.append(prompt) or "Answer [1].")

        synthesize_node(state, llm)

        self.assertIn("notes.txt", seen_prompts[0])


class TestCritiqueNode(unittest.TestCase):
    def test_sufficient_stops_the_loop(self):
        state = new_state("Topic")
        llm = FakeLLM(lambda prompt, system: '{"sufficient": true, "gaps": ""}')
        critique_node(state, llm)
        self.assertTrue(state["is_sufficient"])
        self.assertEqual(state["follow_up_questions"], [])

    def test_insufficient_generates_follow_up_questions(self):
        state = new_state("Topic")
        calls = {"n": 0}

        def responder(prompt, system):
            calls["n"] += 1
            if calls["n"] == 1:
                return '{"sufficient": false, "gaps": "missing recent data"}'
            return '["What happened most recently?"]'

        llm = FakeLLM(responder)
        critique_node(state, llm)

        self.assertFalse(state["is_sufficient"])
        self.assertEqual(state["follow_up_questions"], ["What happened most recently?"])

    def test_malformed_critique_response_defaults_to_sufficient(self):
        state = new_state("Topic")
        llm = FakeLLM(lambda prompt, system: "garbage response")
        critique_node(state, llm)
        self.assertTrue(state["is_sufficient"])


class TestRouteAfterCritique(unittest.TestCase):
    def test_sufficient_routes_to_finish(self):
        state = new_state("Topic")
        state["is_sufficient"] = True
        self.assertEqual(route_after_critique(state), "finish")

    def test_insufficient_with_no_follow_ups_routes_to_finish(self):
        state = new_state("Topic")
        state["is_sufficient"] = False
        state["follow_up_questions"] = []
        self.assertEqual(route_after_critique(state), "finish")

    def test_insufficient_under_iteration_cap_routes_to_continue(self):
        state = new_state("Topic", max_iterations=3)
        state["is_sufficient"] = False
        state["follow_up_questions"] = ["more?"]
        state["iteration"] = 0
        self.assertEqual(route_after_critique(state), "continue")

    def test_insufficient_at_iteration_cap_routes_to_finish(self):
        state = new_state("Topic", max_iterations=2)
        state["is_sufficient"] = False
        state["follow_up_questions"] = ["more?"]
        state["iteration"] = 1  # + 1 == max_iterations
        self.assertEqual(route_after_critique(state), "finish")

    def test_route_after_critique_does_not_mutate_state(self):
        state = new_state("Topic", max_iterations=3)
        state["is_sufficient"] = False
        state["follow_up_questions"] = ["more?"]
        state["iteration"] = 0
        before = dict(state)
        route_after_critique(state)
        self.assertEqual(state["iteration"], before["iteration"])


class TestLoadDocumentsNode(unittest.TestCase):
    def test_no_paths_gives_empty_list(self):
        state = new_state("Topic")
        load_documents_node(state)
        self.assertEqual(state["local_documents"], [])


class TestCompileReportNode(unittest.TestCase):
    def test_uses_llm_generated_title_when_available(self):
        state = new_state("Topic")
        state["findings"] = {}
        llm = FakeLLM(lambda prompt, system: "A Custom Title")
        compile_report_node(state, llm)
        self.assertIn("# A Custom Title", state["report"])

    def test_falls_back_to_default_title_without_llm(self):
        state = new_state("Topic")
        compile_report_node(state, llm=None)
        self.assertIn("# Research Report: Topic", state["report"])

    def test_title_generation_failure_falls_back_gracefully(self):
        state = new_state("Topic")

        class BrokenLLM:
            def generate(self, prompt, system=None):
                raise RuntimeError("boom")

        compile_report_node(state, BrokenLLM())
        self.assertIn("# Research Report: Topic", state["report"])


if __name__ == "__main__":
    unittest.main()
