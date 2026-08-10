# Project 08 — Cross-Framework Agent Network

> **Difficulty:** ⭐⭐⭐⭐⭐ | **Estimated time:** 4–6 weeks | **Status:** ✅ Reference implementation

A reference implementation of a **cross-framework multi-agent network** that demonstrates the [A2A (Agent-to-Agent) protocol](https://google.github.io/A2A/) for interoperability between three different AI agent frameworks:

| Framework | Role | Exposed via |
|-----------|------|-------------|
| **LangGraph** | Supervisor / orchestrator | A2A client |
| **OpenAI Agents SDK** | Research agent | A2A server (port 8001) |
| **CrewAI** | Writer crew | A2A server (port 8002) |

The supervisor decomposes a user task, delegates sub-tasks to the appropriate agent via A2A, and synthesizes the results. Each agent runs in its own process and communicates exclusively through the A2A protocol — proving that the protocol enables true framework-agnostic interop.

---

## Architecture

```
┌─────────────┐
│  User Task  │
└──────┬──────┘
       ▼
┌──────────────────────┐
│  LangGraph Supervisor │
│  (plan → exec → synth)│
└────┬─────────────┬───┘
     │ A2A         │ A2A
     ▼             ▼
┌─────────────┐ ┌─────────────┐
│  Research    │ │   Writer    │
│  Agent       │ │   Crew      │
│ (OpenAI SDK) │ │  (CrewAI)   │
│  :8001       │ │  :8002      │
└─────────────┘ └─────────────┘
```

### How it works

1. **Plan** — The supervisor uses an LLM to decompose the user's task into 2–4 steps, each routed to `research` or `writing`.
2. **Execute** — For each step, the supervisor sends an A2A `tasks/send` request to the appropriate agent server. The agent processes the request and returns a completed task with an artifact.
3. **Synthesize** — Once all steps complete, the supervisor merges the results into a coherent final output.

Each A2A handoff is measured for latency, success, and payload size — feeding the evaluation metrics.

---

## Quick Start

### Prerequisites

- Python 3.10+
- No API keys required (uses a deterministic mock LLM by default)

### Option 1: One-command demo

```bash
cd 08-cross-framework-network
make install          # install dependencies
make demo             # start agents + run a demo task
```

This starts both A2A agent servers in background threads, runs the supervisor on a sample task, and prints the result with interop metrics.

### Option 2: Manual (three terminals)

```bash
# Terminal 1 — Research agent (OpenAI Agents SDK pattern)
python -m agents.openai_research.server --port 8001

# Terminal 2 — Writer crew (CrewAI pattern)
python -m agents.crewai_writer.server --port 8002

# Terminal 3 — Supervisor
python -m supervisor.cli "Research multi-agent AI systems and write a blog post about it"
```

### Option 3: Docker

```bash
cp .env.example .env
docker compose up -d research-agent writer-crew
docker compose run --rm supervisor "Research and write about the A2A protocol"
docker compose down
```

---

## Using a Real LLM (Optional)

The project ships with a deterministic **mock LLM** so it runs without any API keys. To use a real OpenAI model:

```bash
# 1. Install the OpenAI package
pip install openai

# 2. Set environment variables
export LLM_BACKEND=openai
export OPENAI_API_KEY=sk-your-key-here
export OPENAI_MODEL=gpt-4o   # optional, defaults to gpt-4o

# 3. Run as usual
python -m examples.demo
```

The LLM backend is pluggable — see [`llm/`](llm/) for the interface. You can add Anthropic, local models, or any other backend by implementing `LLMBackend`.

---

## Project Structure

```
08-cross-framework-network/
├── a2a/                           # A2A Protocol Core
│   ├── models.py                  #   AgentCard, Task, Message, Part, ...
│   ├── exceptions.py              #   JSON-RPC error types
│   ├── protocol.py                #   JSON-RPC 2.0 helpers
│   ├── server.py                  #   FastAPI A2A server + task manager
│   └── client.py                  #   Async A2A client
│
├── agents/                        # A2A Agent Servers
│   ├── shared.py                  #   Shared server-building utilities
│   ├── openai_research/           #   OpenAI Agents SDK → research agent
│   │   ├── agent.py               #     Agent definition (mirrors openai.agents.Agent)
│   │   └── server.py              #     A2A server wrapping the agent
│   └── crewai_writer/             #   CrewAI → writer crew
│       ├── crew.py                #     Crew definition (mirrors crewai.Crew)
│       └── server.py              #     A2A server wrapping the crew
│
├── supervisor/                    # LangGraph Supervisor
│   ├── state.py                   #   Graph state (plan, steps, handoffs)
│   ├── nodes.py                   #   Graph nodes (plan, execute, synthesize)
│   ├── graph.py                   #   State machine (mirrors LangGraph StateGraph)
│   ├── a2a_adapter.py             #   A2A client adapter with telemetry
│   └── cli.py                     #   CLI entry point
│
├── llm/                           # Pluggable LLM Backend
│   ├── base.py                    #   Abstract interface + factory
│   ├── mock.py                    #   Deterministic mock (default)
│   └── openai_backend.py          #   Real OpenAI backend (optional)
│
├── eval/                          # Evaluation Framework
│   ├── dataset.json               #   20 multi-step tasks
│   ├── metrics.py                 #   4-metric computation
│   └── runner.py                  #   Eval runner
│
├── tests/                         # Test Suite (pytest + pytest-asyncio)
│   ├── test_a2a_models.py
│   ├── test_a2a_server.py
│   ├── test_a2a_client.py
│   ├── test_research_agent.py
│   ├── test_writer_agent.py
│   └── test_supervisor.py
│
├── examples/                      # Example Scripts
│   ├── demo.py                    #   One-command demo
│   └── run_eval.py                #   Run the evaluation locally
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md
│   ├── A2A_PROTOCOL.md
│   └── DEPLOYMENT.md
│
├── Dockerfile                     # Shared Docker image
├── docker-compose.yml             # 3-service orchestration
├── Makefile                       # Common commands
├── pyproject.toml                 # Project config
├── requirements.txt               # Dependencies
└── .env.example                   # Environment template
```

---

## Evaluation

The project includes an evaluation framework with 20 multi-step tasks and four metrics aligned with the project spec:

| Metric | Target | How Measured |
|--------|--------|--------------|
| **Task completion** | ≥ 80% | Fraction of tasks reaching COMPLETED state |
| **Interop correctness** | 100% | Fraction of A2A handoffs that succeed |
| **Latency overhead** | < 2,000ms per handoff | Average A2A round-trip time |
| **Cost overhead** | < 10% of total cost | Protocol overhead vs. productive work |

### Run the evaluation

```bash
# Full eval (20 tasks)
make eval

# Quick eval (first 3 tasks)
make eval-quick

# Or directly
python -m eval.runner --limit 5
```

Results are saved to `eval/results/eval_results.json`.

---

## Testing

```bash
# Run all tests
make test

# With coverage
make test-cov
```

Tests use `pytest` + `pytest-asyncio` and run against in-process ASGI transports (no real network needed). The test suite covers:

- A2A model serialization and validation
- A2A server JSON-RPC dispatch (send, get, cancel, list, errors)
- A2A client discovery and task operations
- Research agent execution
- Writer crew execution
- Full supervisor integration (end-to-end with in-process A2A)

---

## Key Design Decisions

### 1. Self-contained A2A protocol implementation

Rather than depending on an external A2A SDK, the protocol is implemented from scratch in [`a2a/`](a2a/). This makes the interop mechanics transparent and educational — you can see exactly how JSON-RPC 2.0 requests flow, how tasks transition through their lifecycle, and how Agent Cards enable discovery.

### 2. Pluggable LLM backend

The [`llm/`](llm/) package provides a uniform async interface with two backends:
- **MockLLM** (default): deterministic, no API key, produces realistic structured output
- **OpenAIBackend**: real GPT-4o (or any OpenAI model)

This lets the entire network run end-to-end out of the box, while remaining trivially swappable for production.

### 3. Framework pattern mirroring

The agents mirror their real framework patterns:
- `agents/openai_research/agent.py` mirrors `openai.agents.Agent` (name, instructions, model, tools)
- `agents/crewai_writer/crew.py` mirrors `crewai.Crew` (agents, tasks, sequential process)

This means swapping in the real SDKs is straightforward — replace the mock execution with real SDK calls.

### 4. Telemetry-first handoffs

Every A2A handoff records a [`HandoffRecord`](supervisor/state.py) with latency, success, payload size, and error info. This feeds the evaluation metrics and makes interop overhead measurable — the core deliverable of the project.

---

## Stretch Goals

The spec lists three stretch goals. Here's how they'd be implemented:

| Stretch Goal | Implementation Path |
|---|---|
| **Dynamic agent discovery** | The A2A client already fetches Agent Cards at `/.well-known/agent.json`. Add a registry service that lists agent URLs; the supervisor queries it at startup. |
| **Agent failover** | The `A2AAdapter` already catches errors. Add backup URLs per agent type and retry on failure. |
| **Agent versioning** | Agent Cards have a `version` field. Add version negotiation in the adapter — fetch the card, check version, route accordingly. |

---

## References

- [A2A Protocol Specification](https://google.github.io/A2A/)
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [CrewAI](https://github.com/crewAIInc/crewAI)
- [LangGraph](https://github.com/langchain-ai/langgraph)

---

## License

MIT — see the project repository for details.
