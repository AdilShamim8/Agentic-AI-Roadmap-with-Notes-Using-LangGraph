"""Tests for the universal MCP agent.

Run with::

    pip install pytest
    pytest tests/

These tests do NOT require an API key – they use the MockLLM and exercise
the orchestration, tool selection, embeddings and MCP server wiring.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# Force the mock LLM so tests run without any API key.
os.environ.setdefault("MCP_AGENT_USE_MOCK_LLM", "true")
os.environ.setdefault("MCP_AGENT_SELECTION_STRATEGY", "retrieval")


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
def test_tfidf_top_k_returns_relevant_doc():
    from agent.embeddings import TfIdfIndex
    docs = [
        "Read a file from disk.",
        "Run a SQL query against the database.",
        "Convert currencies using static rates.",
        "Compute the square root of a number.",
    ]
    idx = TfIdfIndex().fit(docs)
    # Query uses the actual tokens that appear in the docs (TF-IDF matches
    # tokens, not stems – so "sqrt" would NOT match "square root").
    top = idx.top_k("compute square root", k=2)
    assert top[0][0] == 3  # "Compute the square root of a number."
    assert top[0][1] > top[1][1]
    assert top[0][1] > 0.0  # the top score is positive


def test_tfidf_handles_empty_index():
    from agent.embeddings import TfIdfIndex
    idx = TfIdfIndex()
    assert idx.top_k("anything", k=3) == []


# ---------------------------------------------------------------------------
# Tool selector
# ---------------------------------------------------------------------------
def _fake_tools():
    from agent.discovery import ToolInfo
    return [
        ToolInfo(name="filesystem.read_file", server="filesystem", category="files",
                 tool_name="read_file", description="Read a file from disk.",
                 input_schema={"type": "object", "properties": {}}),
        ToolInfo(name="calculator.evaluate", server="calculator", category="math",
                 tool_name="evaluate", description="Compute an arithmetic expression.",
                 input_schema={"type": "object", "properties": {}}),
        ToolInfo(name="custom.uuid_v4", server="custom", category="misc",
                 tool_name="uuid_v4", description="Generate a UUID.",
                 input_schema={"type": "object", "properties": {}}),
    ]


def test_naive_strategy_passes_all_tools():
    from agent.tool_selector import ToolSelector
    sel = ToolSelector(_fake_tools(), strategy="naive")
    out = sel.select("anything", [])
    assert len(out.tools) == 3
    assert out.strategy == "naive"


def test_retrieval_strategy_returns_top_k():
    from agent.tool_selector import ToolSelector
    sel = ToolSelector(_fake_tools(), strategy="retrieval", top_k=2)
    out = sel.select("read a file", [])
    assert len(out.tools) == 2
    names = [t["function"]["name"] for t in out.tools]
    assert "filesystem.read_file" in names


def test_categorized_strategy_keyword_fallback():
    from agent.tool_selector import ToolSelector
    sel = ToolSelector(_fake_tools(), strategy="categorized", llm=None)
    out = sel.select("please read the file", [])
    assert out.rationale.startswith("keyword-picked category 'files'")
    names = [t["function"]["name"] for t in out.tools]
    assert names == ["filesystem.read_file"]


# ---------------------------------------------------------------------------
# MCP server wiring (subprocess smoke test)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_discovery_lists_tools_from_all_servers():
    from agent.discovery import discover_servers
    async with discover_servers(_ROOT / "registry.json") as d:
        names = {t.name for t in d.tools}
        # Every server should expose at least one tool.
        assert "filesystem.list_files" in names
        assert "calculator.evaluate" in names
        assert "sqlite.list_tables" in names
        assert "search.search_web" in names
        assert "custom.uuid_v4" in names


@pytest.mark.asyncio
async def test_calculator_server_evaluates_expression():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command="python3", args=["-m", "mcp_servers.calculator_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.call_tool("evaluate", {"expression": "2 + 3 * 4"})
            text = res.content[0].text
            # evaluate() returns float, so "14.0" – accept either form.
            assert float(text) == 14.0


# ---------------------------------------------------------------------------
# Full agent loop (mock LLM)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_loop_with_mock_llm():
    from agent.graph import run_agent
    result = await run_agent("List every file in the sandbox.",
                             registry_path=str(_ROOT / "registry.json"),
                             selection_strategy="retrieval")
    assert result["provider"] == "mock"
    assert result["iterations"] >= 1
    # The mock LLM should have triggered filesystem.list_files.
    tool_steps = [s for s in result["trace"] if s.get("step") == "tool"]
    assert any(s["tool"] == "filesystem.list_files" for s in tool_steps)
