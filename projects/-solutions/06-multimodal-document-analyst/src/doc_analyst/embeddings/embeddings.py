"""Embeddings client.

Wraps the embedding provider so the rest of the code can call
`embed_texts([...]) -> list[list[float]]` without caring who serves the
vectors.

Two providers are supported:
  - `zai` (default): uses the z-ai SDK's `embedding` function via the CLI.
  - `chroma_default`: uses ChromaDB's bundled SentenceTransformers model
    (all-MiniLM-L6-v2). Useful when running offline or to avoid any LLM
    API at all.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..utils.logging import get_logger
from .vlm import VLMError

log = get_logger(__name__)


class EmbeddingError(RuntimeError):
    pass


class EmbeddingClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


# ----------------------------------------------------------------------
# Chroma default (SentenceTransformers, no API key)
# ----------------------------------------------------------------------
class ChromaDefaultEmbeddings(EmbeddingClient):
    def __init__(self) -> None:
        try:
            from chromadb.utils import embedding_functions  # type: ignore

            self._fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(
                "Could not load SentenceTransformer embeddings. "
                "Install `sentence-transformers` or switch EMBEDDING_PROVIDER=zai."
            ) from exc

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._fn, texts)


# ----------------------------------------------------------------------
# z-ai adapter
# ----------------------------------------------------------------------
class ZAIEmbeddings(EmbeddingClient):
    def __init__(self) -> None:
        self._cli = os.environ.get("ZAI_CLI", "z-ai")
        self._model = settings.embedding_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        # z-ai CLI `function` accepts a JSON args object. The function name
        # for embeddings is `embedding`.
        return await loop.run_in_executor(None, self._embed_sync, texts)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as in_f:
            json.dump({"texts": texts, "model": self._model}, in_f)
            tmp = in_f.name
        out_path = tmp + ".out"
        try:
            cmd = [
                self._cli,
                "function",
                "--name",
                "embedding",
                "--args",
                json.dumps({"texts": texts, "model": self._model}),
                "--output",
                out_path,
            ]
            log.debug("z-ai embedding: batch size=%d", len(texts))
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, check=False
            )
            if result.returncode != 0:
                raise EmbeddingError(
                    f"z-ai embedding failed (exit {result.returncode}): "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            if not os.path.exists(out_path):
                # Some CLI versions print JSON to stdout.
                return self._parse(result.stdout)
            data = json.loads(Path(out_path).read_text())
            return self._parse(data)
        finally:
            for p in (tmp, out_path):
                try:
                    os.unlink(p)
                except FileNotFoundError:
                    pass

    @staticmethod
    def _parse(data: Any) -> list[list[float]]:
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict):
            # Try common shapes.
            for key in ("embeddings", "data", "vectors"):
                if key in data:
                    return [list(map(float, v)) for v in data[key]]
            inner = data.get("data", data)
            if isinstance(inner, dict):
                for key in ("embeddings", "data", "vectors"):
                    if key in inner:
                        return [list(map(float, v)) for v in inner[key]]
        raise EmbeddingError(f"Could not parse embedding response: {str(data)[:200]}")


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------
_client: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    global _client
    if _client is None:
        if settings.embedding_provider == "zai":
            try:
                _client = ZAIEmbeddings()
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "z-ai embeddings unavailable (%s). "
                    "Falling back to Chroma default.",
                    exc,
                )
                _client = ChromaDefaultEmbeddings()
        elif settings.embedding_provider == "chroma_default":
            _client = ChromaDefaultEmbeddings()
        else:
            raise EmbeddingError(
                f"Unknown embedding provider: {settings.embedding_provider}"
            )
    return _client


# Expose VLMError here too for convenience.
__all__ = [
    "EmbeddingClient",
    "ChromaDefaultEmbeddings",
    "ZAIEmbeddings",
    "get_embedding_client",
    "EmbeddingError",
    "VLMError",
]
