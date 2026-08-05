"""Ingest the sample dataset using FAKE embeddings (no OpenAI key needed).

Used by the eval harness `--stub` mode and by the smoke test. Real ingestion
uses `knowledge_manager.ingestion.pipeline.ingest_directory`, which calls
OpenAI's embedding API. This script monkey-patches the embedder so it can
run end-to-end without an API key.

Usage:  python scripts/ingest_stub.py [eval/data/documents]
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from knowledge_manager.ingestion import pipeline
from knowledge_manager.llm import get_embeddings
from knowledge_manager.storage.db import wipe


def _fake_embed(texts: list[str]) -> list[list[float]]:
    out = []
    for t in texts:
        h = hashlib.sha256(t.encode()).digest()
        vec = []
        while len(vec) < 1536:
            for b in h:
                vec.append((b - 128) / 128.0)
            h = hashlib.sha256(h).digest()
        out.append(vec[:1536])
    return out


def main(target: str = "eval/data/documents") -> int:
    target_path = Path(target)
    if not target_path.exists():
        print(f"Path not found: {target_path}")
        return 2

    # Wipe DB first so we start clean.
    wipe()
    print(f"Wiped DB. Ingesting {target_path} ...")

    # Monkey-patch the embedder.
    import knowledge_manager.ingestion.pipeline as pl

    orig_embed = pl.embed_texts
    pl.embed_texts = _fake_embed
    # Also patch the llm module's embed_texts since pipeline imports it
    import knowledge_manager.llm as llm_mod

    llm_mod.embed_texts = _fake_embed
    # And patch OpenAIEmbeddings.embed_documents just in case
    try:
        from langchain_openai import OpenAIEmbeddings

        OpenAIEmbeddings.embed_documents = lambda self, texts: _fake_embed(texts)
    except Exception:
        pass

    # Patch the extractor to be a no-op (since we can't call the LLM).
    from knowledge_manager.ingestion import extractor

    def _stub_extract(text):
        from knowledge_manager.ingestion.extractor import ExtractionResult

        return ExtractionResult(entities=[], relationships=[])

    extractor.extract = _stub_extract
    # pipeline calls `extract` directly via `from .extractor import extract`
    pl.extract = _stub_extract

    report = pipeline.ingest_directory(target_path, extract_entities=False)
    print(
        f"\nDone: {report.n_files} files, {report.n_chunks} chunks, "
        f"{report.n_entities} entities, {report.n_relationships} rels "
        f"in {report.elapsed_s:.1f}s"
    )
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "eval/data/documents"
    sys.exit(main(target))
