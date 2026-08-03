# 🔎 Research Agent

An autonomous research agent, built as **Project 01** of the
[Agentic AI Roadmap](https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-Using-LangGraph).

Give it a topic. It plans sub-questions, searches the web (and any local
documents you hand it), synthesizes what it finds into a cited report,
critiques its own draft for gaps, does another research pass if needed,
and writes out a finished Markdown report — all orchestrated as a
[LangGraph](https://github.com/langchain-ai/langgraph) state graph with a
genuine reflection loop, not just a straight-line pipeline.

```
$ python cli.py "The impact of quantum computing on cryptography"

Researching: The impact of quantum computing on cryptography
provider=anthropic · max_results=4 · max_iterations=2 · engine=auto

  → Loading local documents...
  → Planning sub-questions...
  → Searching...
  → Synthesizing findings...
  → Reviewing for gaps...
  → Compiling final report...

Done in 34.2s.
Sources collected : 11
Sub-questions     : 4
Report written to : reports/the-impact-of-quantum-computing-on-cryptography.md
```

See [`examples/sample_report.md`](examples/sample_report.md) for what a
finished report looks like.

---

## Features

- **Plan → Search → Synthesize → Critique → Refine loop**, built as a real
  LangGraph `StateGraph` with a conditional edge (see
  [`docs/architecture.md`](docs/architecture.md) for the diagram).
- **Numbered, deduplicated citations** — every claim in the report is
  backed by a `[n]` reference that matches a real `## References` entry;
  the same URL always gets the same number, even if it surfaces under
  multiple sub-questions.
- **Self-critique with a bounded refinement loop** — after synthesizing
  answers, the agent judges its own draft, proposes follow-up questions
  if it finds gaps, and runs one more research round (capped by
  `MAX_ITERATIONS` so it always terminates).
- **Web *and* local documents** — pass `--docs report.pdf notes.md` and
  they're treated as first-class sources alongside live web search.
- **Runs with zero API keys** via `--demo` mode, so you can see the whole
  pipeline and report format before wiring up a real provider.
- **Provider-agnostic** — Anthropic, OpenAI, or a local Ollama model,
  switchable with one `.env` line, with no LangChain wrapper required
  (see [Why no LangChain LLM wrapper?](docs/architecture.md)).
- **Free by default** — DuckDuckGo search needs no API key; Tavily is a
  drop-in upgrade if you set `TAVILY_API_KEY`.
- **57 passing unit/integration tests**, all offline — the whole test
  suite runs without a network connection, an API key, or even LangGraph
  installed (see [Testing](#testing)).
- **CLI + optional Streamlit UI**, both built on the same underlying
  package.

## How it works

```
load_documents → plan → search → synthesize → critique ──▶ compile_report
                   ▲                              │
                   └──────────── loop if gaps ─────┘
```

1. **`load_documents`** reads any local `.txt` / `.md` / `.pdf` files you
   supplied — once, up front.
2. **`plan`** asks the LLM to break the topic into a handful of focused
   sub-questions (or, on a refinement round, uses the follow-up
   questions the critique step proposed).
3. **`search`** runs a web search for each sub-question.
4. **`synthesize`** writes a cited answer to each sub-question from the
   search results and local documents.
5. **`critique`** reviews the findings against the original topic and
   decides whether they're sufficient, or what's missing.
6. If gaps were found **and** the iteration budget allows it, the graph
   loops back to `plan` with the follow-up questions. Otherwise, it moves
   on to **`compile_report`**, which assembles the final Markdown report.

Full design rationale — including why the project ships *both* a
LangGraph implementation and a dependency-free runner — is in
[`docs/architecture.md`](docs/architecture.md).

## Project structure

```
research-agent/
├── cli.py                     # command-line entry point
├── app.py                     # optional Streamlit UI
├── research_agent/
│   ├── config.py              # .env / settings loading
│   ├── state.py               # ResearchState + Source/SearchResult/Finding
│   ├── llm.py                 # LLMClient protocol + Anthropic/OpenAI/Ollama/Fake
│   ├── prompts.py              # prompt templates for each reasoning step
│   ├── nodes.py                # plan / search / synthesize / critique / compile
│   ├── engine.py                # dependency-free graph runner (used by tests)
│   ├── graph.py                 # LangGraph StateGraph wiring
│   ├── report.py                # citation registry + Markdown report builder
│   ├── utils.py                 # JSON parsing, chunking, URL normalization, etc.
│   └── tools/
│       ├── web_search.py       # DuckDuckGo / Tavily / Fake search backends
│       ├── fetch.py             # page fetch + readable-text extraction
│       └── documents.py         # local .txt/.md/.pdf loader
├── tests/                      # 57 offline unit + integration tests
├── examples/sample_report.md   # example output
├── docs/architecture.md        # graph diagram + design rationale
├── requirements.txt
├── requirements-dev.txt         # + pytest
├── requirements-ui.txt          # + streamlit
└── .env.example
```

## Setup

```bash
git clone <this-repo-url> research-agent
cd research-agent
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# then edit .env and set:
#   LLM_PROVIDER=anthropic          (or openai / ollama)
#   ANTHROPIC_API_KEY=sk-...        (matching whichever provider you chose)
```

No search API key is required — DuckDuckGo works out of the box. Set
`TAVILY_API_KEY` in `.env` only if you want to switch to Tavily.

### Try it with no setup at all

```bash
python cli.py "Any topic you like" --demo
```

`--demo` uses a fake LLM and fake search results so you can see the CLI,
the step-by-step trace, and the report format before spending an API
call.

## Usage

```bash
# Basic
python cli.py "State of small modular reactors in 2026"

# Choose a provider / model explicitly
python cli.py "Topic" --provider openai --model gpt-4o

# More search depth and more refinement rounds
python cli.py "Topic" --max-results 6 --max-iterations 3

# Include local documents alongside web search
python cli.py "Our Q3 migration plan" --docs notes/plan.pdf notes/meeting.md

# Choose where the report is written
python cli.py "Topic" --output reports/my_report.md

# Force the plain-Python engine even if LangGraph is installed
python cli.py "Topic" --engine simple

# See the agent's internal trace as it runs
python cli.py "Topic" -v
```

Run `python cli.py --help` for the full option list.

### Streamlit UI

```bash
pip install -r requirements-ui.txt
streamlit run app.py
```

### Programmatic use

```python
from research_agent.llm import build_llm
from research_agent.tools.web_search import build_search_tool_from_env
from research_agent.graph import build_graph
from research_agent.state import new_state

llm = build_llm("anthropic")
search_tool = build_search_tool_from_env()
app = build_graph(llm, search_tool)

final_state = app.invoke(new_state(topic="The economics of vertical farming"))
print(final_state["report"])
```

## Configuration

All settings can be set in `.env` (see `.env.example`) or overridden via
CLI flags.

| Variable                | Default        | Description                                             |
|--------------------------|-----------------|----------------------------------------------------------|
| `LLM_PROVIDER`           | `anthropic`     | `anthropic` \| `openai` \| `ollama`                       |
| `LLM_MODEL`              | provider default | Model name override                                    |
| `ANTHROPIC_API_KEY`      | —               | Required if `LLM_PROVIDER=anthropic`                      |
| `OPENAI_API_KEY`         | —               | Required if `LLM_PROVIDER=openai`                          |
| `OLLAMA_HOST`            | `http://localhost:11434` | Used if `LLM_PROVIDER=ollama`                    |
| `TAVILY_API_KEY`         | —               | Optional — switches search backend from DuckDuckGo to Tavily |
| `MAX_RESULTS_PER_QUERY`  | `4`             | Search results fetched per sub-question                   |
| `MAX_ITERATIONS`         | `2`             | Max plan→search→synthesize→critique rounds                |
| `USE_LANGGRAPH`          | `true`          | Set `false` to always use the plain-Python engine          |

## Testing

The entire test suite is offline: it uses `FakeLLM` and `FakeSearch`
stand-ins (see `research_agent/llm.py` and
`research_agent/tools/web_search.py`), so it needs no API key, no
network access, and — because the tests exercise `engine.py` rather than
`graph.py` — not even LangGraph installed.

```bash
# stdlib, no extra install required
python -m unittest discover -s tests -v

# or, if you installed requirements-dev.txt
pytest tests/ -v
```

57 tests cover: JSON-parsing robustness against messy LLM output, URL
normalization and citation deduplication, Markdown report assembly, the
local document loader, HTML text extraction, every node function in
isolation, the routing logic that prevents infinite refinement loops,
and full end-to-end runs (single-round, multi-round, and
iteration-capped).

## Notes on this build

I wasn't able to load the exact original README for this project from
GitHub in the environment this was built in (automated access to
`github.com` is blocked by robots.txt, and the repository referenced
appears to have since been renamed). This implementation was built from
the project's stated purpose — a LangGraph-based research agent that
searches the web and documents, synthesizes findings, and compiles a
cited report — confirmed via the roadmap's own project index. If your
copy of the original spec calls for something structurally different,
let me know what to adjust.

## License

MIT — see [`LICENSE`](LICENSE).
