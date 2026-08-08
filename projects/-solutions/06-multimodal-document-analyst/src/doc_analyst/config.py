"""Application configuration.

All settings are loaded from environment variables (with a fallback to
`.env`). The module exposes a singleton `settings` instance imported
throughout the codebase.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Project settings.

    The defaults below let the project run with zero configuration:
    ChromaDB on local disk, z-ai SDK for VLM/embeddings/LLM, no API
    keys required.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Storage ----
    data_dir: Path = Field(default=Path("./.data"))
    chroma_text_collection: str = "doc_text"
    chroma_caption_collection: str = "doc_captions"

    # ---- Providers ----
    vlm_provider: Literal["zai", "openai"] = "zai"
    llm_provider: Literal["zai", "openai"] = "zai"
    embedding_provider: Literal["zai", "chroma_default"] = "chroma_default"

    # ---- OpenAI (only used when provider=openai) ----
    openai_api_key: str = ""
    openai_vision_model: str = "gpt-4o"
    openai_chat_model: str = "gpt-4o-mini"

    # ---- Embeddings ----
    embedding_model: str = "all-MiniLM-L6-v2"

    # ---- Retrieval ----
    top_k_text: int = 5
    top_k_captions: int = 3
    top_k_tables: int = 3

    # ---- API server ----
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ---- Observability ----
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "multimodal-document-analyst"

    # ---- Misc ----
    log_level: str = "INFO"

    # ---- Derived properties ----
    @property
    def chroma_path(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def pdf_cache_path(self) -> Path:
        return self.data_dir / "pdf_cache"

    @property
    def page_images_path(self) -> Path:
        return self.data_dir / "page_images"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "documents.db"

    def ensure_dirs(self) -> None:
        """Create all on-disk directories used by the project."""
        for p in (
            self.data_dir,
            self.chroma_path,
            self.pdf_cache_path,
            self.page_images_path,
        ):
            p.mkdir(parents=True, exist_ok=True)


# Apply LangSmith env vars BEFORE langchain is imported anywhere.
settings = Settings()
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)

settings.ensure_dirs()
