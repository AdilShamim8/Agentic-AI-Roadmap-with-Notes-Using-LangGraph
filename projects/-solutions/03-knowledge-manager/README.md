# Personal Knowledge Manager

A self-contained, end-to-end implementation of the **Project 03 — Personal Knowledge Manager** spec from [AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects](https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects/tree/main/projects/03-knowledge-manager).

> Dump notes, web clips, and PDFs into a system and have it surface the right thing at the right time, organized by concept — with every answer linking back to its source.

This project implements the canonical "memory" pattern from the Agentic AI roadmap:

- **RAG** (retrieval over the knowledge base)
- **Graph memory** (entities + relationships)
- **Multi-modal ingestion** (PDF / HTML / Markdown / plain text)
- **Provenance** (every claim links to a source)
- **MCP** tool server (so other agents can query your KB)
- **LangSmith** observability hooks

---

## Architecture

```
┌────────────────┐     ┌──────────────┐     ┌────────────────┐
│ PDF / MD / HTML│ ──▶ │   Ingestion  │ ──▶ │   Extractor    │
│  / TXT files   │     │ (loader +    │     │ (LLM: entities │
└────────────────┘     │  chunker +   │     │ + relations)   │
                       │  embedder)   │     └────────┬───────┘
                       └──────┬───────┘              │
                              │                      │
              ┌───────────────┴──────────┐           │
              ▼                          ▼           ▼
        ┌──────────┐              ┌────────────┐  ┌─────────┐
        │  SQLite  │              │ sqlite-vec │  │NetworkX │
        │ (chunks, │              │  (vector   │  │ (entity │
        │  docs)   │              │   index)   │  │  graph) │
        └────┬─────┘              └─────┬──────┘  └────┬────┘
             │                          │              │
             │                          ▼              │
             │              ┌───────────────────┐      │
             │              │ Hybrid retrieval  │◀─────┘
             │              │ (vector ∪ graph)  │
             │              └─────────┬─────────┘
             │                        │
             │                        ▼
             │              ┌───────────────────┐
             └─────────────▶│  LangGraph agent  │
                            │  retrieve → synth │
                            └─────────┬─────────┘
                                      │
                                      ▼
                            ┌───────────────────┐
                            │ Answer + citation │
                            │   provenance      │
                            └───────────────────┘
```

### Pipeline

1. **Ingestion pipeline** — `knowledge_manager/ingestion/`
   - `loader.py` — PDF (pypdf), HTML (BeautifulSoup), Markdown (markdown), TXT
   - `chunker.py` — recursive character splitter with overlap
   - `pipeline.py` — orchestrates load → chunk → embed → extract → index
2. **Extraction** — `knowledge_manager/ingestion/extractor.py`
   - LLM prompt returns strict JSON with `entities[]` + `relationships[]`
   - Canonical entity kinds: person, place, concept, org, date, other
3. **Indexing** — `knowledge_manager/storage/`
   - `db.py` — SQLite schema (documents, chunks, entities, relationships, mentions)
   - `vector_store.py` — sqlite-vec virtual table for ANN search
   - `graph_store.py` — NetworkX DiGraph serialized to pickle
4. **Retrieval agent** — `knowledge_manager/retrieval/` + `knowledge_manager/agent/`
   - Vector search + graph traversal fused 0.6/0.4 by default
   - LangGraph state machine: `retrieve → synthesize → END`
5. **Response with provenance** — every claim carries `[n]` citations mapped back to source chunks

### Stretch goals (implemented)

- **Zettelkasten note linking** — `knowledge_manager/zettelkasten/linker.py`
  - Suggests note-to-note links via shared-entity Jaccard + embedding cosine
- **MCP tool server** — `knowledge_manager/mcp/server.py`
  - Exposes `search_kb`, `ask_agent`, `get_chunk`, `get_document`, `list_entities`, `get_entity_neighbors`
- **Eval harness** — `eval/`
  - 4 metrics from the rubric: precision@5, entity F1, provenance accuracy, latency p95
  - 53 sample documents + 20 hand-labeled entity sets + 35 Q&A pairs
- **LangSmith tracing** — wire `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` in `.env`

---

## Quick start

```bash
# 1. Install
pip install -r requirements.txt
pip install -e .

# 2. Configure
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...

# 3. Ingest the sample dataset (53 docs in MD/HTML/PDF)
make ingest-eval

# 4. Ask a question
make ask Q="Who designed the Bombe?"

# 5. Launch the Streamlit UI
make ui
# → http://localhost:8501

# 6. Run the eval harness
make eval
```

### Smoke test without OpenAI

The eval harness has a `--stub` flag that uses BM25-style retrieval (no LLM
calls) so you can verify the data plumbing without burning tokens:

