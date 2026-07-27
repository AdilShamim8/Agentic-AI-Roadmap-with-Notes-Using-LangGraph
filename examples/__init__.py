"""Reference implementations for the agentic AI roadmap.

This directory contains runnable Python files that demonstrate the core
patterns from the curriculum. Each file is self-contained and can be run
standalone (with the right environment variables set).

The files are the source of truth; the notebooks in the curriculum
modules import from these files and add commentary.

## Files

- `conversational_agent_demo.py` - a conversational ReAct agent with a
  weather tool, persistence, and a recursion limit. The minimum viable
  production agent.
- `structured_output_demo.py` - structured outputs and tool calling with
  Pydantic schemas, retry on validation failure, and a max-iteration
  limit.
- `langgraph_core_demo.py` - a StateGraph with state, nodes, edges, a
  conditional edge, and a loop. Demonstrates the core LangGraph mental
  model.
- `mcp_filesystem_server.py` - a filesystem MCP server built with the
  `mcp` SDK. Exposes `read_file` and `list_directory` tools.
- `react_demo.py` - a ReAct agent with web search and calculator tools.
- `run_evals.py` - the eval runner used by `make eval` and the CI
  workflow. Loads the agent, loads the golden dataset, runs the agent
  on each row, scores the outputs, and produces a Markdown report.

## Running

```bash
# Install dependencies
make install

# Set up environment
cp .env.example .env
# edit .env with your API keys

# Run a demo
python examples/conversational_agent_demo.py

# Run the eval suite
make eval
```

## Environment

All examples read from environment variables (loaded from .env via
python-dotenv). The required variables are in `.env.example`.
"""

__version__ = "0.2.0"
