# Project 05 — MCP Universal Agent

> Difficulty ⭐⭐⭐⭐ · Estimated time 3–4 weeks · **Reference implementation**

A universal agent that accomplishes arbitrary user goals by **dynamically
discovering** MCP servers from a local registry, listing their tools, picking
the right tool(s) for the goal, executing them, and synthesising a final
answer. The agent has **no built-in tools of its own** – every capability
lives behind an MCP server.

This is the canonical "MCP" project from the
[Agentic-AI-Roadmap-with-Notes-and-Projects](https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects)
curriculum.

---

## Table of contents

1. [Architecture](#architecture)
2. [Repository layout](#repository-layout)
3. [Quick start](#quick-start)
4. [The five-stage loop](#the-five-stage-loop)
5. [Tool-selection strategies](#tool-selection-strategies)
6. [MCP servers](#mcp-servers)
7. [Evaluation harness](#evaluation-harness)
8. [Configuration](#configuration)
9. [Testing](#testing)
10. [Stretch goals](#stretch-goals)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                              User goal                                │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  1. Discover   – read registry.json, spawn every MCP server via      │
│                   stdio, list the tools each one exposes             │
├──────────────────────────────────────────────────────────────────────┤
│  2. List tools – flat list of ToolInfo(name, server, category,       │
│                   description, input_schema)                         │
├──────────────────────────────────────────────────────────────────────┤
│  3. Select     – naive | categorized | retrieval (default)           │
│                   – retrieval uses a TF-IDF index over descriptions  │
├──────────────────────────────────────────────────────────────────────┤
│  4. Execute    – LangGraph node calls the right MCP server session   │
│                   with the LLM-chosen arguments                      │
├──────────────────────────────────────────────────────────────────────┤
│  5. Synthesise – feed tool results back to the LLM; loop 4–5 until   │
│                   the LLM emits a final text answer                  │
└──────────────────────────────────────────────────────────────────────┘
                                    ▼
                            Final answer + trace
```

The LangGraph state machine:

```
select ──▶ llm ──▶ {tool_calls?} ──yes──▶ execute ──▶ select
                  │
                  └──no──▶ synthesise ──▶ END
```

---

## Repository layout

```
mcp-universal-agent/
├── README.md                    # this file
├── requirements.txt             # pinned deps (mcp, langgraph, openai, numpy)
├── .env.example                 # copy to .env and fill in API keys
├── .gitignore
├── registry.json                # the MCP server registry (discovery source)
│
├── data/                        # sandbox for the filesystem + sqlite servers
│   ├── sample.txt               #   a Q3 launch plan
│   ├── notes.md                 #   engineering notes
│   └── todo.json                #   a todo list
│
├── mcp_servers/                 # 5 stdio MCP servers (FastMCP)
│   ├── filesystem_server.py     #   list / read / write / search / stats
│   ├── calculator_server.py     #   evaluate / statistics / convert_units / percentage
│   ├── sqlite_server.py         #   list_tables / describe_table / run_query
│   ├── search_server.py         #   search_web / fetch_page / current_time (offline mock)
│   └── custom_server.py         #   uuid / hash / currency / string / kv
│
├── agent/                       # the agent itself
│   ├── discovery.py             #   stage 1–2: spawn servers, list tools
│   ├── embeddings.py            #   TF-IDF index for retrieval-based selection
│   ├── tool_selector.py         #   stage 3: naive | categorized | retrieval
│   ├── llm.py                   #   OpenAI / Anthropic / Mock LLM abstraction
│   ├── graph.py                 #   LangGraph: stage 4 (execute) + 5 (synthesise)
│   └── cli.py                   #   `python3 -m agent.cli "goal"`
│
├── evals/                       # evaluation harness
│   ├── goals.jsonl              #   30 hand-labeled user goals
│   └── run_evals.py             #   runs every goal, prints the rubric table
│
└── tests/
    └── test_agent.py            # pytest suite (no API key required)
```

---

## Quick start

```bash
# 1. Install deps (Python 3.10+)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. (Optional) configure an LLM provider.
#    Without a key the agent falls back to a deterministic MockLLM so you
#    can still smoke-test the full loop end-to-end.
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...   (or ANTHROPIC_API_KEY=sk-ant-...)

# 3. Run a one-shot goal.
python3 -m agent.cli "List every file in the sandbox."

# 4. Interactive REPL.
python3 -m agent.cli --interactive

# 5. Run the eval suite (30 goals, prints the rubric table).
python3 -m evals.run_evals
```

A successful run looks like:

```
[01/30] g01: List every file in the sandbox.
       -> sel=1.00  comp=1  args=1.00  tools=['filesystem.list_files']
[02/30] g02: Read the contents of sample.txt.
       -> sel=1.00  comp=1  args=1.00  tools=['filesystem.read_file']
...

========================================================================
EVAL SUMMARY
========================================================================
{
  "n_goals": 30,
  "tool_selection_accuracy": 0.88,
  "task_completion": 0.83,
  "tool_argument_correctness": 0.93,
  "provider": "openai",
  "strategy": "retrieval"
}

Rubric vs. target:
  PASS  tool_selection_accuracy         got=88.00%  target=85%
  PASS  task_completion                 got=83.00%  target=75%
  PASS  tool_argument_correctness       got=93.00%  target=90%
  PASS  robustness_completion           got=80.00%  target=70%
```

---

## The five-stage loop

| Stage | File | Responsibility |
|-------|------|----------------|
| 1. Discover | `agent/discovery.py` | Read `registry.json`, spawn each MCP server as a stdio subprocess, call `session.initialize()`. |
| 2. List tools | `agent/discovery.py` | Call `session.list_tools()` on every server; flatten into a single `list[ToolInfo]`. |
| 3. Select | `agent/tool_selector.py` | Pick which tools the LLM sees this turn (see below). |
| 4. Execute | `agent/graph.py::_execute_tools_node` | Dispatch each `ToolCall` to the right MCP `session.call_tool(...)`. |
| 5. Synthesise | `agent/graph.py::_synthesize_node` | If the LLM emitted text, return it; otherwise prompt it to summarise. |

The loop is implemented as a LangGraph `StateGraph` with a conditional edge
on the LLM node: if the LLM emitted tool calls we go to `execute`, otherwise
to `synthesize`. The loop is bounded by `MCP_AGENT_MAX_ITERATIONS` (default
8) to prevent runaway tool-call chains.

---

## Tool-selection strategies

The spec's central challenge is **step 3**: when the tool list grows past
~15 tools, naive selection accuracy collapses. This project ships three
mitigation strategies, switchable at runtime via
`MCP_AGENT_SELECTION_STRATEGY`:

| Strategy | How it works | When to use |
|----------|--------------|-------------|
| `naive` | Pass ALL tools to the LLM every turn. | Baseline / debugging. Cheapest to reason about, worst accuracy above ~10 tools. |
| `categorized` | Two-stage call: first ask the LLM to pick a *category* ("files", "math", "data", "web", "misc"), then pass only tools from that category. | When you want to cut the tool list in half with a cheap extra LLM call. |
| `retrieval` *(default)* | At startup, build a TF-IDF index over every tool description. For each user message, retrieve the top-k (`MCP_AGENT_RETRIEVAL_TOP_K`, default 12) most similar tools and pass only those. | Best accuracy on the 20-tool registry. No external API needed. |

You can override per-run:

```bash
MCP_AGENT_SELECTION_STRATEGY=categorized python3 -m agent.cli "Convert 100 USD to PKR"
python3 -m evals.run_evals --strategy naive    # measure the baseline
```

### Why TF-IDF, not OpenAI ada-002?

1. Tool descriptions are short (1–3 sentences). TF-IDF discriminates them
   well at sub-millisecond latency for ~50 tools.
2. The project must run end-to-end without any API key. Depending on
   `text-embedding-3-small` would break that property.
3. The retrieval index rebuilds every time the registry changes, so it
   has to be fast. TF-IDF over 50 docs is essentially free.

If you want real embeddings, replace `agent/embeddings.py::TfIdfIndex`
with an OpenAI-embeddings-backed class that exposes the same `fit()` /
`top_k()` interface. Nothing else in the codebase needs to change.

---

## MCP servers

Five stdio MCP servers, all implemented with `mcp.server.fastmcp.FastMCP`.
Each one is a standalone Python module you can run directly to inspect:

```bash
MCP_FS_ROOT=./data python3 -m mcp_servers.filesystem_server   # then type JSON-RPC on stdin
```

| Server | Module | Tools | Notes |
|--------|--------|-------|-------|
| filesystem | `mcp_servers.filesystem_server` | `list_files`, `read_file`, `write_file`, `search_files`, `file_stats` | Sandboxed to `MCP_FS_ROOT`. Refuses `../` escapes. |
| calculator | `mcp_servers.calculator_server` | `evaluate`, `statistics`, `convert_units`, `percentage` | Safe AST evaluator (no `eval`). |
| sqlite | `mcp_servers.sqlite_server` | `list_tables`, `describe_table`, `run_query` | Auto-seeds a tiny demo schema on first run. |
| search | `mcp_servers.search_server` | `search_web`, `fetch_page`, `current_time` | Offline mock "web" – swap the body for a real search API in production. |
| custom | `mcp_servers.custom_server` | `uuid_v4`, `hash_text`, `convert_currency`, `transform_string`, `kv_store` | Misc utilities. KV store is per-process. |

### Adding your own server

1. Write a new `mcp_servers/my_server.py` with one or more `@mcp.tool()`
   functions.
2. Add an entry to `registry.json`:

```json
{
  "name": "my_server",
  "category": "custom_cat",
  "description": "What this server does, in one line.",
  "command": "python3",
  "args": ["-m", "mcp_servers.my_server"],
  "env": {}
}
```

3. Re-run the agent. Discovery will pick it up automatically – no agent code
   changes required.

---

## Evaluation harness

`evals/goals.jsonl` contains 30 hand-labeled user goals spanning all five
servers. Each line is:

```json
{"id":"g01","goal":"List every file in the sandbox.",
 "expected_tools":["filesystem.list_files"],
 "category":"files","difficulty":"easy"}
```

Run the suite:

```bash
python3 -m evals.run_evals                 # all 30 goals
python3 -m evals.run_evals --limit 5       # first 5 only
python3 -m evals.run_evals --only g01,g06  # specific goals
python3 -m evals.run_evals --robustness    # run with the 'custom' server killed
```

The runner computes the four metrics from the spec rubric and prints a
pass/fail table against the targets:

| Metric | Target |
|--------|--------|
| Tool-selection accuracy | 85% |
| Task completion | 75% |
| Tool-argument correctness | 90% |
| Robustness to tool failure | 70% |

A full JSON report is written to `evals/results/report.json` (or
`report_robustness.json` for the robustness suite).

### LLM-as-judge

By default the eval uses a deterministic, rule-based completion check (no
API key needed). For real scoring, set `OPENAI_API_KEY` – the agent will
use GPT-4o-mini and the rubric will reflect a real LLM's selection
accuracy.

---

## Configuration

All configuration is via environment variables (read from `.env`
automatically by `agent/cli.py`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `OPENAI_API_KEY` | *(unset)* | If set, agent uses OpenAI for selection + synthesis. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Override the OpenAI model. |
| `OPENAI_BASE_URL` | *(unset)* | Override for Azure / proxies. |
| `ANTHROPIC_API_KEY` | *(unset)* | If set, agent uses Claude Sonnet. |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Override the Claude model. |
| `MCP_AGENT_USE_MOCK_LLM` | `false` | If `true`, force the deterministic MockLLM. |
| `MCP_AGENT_SELECTION_STRATEGY` | `retrieval` | `naive` / `categorized` / `retrieval`. |
| `MCP_AGENT_RETRIEVAL_TOP_K` | `12` | Tools retrieved per turn under `retrieval`. |
| `MCP_AGENT_MAX_ITERATIONS` | `8` | Loop cap to prevent runaway tool-call chains. |
| `LANGSMITH_API_KEY` | *(unset)* | If set, LangGraph traces are sent to LangSmith. |

---

## Testing

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

The test suite covers:

- The TF-IDF index (`test_tfidf_top_k_returns_relevant_doc`,
  `test_tfidf_handles_empty_index`).
- All three tool-selection strategies
  (`test_naive_strategy_passes_all_tools`,
  `test_retrieval_strategy_returns_top_k`,
  `test_categorized_strategy_keyword_fallback`).
- MCP server wiring via real stdio subprocesses
  (`test_discovery_lists_tools_from_all_servers`,
  `test_calculator_server_evaluates_expression`).
- The full agent loop with the MockLLM (`test_agent_loop_with_mock_llm`).

None of the tests require an API key.

---

## Stretch goals

The spec lists three stretch goals. Implementation hints:

1. **Tool conflicts** – two tools can satisfy the same intent.
   Add a `priority` field to `registry.json` entries and have the selector
   break ties by priority when retrieval scores are within ε.

2. **Tool versioning** – different versions of the same tool.
   Extend `ToolInfo` with a `version` field and have `tool_selector.py`
   prefer the highest version when duplicate bare names are retrieved.

3. **Per-user tool preferences** – learn which tools a user prefers.
   Log every successful `(user_id, tool_name)` pair and bias the
   retrieval scores by historical frequency. A 10-line SQLite table is
   enough to get started.

---

## References

- [Model Context Protocol spec](https://modelcontextprotocol.io)
- [MCP servers registry](https://github.com/modelcontextprotocol/servers) – pre-built MCP servers
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [Anthropic tool-use docs](https://docs.anthropic.com/claude/docs/tool-use)

## License

MIT – see the upstream curriculum repo for details.
