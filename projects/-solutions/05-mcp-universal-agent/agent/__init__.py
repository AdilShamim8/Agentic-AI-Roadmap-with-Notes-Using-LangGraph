"""Universal MCP agent package.

The package is organised around the five-stage loop from the project spec:

    discover -> list tools -> select tools -> execute -> synthesise

Each stage is a separate module so the pieces can be tested in isolation:

- :mod:`agent.discovery`     – read ``registry.json`` and connect to servers.
- :mod:`agent.embeddings`    – tiny TF-IDF embeddings for tool retrieval.
- :mod:`agent.tool_selector` – naive / categorized / retrieval strategies.
- :mod:`agent.llm`           – OpenAI / Anthropic / mock LLM abstraction.
- :mod:`agent.graph`         – the LangGraph orchestration.
- :mod:`agent.cli`           – command-line entry point.

Run from the project root::

    python3 -m agent.cli "What files are in the sandbox?"
"""

from .graph import build_graph, run_agent
from .discovery import discover_servers, DiscoveredServer, ToolInfo

__all__ = [
    "build_graph",
    "run_agent",
    "discover_servers",
    "DiscoveredServer",
    "ToolInfo",
]
