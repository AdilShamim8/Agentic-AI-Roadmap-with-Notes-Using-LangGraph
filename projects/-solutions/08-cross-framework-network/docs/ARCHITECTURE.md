# Architecture

## Overview

The cross-framework network follows a **hub-and-spoke** architecture:

```
                    ┌─────────────────────┐
                    │   LangGraph         │
                    │   Supervisor        │
                    │   (port: CLI)       │
                    └──────┬───────┬──────┘
                           │       │
                      A2A  │       │ A2A
                           ▼       ▼
              ┌──────────────┐   ┌──────────────┐
              │  Research     │   │   Writer     │
              │  Agent        │   │   Crew       │
              │  (OpenAI SDK) │   │   (CrewAI)   │
              │  :8001        │   │   :8002      │
              └──────────────┘   └──────────────┘
```

The supervisor is the only component that initiates A2A calls. The agents are passive A2A servers — they respond to `tasks/send` requests and return completed tasks.

## Component Details

### 1. A2A Protocol Core (`a2a/`)

The protocol layer is framework-agnostic and reusable. It implements:

- **Data models** (`models.py`): Pydantic v2 models for `AgentCard`, `Task`, `Message`, `Part` (text/data/file), `Artifact`, `TaskStatus`, and JSON-RPC envelopes.
- **Exceptions** (`exceptions.py`): JSON-RPC 2.0 error codes mapped to Python exceptions.
- **Protocol helpers** (`protocol.py`): Request/response builders and parsers.
- **Server** (`server.py`): A `FastAPI` application with:
  - `GET /.well-known/agent.json` — Agent Card discovery
  - `POST /` — JSON-RPC 2.0 handler (`tasks/send`, `tasks/get`, `tasks/cancel`, `tasks/list`)
  - `POST /tasks/sendSubscribe` — SSE streaming endpoint
- **Client** (`client.py`): An `httpx`-based async client with `send_task`, `get_task`, `cancel_task`, `list_tasks`, and `send_task_streaming`.

#### Task Lifecycle

```
    ┌───────────┐
    │ SUBMITTED │  ← client sends tasks/send
    └─────┬─────┘
          ▼
    ┌───────────┐
    │  WORKING  │  ← server transitions immediately
    └─────┬─────┘
          │
     ┌────┴────┐
     ▼         ▼
┌─────────┐ ┌──────────┐
│COMPLETED│ │  FAILED  │
└─────────┘ └──────────┘
     │              │
     ▼              ▼
  (artifact)   (error msg)
```

### 2. Research Agent (`agents/openai_research/`)

Mirrors the **OpenAI Agents SDK** pattern:

```python
# Real OpenAI Agents SDK:
from agents import Agent, Runner
agent = Agent(name="...", instructions="...", model="gpt-4o", tools=[...])
result = await Runner.run(agent, query)

# This project (same structure):
agent = ResearchAgent(name="...", instructions="...", model=get_llm(), tools=[...])
result = await agent.run(query)
```

The agent has two simulated tools:
- `web_search` — returns simulated search results
- `summarize` — returns a truncated summary

The agent augments the user query with search context, then generates a structured research briefing via the LLM backend.

### 3. Writer Crew (`agents/crewai_writer/`)

Mirrors the **CrewAI** pattern:

```python
# Real CrewAI:
from crewai import Agent, Task, Crew, Process
crew = Crew(agents=[...], tasks=[...], process=Process.sequential)
result = crew.kickoff(inputs={"topic": "..."})

# This project (same structure):
crew = WriterCrew()  # builds 3 agents + 3 tasks internally
result = await crew.kickoff(inputs={"topic": "..."})
```

The crew has three agents running sequentially:

| Step | Agent | Role |
|------|-------|------|
| 1 | Content Strategist | Plans structure, tone, outline |
| 2 | Writer | Drafts the content |
| 3 | Editor | Reviews, polishes, finalizes |

Each agent's output becomes context for the next — exactly like CrewAI's sequential process.

### 4. LangGraph Supervisor (`supervisor/`)

Mirrors the **LangGraph StateGraph** pattern:

