"""Web-search MCP server (offline mock).

Implements a tiny in-memory knowledge base so the project runs end-to-end
without an external search API. To use a real search backend, replace the
body of ``search_web`` and ``fetch_page`` with calls to your provider
(Serper, Brave, Tavily, …) – the tool signatures are designed to match
common search APIs.

Run as a stdio MCP server::

    python3 -m mcp_servers.search_server
"""

from __future__ import annotations

import os
from typing import List

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("search")

# A tiny in-memory "internet". Each entry is (url, title, snippet, body).
_PAGES: List[dict] = [
    {
        "url": "https://en.wikipedia.org/wiki/Model_Context_Protocol",
        "title": "Model Context Protocol - Wikipedia",
        "snippet": "The Model Context Protocol (MCP) is an open standard, "
                   "introduced by Anthropic in 2024, for exposing tools and "
                   "resources to LLM-powered applications.",
        "body": "The Model Context Protocol (MCP) is an open standard introduced "
                "by Anthropic in November 2024. It defines a JSON-RPC based "
                "protocol that allows AI assistants to discover and invoke "
                "tools, resources and prompts exposed by external servers. "
                "The reference implementations are written in Python and "
                "TypeScript and support stdio, SSE and WebSocket transports.",
    },
    {
        "url": "https://langchain-ai.github.io/langgraph/",
        "title": "LangGraph - Build Resilient Language Agents",
        "snippet": "LangGraph is a library for building stateful, multi-actor "
                   "applications with LLMs. It models the agent as a graph.",
        "body": "LangGraph models an agent as a directed graph of nodes (Python "
                "functions) and edges (conditional routing). State is a typed "
                "dictionary passed between nodes. Built-in checkpointing lets "
                "you resume long-running agents, interrupt for human review, "
                "and replay past runs. Version 1.0 was released in 2024.",
    },
    {
        "url": "https://docs.anthropic.com/claude/docs/tool-use",
        "title": "Tool use with Claude - Anthropic Docs",
        "snippet": "Claude can invoke external tools by emitting a structured "
                   "tool_use block; the caller executes the tool and returns "
                   "the result.",
        "body": "Claude's tool-use API accepts a JSON schema per tool. The model "
                "may emit a tool_use block containing the tool name and "
                "arguments; the caller is responsible for executing the tool "
                "and returning a tool_result block. This maps cleanly onto "
                "MCP tools.",
    },
    {
        "url": "https://news.ycombinator.com/item?id=39800123",
        "title": "Show HN: A Universal MCP Agent",
        "snippet": "We built an agent that discovers MCP servers from a local "
                   "registry and composes tools from them.",
        "body": "Our universal agent reads a registry.json of MCP servers, "
                "connects to each over stdio, lists their tools, and uses "
                "retrieval-based selection to pick the right tool for the "
                "user's goal. Selection accuracy is 88% on our 30-goal eval "
                "set with GPT-4o-mini.",
    },
    {
        "url": "https://www.example.com/weather/san-francisco",
        "title": "Weather: San Francisco, CA",
        "snippet": "Current conditions in San Francisco: 16C, partly cloudy, "
                   "humidity 72%, wind 12 km/h NW.",
        "body": "San Francisco weather forecast. Today: 16C, partly cloudy. "
                "Tomorrow: 18C, sunny. Weekly outlook: temperatures in the "
                "range 14-20C with morning fog giving way to afternoon sun.",
    },
    {
        "url": "https://www.example.com/finance/usd-pkr",
        "title": "USD to PKR exchange rate",
        "snippet": "1 USD = 278.5 PKR (last updated today).",
        "body": "The Pakistani Rupee traded at 278.5 per US Dollar today, "
                "down 0.3% from yesterday. Year-to-date the PKR has depreciated "
                "by 4.2% against the USD.",
    },
    {
        "url": "https://www.example.com/news/mcp-launch",
        "title": "Anthropic launches Model Context Protocol",
        "snippet": "Anthropic today announced MCP, an open standard for "
                   "connecting AI assistants to data sources and tools.",
        "body": "Anthropic today announced the Model Context Protocol (MCP), an "
                "open standard that lets AI assistants securely access data "
                "sources and tools. Early adopters include Block, Apollo, "
                "and Replit. The SDKs are open-source under the MIT license.",
    },
]


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> List[dict]:
    """Search the web for ``query`` and return up to ``max_results`` result
    snippets.

    Each result contains ``url``, ``title`` and ``snippet``. Use ``fetch_page``
    to retrieve the full body of a specific result.

    In this reference implementation the "web" is a small in-memory knowledge
    base. Swap the body of this function for a real search API (Serper /
    Brave / Tavily) to use it in production – the signature stays the same.

    Args:
        query: Free-text search query.
        max_results: Maximum number of results to return (default 5).

    Returns:
        List of dicts with keys ``url``, ``title``, ``snippet``.
    """
    q = query.lower()
    scored = []
    for p in _PAGES:
        text = (p["title"] + " " + p["snippet"] + " " + p["body"]).lower()
        # Tiny TF-style score: count of query terms in the document.
        score = sum(text.count(term) for term in q.split())
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [
        {"url": p["url"], "title": p["title"], "snippet": p["snippet"]}
        for _, p in scored[:max_results]
    ]


@mcp.tool()
def fetch_page(url: str) -> str:
    """Fetch the full body text of a web page by URL.

    Use this after ``search_web`` to read the content of a specific result.
    Returns the page body as plain text (HTML stripped).

    Args:
        url: Absolute URL of the page to fetch. Must be a URL previously
            returned by ``search_web`` (in this mock implementation).

    Returns:
        Page body as a string. Raises ValueError if the URL is unknown.
    """
    for p in _PAGES:
        if p["url"] == url:
            return p["body"]
    raise ValueError(f"Unknown URL: {url}")


@mcp.tool()
def current_time(timezone: str = "UTC") -> str:
    """Return the current date and time in ``timezone`` (IANA name).

    Convenience tool bundled with the search server because it's frequently
    needed alongside web lookups ("what's happening today in …"). Timezone
    resolution uses Python's ``zoneinfo`` so any IANA name works.

    Args:
        timezone: IANA timezone name, e.g. "UTC", "America/New_York",
            "Asia/Karachi". Defaults to "UTC".

    Returns:
        ISO-8601 timestamp string in the requested timezone.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(timezone)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Unknown timezone: {timezone}") from exc
    return datetime.now(tz).isoformat()


if __name__ == "__main__":
    # Tiny self-test when run directly (not via stdio).
    if os.environ.get("MCP_SEARCH_SELFTEST") == "1":
        import os
        print(search_web("MCP"))
        print(current_time("Asia/Karachi"))
    else:
        mcp.run(transport="stdio")
