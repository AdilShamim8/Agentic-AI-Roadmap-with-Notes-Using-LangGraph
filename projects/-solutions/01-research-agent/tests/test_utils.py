import unittest

from research_agent.utils import (
    chunk_text,
    dedupe_preserve_order,
    normalize_url,
    safe_json_parse,
    slugify,
    truncate,
)


class TestSafeJsonParse(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(safe_json_parse('["a", "b"]'), ["a", "b"])

    def test_json_in_fence(self):
        text = '```json\n["a", "b"]\n```'
        self.assertEqual(safe_json_parse(text), ["a", "b"])

    def test_json_with_preamble(self):
        text = 'Sure! Here you go:\n["a", "b", "c"]\nHope that helps.'
        self.assertEqual(safe_json_parse(text), ["a", "b", "c"])

    def test_object_with_preamble(self):
        text = 'Here is the object: {"sufficient": true, "gaps": ""} thanks'
        self.assertEqual(safe_json_parse(text), {"sufficient": True, "gaps": ""})

    def test_unparsable_returns_none(self):
        self.assertIsNone(safe_json_parse("not json at all, sorry"))


class TestChunkText(unittest.TestCase):
    def test_short_text_single_chunk(self):
        self.assertEqual(chunk_text("hello world", max_chars=100), ["hello world"])

    def test_empty_text(self):
        self.assertEqual(chunk_text(""), [])

    def test_long_text_multiple_chunks(self):
        text = ("word " * 2000).strip()
        chunks = chunk_text(text, max_chars=500, overlap=50)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(c), 500)
        # reconstructed text should still contain the first and last words
        self.assertTrue(chunks[0].startswith("word"))

    def test_no_infinite_loop_on_no_whitespace(self):
        text = "a" * 5000
        chunks = chunk_text(text, max_chars=500, overlap=50)
        self.assertGreater(len(chunks), 1)


class TestTruncate(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(truncate("hello", max_chars=100), "hello")

    def test_long_text_truncated(self):
        result = truncate("a" * 100, max_chars=10)
        self.assertTrue(result.endswith("…"))
        self.assertLessEqual(len(result), 12)


class TestNormalizeUrl(unittest.TestCase):
    def test_strips_fragment(self):
        self.assertEqual(normalize_url("https://x.com/a#section"), "https://x.com/a")

    def test_strips_utm_params(self):
        self.assertEqual(
            normalize_url("https://x.com/a?utm_source=twitter&id=5"),
            "https://x.com/a?id=5",
        )

    def test_case_insensitive_and_trailing_slash(self):
        self.assertEqual(normalize_url("HTTPS://X.com/a/"), "https://x.com/a")


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_empty_falls_back(self):
        self.assertEqual(slugify("!!!"), "untitled")


class TestDedupe(unittest.TestCase):
    def test_dedupe_case_insensitive(self):
        result = dedupe_preserve_order(["Foo", "foo", "Bar", "  bar  ", "Baz"])
        self.assertEqual(result, ["Foo", "Bar", "Baz"])


if __name__ == "__main__":
    unittest.main()
