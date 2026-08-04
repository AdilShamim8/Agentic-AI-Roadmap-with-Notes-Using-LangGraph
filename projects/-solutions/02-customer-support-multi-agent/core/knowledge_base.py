"""
Lightweight retrieval-augmented-generation (RAG) search over the local
knowledge base, using TF-IDF + cosine similarity (scikit-learn) instead of
an embeddings API. This keeps the whole project runnable offline with no
API key and no vector-DB service, while still demonstrating the RAG pattern
that a production version would swap in (e.g. Chroma/FAISS + OpenAI or
Voyage embeddings).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"


@dataclass
class KBHit:
    title: str
    content: str
    score: float


class KnowledgeBase:
    """Loads every .md file in the knowledge base directory and indexes it with TF-IDF."""

    def __init__(self, kb_dir: Path = KB_DIR):
        self.kb_dir = kb_dir
        self._titles: list[str] = []
        self._contents: list[str] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._load()

    def _load(self) -> None:
        paths = sorted(self.kb_dir.glob("*.md"))
        if not paths:
            raise FileNotFoundError(f"No knowledge base articles found in {self.kb_dir}")

        for path in paths:
            text = path.read_text(encoding="utf-8")
            title = text.splitlines()[0].lstrip("# ").strip() if text else path.stem
            self._titles.append(title)
            self._contents.append(text)

        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(self._contents)

    def search(self, query: str, k: int = 2, min_score: float = 0.05) -> list[KBHit]:
        """Return the top-k most relevant articles for `query`, above `min_score` similarity."""
        if not query.strip():
            return []
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        hits: list[KBHit] = []
        for i in ranked[:k]:
            if scores[i] < min_score:
                continue
            hits.append(KBHit(title=self._titles[i], content=self._contents[i], score=float(scores[i])))
        return hits


_kb_singleton: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb_singleton
    if _kb_singleton is None:
        _kb_singleton = KnowledgeBase()
    return _kb_singleton


def search_kb(query: str, k: int = 2) -> list[KBHit]:
    """Module-level convenience wrapper around the singleton KnowledgeBase."""
    return get_kb().search(query, k=k)