```bash
# Ingest all 53 sample docs using FAKE embeddings (no OpenAI key needed)
python scripts/ingest_stub.py eval/data/documents

# Run the eval harness in stub mode
python eval/run_eval.py --stub
```

In stub mode, retrieval precision@5 is still meaningful (BM25 token overlap);
entity F1 will be 0% (no LLM extraction); provenance will be partial (top-1
BM25 hit only); latency will be near zero. With a real `OPENAI_API_KEY` set
and `make ingest-eval` run, all four metrics should hit their targets.

---

## Project layout

```
03-knowledge-manager/
├── README.md                      ← this file
├── requirements.txt
├── pyproject.toml
├── Makefile
├── .env.example
├── .gitignore
├── app.py                         ← Streamlit UI (chat / ingest / graph / notes / status)
│
├── knowledge_manager/
│   ├── __init__.py
│   ├── config.py                  ← settings (env vars, paths)
│   ├── llm.py                     ← OpenAI client wrapper
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py                  ← SQLite schema + connection
│   │   ├── vector_store.py        ← sqlite-vec ANN search
│   │   └── graph_store.py         ← NetworkX entity graph
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── loader.py              ← PDF / HTML / MD / TXT loaders
│   │   ├── chunker.py             ← recursive text splitter
│   │   ├── extractor.py           ← LLM entity + relationship extractor
│   │   └── pipeline.py            ← end-to-end ingest
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── vector_search.py       ← embed + ANN search
│   │   ├── graph_traversal.py     ← entity spotter + BFS
│   │   └── hybrid.py              ← fused retrieval
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── prompts.py             ← synthesis prompt with citation rules
│   │   └── graph.py               ← LangGraph state machine
│   ├── zettelkasten/
│   │   ├── __init__.py
│   │   └── linker.py              ← note-to-note suggestions
│   └── mcp/
│       ├── __init__.py
│       └── server.py              ← FastMCP tool server
│
├── scripts/
│   ├── ingest.py                  ← km-ingest <dir>
│   ├── ask.py                     ← km-ask "question"
│   ├── graph_show.py              ← km-graph (print entity graph)
│   └── reset_db.py                ← km-reset --yes
│
├── eval/
│   ├── __init__.py
│   ├── generate_dataset.py        ← builds 53 docs + 20 labels + 35 Q&A
│   ├── metrics.py                 ← precision@5, F1, provenance, latency
│   ├── agent_stub.py              ← no-LLM stub for offline eval
│   ├── run_eval.py                ← main eval driver
│   ├── README.md                  ← eval docs
│   └── data/
│       ├── documents/             ← 53 sample docs (md/html/pdf)
│       ├── labels/labels.jsonl    ← 20 hand-labeled entity sets
│       ├── qa/qa_pairs.jsonl      ← 35 Q&A pairs with expected sources
│       └── manifest.json          ← dataset manifest
│
├── tests/
│   ├── test_storage.py            ← SQLite + sqlite-vec + NetworkX
│   ├── test_chunker.py            ← text chunking
│   ├── test_loaders.py            ← PDF/HTML/MD/TXT loaders
│   └── test_retrieval.py          ← vector search + zettelkasten
│
└── data/
    ├── ingest/                    ← drop folder for your own files
    └── db/                        ← SQLite DB + graph pickle (auto-created)
```

---

## Eval rubric

| Metric | Target | How measured | Where |
|---|---|---|---|
| Retrieval precision@5 | ≥ 80% | hybrid retriever returns ≥1 expected source in top-5 | `eval/metrics.py::retrieval_precision_at_k` |
| Entity extraction F1 | ≥ 85% | macro-F1 over (name, kind) pairs vs hand-labeled set | `eval/metrics.py::entity_f1` |
| Provenance accuracy | 100% | every cited source is one of the expected source files | `eval/metrics.py::provenance_accuracy` |
| Indexing latency | < 30s / doc | wall-clock during `ingest_directory` | `IngestionReport.elapsed_s / n_files` |
| Query latency p95 | < 5s | wall-clock, 95th percentile over Q&A set | `eval/metrics.py::latency_p95` |

Run with: `make eval` (or `python eval/run_eval.py`).

---

## Using the MCP server

The MCP server exposes your KB to other AI agents (Claude Desktop, Cursor, custom LangGraph agents):

```bash
make mcp   # or: python -m knowledge_manager.mcp.server
```

Tools exposed:
- `search_kb(query, top_k=5)` — hybrid retrieval
- `ask_agent(question)` — full LangGraph agent with provenance
- `get_chunk(chunk_id)` — fetch a chunk
- `get_document(doc_id)` — fetch document metadata + chunk list
- `list_entities(kind=None)` — list entities
- `get_entity_neighbors(entity_id, depth=2)` — BFS over the entity graph

