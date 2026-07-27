"""Pytest tests for the example agents.

Run:
    pytest examples/tests/ -v

These tests verify that the example agents work correctly. They do not
test the LLM (which is probabilistic); they test the graph structure,
the tool wiring, and the error handling.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the examples directory to the path so we can import the agents.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_langgraph_core_graph_terminates():
    """The core demo graph should terminate with the expected value."""
    from examples.langgraph_core_demo import agent

    result = agent.invoke({"value": 3, "steps": 0})
    assert result["value"] == 14, f"Expected 14, got {result['value']}"
    assert result["steps"] == 3, f"Expected 3 steps, got {result['steps']}"


def test_calculator_tool_handles_errors():
    """The calculator tool should return an error, not raise."""
    from examples.react_demo import calculator

    result = calculator.invoke({"expression": "1/0"})
    assert "Error" in result


def test_weather_tool_returns_string():
    """The weather tool should return a string with the location."""
    from examples.conversational_agent_demo import get_weather

    result = get_weather.invoke({"location": "San Francisco"})
    assert "San Francisco" in result
    assert "72F" in result


def test_structured_output_agent_has_max_iterations():
    """The structured output agent should respect the max_iterations parameter."""
    from examples.structured_output_demo import run_agent

    # A nonsense question should hit the max iterations and return the fallback.
    result = run_agent("xyzzy", max_iterations=2)
    assert isinstance(result, str)
    assert len(result) > 0


def test_mcp_filesystem_server_exists():
    """The MCP filesystem server module should import cleanly."""
    from examples.mcp_filesystem_server import server

    assert server.name == "filesystem-server"