```python
# Real LangGraph:
from langgraph.graph import StateGraph, END
graph = StateGraph(State)
graph.add_node("plan", plan_node)
graph.add_node("execute", execute_node)
graph.add_node("synthesize", synthesize_node)
graph.add_edge("plan", "execute")
graph.add_conditional_edges("execute", should_continue, {"execute": "execute", "synthesize": "synthesize"})
graph.add_edge("synthesize", END)

# This project (same flow, self-contained):
class SupervisorGraph:
    async def run(self, task):
        state = SupervisorState(task=task)
        state.plan = await plan_node(state)["plan"]       # Step 1: Plan
        while should_continue(state) == "execute":         # Step 2: Execute (loop)
            update = await execute_node(state, adapter)
            state.merge(update)
        state.final_output = await synthesize_node(state)  # Step 3: Synthesize
        return state
```

#### Graph Flow

```
START → plan → execute ⇄ (loop if more steps) → synthesize → END
```

#### State

The `SupervisorState` carries:
- `task` — the original user request
- `plan` — list of `PlanStep` objects (id, description, agent, status, output)
- `results` — dict of step_id → output text
- `handoffs` — list of `HandoffRecord` (latency, success, payload sizes)
- `final_output` — the synthesized result

### 5. LLM Backend (`llm/`)

Provides a uniform `LLMBackend` interface:

```python
class LLMBackend(ABC):
    async def generate(self, prompt, *, system=None, max_tokens=1024, temperature=0.7) -> LLMResponse:
        ...
```

Two implementations:
- `MockLLM` — deterministic, template-based, no dependencies
- `OpenAIBackend` — real OpenAI Chat Completions API

Selected via `LLM_BACKEND` environment variable. The factory is in `llm/base.py:get_llm()`.

## Data Flow: End-to-End Example

For the task *"Research multi-agent AI and write a blog post"*:

1. **Supervisor receives task**
   - `SupervisorState.task = "Research multi-agent AI and write a blog post"`

2. **Plan node**
   - LLM decomposes into:
     - Step 0: `[research] Research multi-agent AI systems`
     - Step 1: `[writing] Write a blog post about the findings`
   - `state.plan = [PlanStep(0, ...), PlanStep(1, ...)]`

3. **Execute node (step 0)**
   - `A2AAdapter.call_agent(RESEARCH, "Research multi-agent AI systems")`
   - A2A client sends `tasks/send` to `http://localhost:8001`
   - Research agent processes, returns task with artifact
   - `state.results[0] = "## Research Findings\n..."`
   - `state.handoffs = [HandoffRecord(step=0, agent=research, latency=120ms)]`

4. **Execute node (step 1)**
   - Input includes context from step 0
   - `A2AAdapter.call_agent(WRITING, "...with context...")`
   - A2A client sends to `http://localhost:8002`
   - Writer crew runs 3 agents (strategist → writer → editor)
   - `state.results[1] = "# Multi-Agent AI\n## Introduction\n..."`
   - `state.handoffs.append(HandoffRecord(step=1, agent=writing, latency=340ms))`

5. **Synthesize node**
   - LLM merges both results into final output
   - `state.final_output = "..."`

6. **Return state** to caller

## Interop Metrics

Every A2A handoff is instrumented:

```python
@dataclass
class HandoffRecord:
    step_id: int
    agent: AgentType
    agent_url: str
    task_id: str | None
    latency_ms: float        # wall-clock time for the A2A round-trip
    success: bool
    error: str | None
    request_size: int        # bytes in the request
    response_size: int       # bytes in the response
```

These records feed the four evaluation metrics. The latency is the true interop overhead — it includes:
- JSON-RPC serialization
- HTTP transport
- Task lifecycle management
- Agent execution (LLM + tools)

## Scalability

Each agent runs as an independent HTTP service. To scale:
- Run multiple instances behind a load balancer
- Use the A2A registry pattern (stretch goal) for dynamic discovery
- The supervisor is stateless between tasks — scale horizontally

## Security Considerations

For production deployment:
- Add authentication to A2A endpoints (API keys, mTLS)
- Validate and sanitize all task inputs
- Rate-limit per-client
- Use HTTPS in production
- The current implementation is designed for local/development use