To connect from Claude Desktop, add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "knowledge-manager": {
      "command": "python",
      "args": ["-m", "knowledge_manager.mcp.server"],
      "cwd": "/path/to/03-knowledge-manager"
    }
  }
}
```

---

## Configuration

All settings live in `.env` (copy from `.env.example`):

| Var | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | — | **required** |
| `OPENAI_CHAT_MODEL` | `gpt-4o` | synthesis + extraction |
| `OPENAI_EMBED_MODEL` | `text-embedding-3-small` | 1536-dim |
| `OPENAI_EMBED_DIM` | `1536` | must match the embed model |
| `LANGSMITH_TRACING` | (blank) | `true` to enable |
| `LANGSMITH_API_KEY` | — | required if tracing on |
| `LANGSMITH_PROJECT` | `knowledge-manager` | |
| `KM_DB_PATH` | `data/db/knowledge.db` | SQLite DB |
| `KM_GRAPH_PATH` | `data/db/graph.pkl` | NetworkX pickle |
| `KM_INGEST_DIR` | `data/ingest` | drop folder |
| `KM_VECTOR_TOP_K` | `5` | retrieval k |
| `KM_GRAPH_DEPTH` | `2` | BFS hops |
| `KM_CHUNK_SIZE` | `800` | chunker target |
| `KM_CHUNK_OVERLAP` | `120` | chunker overlap |

---

## Switching storage backends

The default storage is **self-contained** (SQLite + sqlite-vec + NetworkX
pickle) so the project runs without external services. If you want to swap in
the spec-faithful stack (Postgres + pgvector + Neo4j), the storage boundary
is exactly three files:

- `knowledge_manager/storage/db.py` — connection + schema
- `knowledge_manager/storage/vector_store.py` — `upsert_many` + `search`
- `knowledge_manager/storage/graph_store.py` — `add_entity`, `neighbors`, etc.

Replace those three with Postgres/Neo4j implementations and the rest of the
codebase (ingestion, retrieval, agent, MCP, UI) works unchanged.

---

## Design notes

### Why LangGraph?

The retrieval → synthesize flow is naturally a state machine with branching
(parallel vector + graph retrieval) and shared state. LangGraph 0.2's
`StateGraph` makes this explicit and traceable; LangSmith then visualises
each node's inputs and outputs.

### Why sqlite-vec?

The README spec lists Postgres + pgvector, but requiring Postgres for a
personal knowledge manager is overkill for most users. sqlite-vec is a
loadable SQLite extension that delivers ANN search in a single file, with
the same `MATCH ... ORDER BY distance` query semantics as pgvector. Backups
become a `cp` instead of a `pg_dump`.

### Why NetworkX for the graph?

Same reasoning. Apache AGE and Neo4j are production-grade, but for a
single-user KB the graph fits comfortably in memory (a few thousand nodes
/ edges) and serialises to a 100KB pickle. The on-disk source of truth is
the `entities` + `relationships` SQLite tables; the pickle is a rebuildable
query cache.

### Provenance design

Every chunk stored in `chunks` has a `(doc_id, position, char_start,
char_end)` tuple. When the agent synthesises an answer, it is forced by the
system prompt to cite every claim with `[n]`, and the parser in
`agent/graph.py` validates that every `[n]` maps to a real source id. The
UI surfaces these as clickable provenance entries with `path`, `title`,
`position`, and `score`.

### Hybrid retrieval fusion

The default weights are `w_vector=0.6, w_graph=0.4`. Vector search gets the
edge because it directly measures query-document similarity, while graph
traversal measures entity overlap (which can be noisy with imperfect entity
extraction). Both scores are in `[0, 1]` so the weighted sum is comparable.
The same chunk appearing in both retrievers keeps its max score per
retriever.

---

## Testing

```bash
make test
```

Runs:
- `tests/test_storage.py` — SQLite schema, sqlite-vec upsert/search, NetworkX graph ops
- `tests/test_chunker.py` — chunking behaviour (empty, short, long, positions)
- `tests/test_loaders.py` — PDF/HTML/MD/TXT loaders, file discovery
- `tests/test_retrieval.py` — vector search end-to-end, Zettelkasten linker

---

## FAQ

**Q: I get `sqlite3.OperationalError: ... vec0`** — make sure `sqlite-vec`
is installed (`pip install sqlite-vec`). The `db.py` module loads it as a
SQLite extension at connection time.

**Q: How do I reset the KB?** — `make reset` (or `python scripts/reset_db.py --yes`).

**Q: Can I use a different LLM?** — Replace `knowledge_manager/llm.py` with
your provider's LangChain wrapper. The rest of the code calls `get_llm()` /
`get_embeddings()` and is provider-agnostic.

**Q: Does it work offline?** — Vector search, graph traversal, chunking,
loaders, and the eval harness (`--stub` flag) all work offline. Only the
agent's synthesize step and the LLM-based entity spotter require an OpenAI
call.

---

## License

MIT. See the upstream repo for the original spec.
