# Customer Support Multi-Agent System

A production-style multi-agent customer support system built with
**LangGraph** + **LangChain**: a supervisor routes each message to a
specialist agent (billing, technical support, order tracking, or general
FAQ), each with its own tools, backed by a small mock CRM/orders/invoices
dataset and a TF-IDF-searchable knowledge base. Angry or explicitly
human-seeking customers get escalated straight to a support ticket.

Runs with **zero API keys** in mock mode (deterministic, template-based
responses built on the exact same business logic and tools a real LLM
agent would use), and upgrades automatically to real, tool-calling Claude
or GPT agents the moment you add a key to `.env`.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design write-up and a
diagram of the graph.

## Features

- 🧭 **Supervisor + 4 specialist agents** - billing, technical support, order
  tracking, general FAQ - each with its own tools and system prompt.
- 😠 **Sentiment/urgency detection** - upset customers or explicit "let me
  talk to a human" requests are escalated immediately, bypassing the bot.
- 🔁 **Self-review loop** - a `reviewer` node escalates to a human ticket
  whenever a specialist couldn't actually resolve the issue (e.g. an order
  ID that doesn't exist).
- 📚 **Local RAG** - TF-IDF search over markdown knowledge base articles, no
  vector DB or embeddings API required.
- 🧠 **Per-conversation memory** - LangGraph's checkpointer persists state
  per `thread_id`, so multi-turn conversations remember the customer ID,
  category, etc. automatically.
- 🧪 **Runs with zero API keys** - a deterministic mock mode exercises the
  full graph (routing, tools, escalation, memory) for free, offline.
- 🖥️ **Three ways to use it** - CLI chat, FastAPI REST API, Streamlit web UI.
- ✅ **23+ unit/integration tests**, most requiring no dependencies beyond
  `scikit-learn` + stdlib.

## Project structure

```
customer-support-multi-agent/
├── data/                    mock CRM data (JSON) + knowledge base (markdown)
├── core/                    framework-agnostic business logic (billing, orders,
│                            tickets, knowledge base search, intent/sentiment)
├── app/                     LangGraph orchestration: state, tools, agents, graph,
│                            CLI, FastAPI backend
├── streamlit_app.py         chat UI
├── scripts/smoke_test.py    quick end-to-end sanity check
├── tests/                   unit tests (core/) + end-to-end tests (full graph)
├── requirements.txt         full app dependencies
├── requirements-core.txt    minimal deps to run/test only core/
├── Dockerfile / docker-compose.yml
└── .env.example
```

## Step-by-step setup

### 1. Get the code and create a virtual environment

```bash
cd customer-support-multi-agent
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

(If you only want to explore/test the business logic without LangGraph,
`pip install -r requirements-core.txt` is enough - see step 6.)

### 3. Configure environment variables (optional)

```bash
cp .env.example .env
```

Leave `.env` empty to run in **mock mode** (no cost, no key needed - see
`app/llm.py`). To use a real LLM, add one of:

```bash
ANTHROPIC_API_KEY=sk-ant-...
# or
OPENAI_API_KEY=sk-...
```

### 4. Run the smoke test

```bash
python scripts/smoke_test.py
```

You should see five sample conversations routed to the right specialist,
with replies printed to the terminal.

### 5. Talk to it

**CLI:**
```bash
python -m app.cli
```

**FastAPI backend** (docs at `http://localhost:8000/docs`):
```bash
uvicorn app.api:app --reload --port 8000

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Where is my order ORD-5001?"}'
```

**Streamlit UI:**
```bash
streamlit run streamlit_app.py
```

### 6. Run the tests

```bash
pytest -v
```

`tests/test_core_*.py` (23 tests) only need `scikit-learn` and pass with no
API key. `tests/test_graph.py` additionally exercises the full compiled
LangGraph graph end-to-end (routing, tools, escalation, multi-turn memory),
also in mock mode, so it needs `langgraph`/`langchain-core` installed but
still no API key.

### 7. (Optional) Run with Docker

```bash
docker compose up --build
```

Starts the FastAPI backend on `:8000` and the Streamlit UI on `:8501`.

## Example conversations to try

| Message | Routes to | What happens |
|---|---|---|
| `Where is my order ORD-5001?` | order | Looks up live shipping status |
| `I was charged twice, CUST-1001` | billing | Looks up the latest invoice |
| `INV-9002, please refund me` | billing | Processes a refund against that invoice |
| `The app keeps crashing on login` | technical | Searches the KB, opens a ticket if unresolved |
| `What's your return policy?` | general | Answers from the knowledge base |
| `This is unacceptable, I want a manager!!` | escalation | Skips the bot, opens an urgent ticket |

## Design notes

- **Routing is a heuristic, not an LLM call.** Keeps it fast, free, and
  unit-testable; see "Why a heuristic router" in `ARCHITECTURE.md`.
- **`core/` has no LangChain/LangGraph dependency.** Business logic is
  independently testable and reusable regardless of which agent framework
  sits on top.
- **Mock mode and live-LLM mode share the same tools.** The only thing that
  changes when you add an API key is who's deciding when to call them (a
  template vs. a real reasoning LLM) - so behavior stays consistent and
  the mock mode is a faithful stand-in for demos, tests, and CI.

## Next steps / ideas to extend this

- Swap the JSON "database" (`core/db.py`) for a real one (Postgres, etc.)
- Swap the TF-IDF knowledge base search for real embeddings + a vector DB
- Add `interrupt_before=["issue_refund"]` for human-in-the-loop refund
  approval before the tool actually runs
- Persist the LangGraph checkpointer to disk/Postgres instead of in-memory
- Add a real auth layer in front of `app/api.py`
