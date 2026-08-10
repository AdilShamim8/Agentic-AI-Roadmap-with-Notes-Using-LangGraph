"""
Pluggable LLM Backend.

Provides a uniform async interface for generating text completions.
Two backends ship out-of-the-box:

    * ``MockLLM``       — deterministic, no API key required (default)
    * ``OpenAIBackend`` — uses the OpenAI Chat Completions API

The backend is selected via the ``LLM_BACKEND`` environment variable:

    LLM_BACKEND=mock        # default
    LLM_BACKEND=openai      # requires OPENAI_API_KEY

This design lets the entire cross-framework network run end-to-end
without any external dependencies, while remaining trivially swappable
for production use with real LLMs.
"""

from llm.base import LLMBackend, LLMResponse, get_llm
from llm.mock import MockLLM
from llm.openai_backend import OpenAIBackend

__all__ = [
    "LLMBackend",
    "LLMResponse",
    "MockLLM",
    "OpenAIBackend",
    "get_llm",
]
