"""Tiny TF-IDF embedding for tool-description retrieval.

We deliberately avoid an external embedding API here:

1. Tool descriptions are short (1-3 sentences). TF-IDF over a 100-doc corpus
   is more than enough to discriminate them.
2. The project must run end-to-end without any API key. Depending on
   OpenAI ada-002 would break that property.
3. The retrieval index must rebuild every time the registry changes, so it
   has to be fast. TF-IDF with cosine similarity is sub-millisecond for
   ~50 tools.

If you want to swap in real embeddings (e.g. ``text-embedding-3-small``),
replace :func:`embed` and :func:`embed_query` with API calls. The rest of
the retrieval pipeline (cosine similarity, top-k) stays the same.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


class TfIdfIndex:
    """A minimal TF-IDF index with cosine-similarity top-k retrieval.

    Build once with :meth:`fit`, then call :meth:`top_k` to retrieve the most
    similar document indices for a query.
    """

    def __init__(self) -> None:
        self._docs: List[List[str]] = []
        self._idf: Dict[str, float] = {}
        self._vectors: List[Dict[str, float]] = []
        self._norms: List[float] = []

    def fit(self, documents: List[str]) -> "TfIdfIndex":
        """Build the index from a list of plain-text documents."""
        self._docs = [_tokenize(d) for d in documents]
        n = len(self._docs)
        # Document frequency
        df: Counter[str] = Counter()
        for toks in self._docs:
            df.update(set(toks))
        # Inverse document frequency (smoothed)
        self._idf = {
            term: math.log((1 + n) / (1 + count)) + 1.0
            for term, count in df.items()
        }
        # TF-IDF vectors
        self._vectors = []
        self._norms = []
        for toks in self._docs:
            tf = Counter(toks)
            vec = {term: count * self._idf.get(term, 0.0)
                   for term, count in tf.items()}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self._vectors.append(vec)
            self._norms.append(norm)
        return self

    def embed_query(self, query: str) -> Dict[str, float]:
        """Return the TF-IDF vector for ``query`` (NOT normalised)."""
        tf = Counter(_tokenize(query))
        return {term: count * self._idf.get(term, 0.0)
                for term, count in tf.items()}

    def top_k(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """Return the top-``k`` (index, score) pairs for ``query``.

        Scores are cosine similarities in ``[0, 1]``. Higher is better.
        """
        if not self._vectors:
            return []
        qv = self.embed_query(query)
        qnorm = math.sqrt(sum(v * v for v in qv.values())) or 1.0
        scores: List[Tuple[int, float]] = []
        for i, dv in enumerate(self._vectors):
            # Sparse dot-product.
            small, large = (qv, dv) if len(qv) < len(dv) else (dv, qv)
            dot = sum(v * large.get(term, 0.0) for term, v in small.items())
            sim = dot / (qnorm * self._norms[i])
            scores.append((i, sim))
        scores.sort(key=lambda x: -x[1])
        return scores[:k]

    # Numpy-backed variant – kept for users who want batched retrieval.
    def top_k_numpy(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        if not self._vectors:
            return []
        vocab = list(self._idf.keys())
        idx = {t: i for i, t in enumerate(vocab)}
        mat = np.zeros((len(self._vectors), len(vocab)), dtype=np.float32)
        for i, dv in enumerate(self._vectors):
            for term, val in dv.items():
                mat[i, idx[term]] = val
        qv = np.zeros(len(vocab), dtype=np.float32)
        for term, val in self.embed_query(query).items():
            qv[idx[term]] = val
        sims = (mat @ qv) / (
            np.linalg.norm(mat, axis=1) * np.linalg.norm(qv) + 1e-9
        )
        order = np.argsort(-sims)[:k]
        return [(int(i), float(sims[i])) for i in order]
