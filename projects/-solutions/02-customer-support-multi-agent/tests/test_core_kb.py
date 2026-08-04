from core.knowledge_base import KnowledgeBase


def test_search_returns_relevant_article_for_refund():
    kb = KnowledgeBase()
    hits = kb.search("how long does a refund take", k=1)
    assert len(hits) == 1
    assert hits[0].title.lower() in ("returns & refunds", "billing & payments")


def test_search_returns_relevant_article_for_login():
    kb = KnowledgeBase()
    hits = kb.search("I can't log in, getting a 500 error", k=1)
    assert len(hits) == 1
    assert "troubleshoot" in hits[0].title.lower()


def test_search_empty_query_returns_nothing():
    kb = KnowledgeBase()
    assert kb.search("") == []


def test_search_irrelevant_query_returns_nothing_above_threshold():
    kb = KnowledgeBase()
    hits = kb.search("purple giraffe astronomy", k=2)
    assert hits == []
