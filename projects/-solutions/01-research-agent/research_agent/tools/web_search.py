"""Web search backends.

Every backend implements `search(query, max_results) -> List[SearchResult]`.
DuckDuckGo is the default because it needs no API key at all, so the
project runs out of the box. Tavily is offered as an optional upgrade —
it's purpose-built for LLM agents and tends to return cleaner results.
"""

from __future__ import annotations

import os
from typing import Callable, List, Optional, Protocol

from ..state import SearchResult


class SearchTool(Protocol):
    def search(self, query: str, max_results: int = 4) -> List[SearchResult]: ...


class DuckDuckGoSearch:
    """Free, no-API-key web search using the `ddgs` package."""

    def __init__(self, region: str = "wt-wt", safesearch: str = "moderate"):
        self.region = region
        self.safesearch = safesearch

    def search(self, query: str, max_results: int = 4) -> List[SearchResult]:
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS  # older package name
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "The 'ddgs' package is required for DuckDuckGoSearch. "
                    "Install it with: pip install ddgs"
                ) from exc

        results: List[SearchResult] = []
        with DDGS() as ddgs:
            for hit in ddgs.text(
                query,
                region=self.region,
                safesearch=self.safesearch,
                max_results=max_results,
            ):
                results.append(
                    SearchResult(
                        title=hit.get("title", ""),
                        url=hit.get("href") or hit.get("link", ""),
                        snippet=hit.get("body", ""),
                    )
                )
        return results


class TavilySearch:
    """Search backend using Tavily's agent-oriented search API."""

    def __init__(self, api_key: Optional[str] = None):
        try:
            from tavily import TavilyClient
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "The 'tavily-python' package is required for TavilySearch. "
                "Install it with: pip install tavily-python"
            ) from exc

        self._client = TavilyClient(api_key=api_key or os.getenv("TAVILY_API_KEY"))

    def search(self, query: str, max_results: int = 4) -> List[SearchResult]:
        response = self._client.search(query=query, max_results=max_results)
        results = []
        for hit in response.get("results", []):
            results.append(
                SearchResult(
                    title=hit.get("title", ""),
                    url=hit.get("url", ""),
                    snippet=hit.get("content", ""),
                    content=hit.get("raw_content") or "",
                )
            )
        return results


class FakeSearch:
    """Deterministic, offline stand-in for tests and demos."""

    def __init__(self, responder: Optional[Callable[[str, int], List[SearchResult]]] = None):
        self.responder = responder or (lambda query, max_results: [])
        self.calls = []

    def search(self, query: str, max_results: int = 4) -> List[SearchResult]:
        self.calls.append({"query": query, "max_results": max_results})
        return self.responder(query, max_results)


def build_search_tool_from_env() -> SearchTool:
    """Factory: use Tavily if a key is configured, else fall back to
    the free DuckDuckGo backend."""

    if os.getenv("TAVILY_API_KEY"):
        return TavilySearch()
    return DuckDuckGoSearch()
