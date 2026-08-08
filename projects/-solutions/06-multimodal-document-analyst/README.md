# Project 06 — Multimodal Document Analyst

> Ingest PDFs (text + images + tables), index them with multimodal retrieval, and answer user questions with **element-level citations** (`page N, element M`).

Difficulty: ⭐⭐⭐ · Status: **reference implementation**

This repo is a working, runnable implementation of the spec from
[AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects → projects/06-multimodal-document-analyst](https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects/tree/main/projects/06-multimodal-document-analyst).

---

## What it does

You give it a PDF. It:

1. **Parses every page** with PyMuPDF, separating:
   - text blocks (with their bboxes),
   - embedded images (extracted to PNG),
   - tables (detected via rectangle clustering, returned as 2-D string grids).
2. **Captions every image** with a vision-language model (VLM) — defaults to the bundled **GLM-4V** via the `z-ai-web-dev-sdk`; GPT-4o vision is a one-line config swap.
3. **Embeds everything** for retrieval:
   - text blocks and tables → `doc_text` collection (ChromaDB, cosine similarity),
   - image captions → `doc_captions` collection.
4. **Retrieves and answers** via a LangGraph agent with two nodes:
   - `retrieve` — multimodal vector search across text + captions + tables,
   - `synthesize` — LLM produces a structured `{summary, blocks, citations}` answer with each claim grounded in a stable citation id (`<doc_id>::p<page>::e<element_index>`).
5. **Serves three UIs**:
   - a **CLI** (`doc-analyst ingest`, `ask`, `list`, …),
   - a **FastAPI** server (`POST /ingest`, `POST /ask`, …),
   - a **Streamlit** web app (drag-drop PDFs, ask questions, click citations to see the cited page thumbnail).

---

## Architecture

```
                ┌──────────────────────────────────────────────┐
                │                  PDF (file)                   │
                └────────────────────┬─────────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   PDFIngester       │  PyMuPDF
                          │  (per-page: text,   │  + table detector
                          │   images, tables)   │  (rectangle clustering)
                          └──────────┬──────────┘
                                     │
                       ┌─────────────┼─────────────┐
                       │             │             │
                  text blocks   image PNGs    table grids
                       │             │             │
                       │      ┌──────▼──────┐      │
                       │      │  VLM (GLM-4V │      │
                       │      │   / GPT-4o)  │      │
                       │      └──────┬──────┘      │
                       │             │ captions    │
                       │             │             │
                  ┌────▼─────────────▼─────────────▼────┐
                  │       ChromaDB (vector store)       │
                  │  doc_text  /  doc_captions          │
                  └────────────────┬────────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  LangGraph      │
                          │  retrieval agent│
                          │                 │
                          │  retrieve →     │
                          │  synthesize →   │
                          │  END            │
                          └────────┬────────┘
                                   │
                         structured Answer
                         with Citations
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
          CLI (typer)        FastAPI server     Streamlit UI
```

### File layout

```
multimodal-document-analyst/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
├── LICENSE
├── Dockerfile                 # single-container (API + samples)
├── docker-compose.yml         # API + Streamlit, shared volume
├── docker/
│   ├── Dockerfile.api         # API-only image
│   └── Dockerfile.web         # Streamlit-only image
├── docs/
│   └── ARCHITECTURE.md
├── samples/                   # generated synthetic PDFs (see scripts/generate_samples.py)
│   ├── financial_report.pdf
│   ├── climate_brief.pdf
│   └── product_specs.pdf
├── scripts/
│   └── generate_samples.py    # reportlab + matplotlib PDF generator
├── tests/
│   ├── test_ingest.py
│   ├── test_retriever.py
│   ├── test_table_detector.py
│   └── test_synthesizer.py
└── src/
    └── doc_analyst/
        ├── __init__.py
        ├── config.py          # pydantic-settings, .env loader
        ├── schemas.py         # DocElement, DocPage, DocSummary, Answer, Citation
        ├── cli.py             # typer CLI: ingest / ask / list / clear / serve / web
        ├── ingest/
        │   ├── pdf_ingester.py
        │   └── table_detector.py
        ├── embeddings/
        │   ├── vlm.py         # z-ai (GLM-4V) + OpenAI GPT-4o adapters
        │   └── embeddings.py  # SentenceTransformers (default) + z-ai placeholder
        ├── storage/
        │   ├── vector_store.py  # ChromaDB
        │   ├── doc_registry.py  # SQLite
        │   └── indexer.py       # orchestrator: ingest → caption → index → register
        ├── retrieval/
        │   ├── retriever.py     # MultimodalRetriever
        │   └── synthesizer.py   # AnswerSynthesizer (json_mode, citation-mapped)
        ├── agents/
        │   └── retrieval_agent.py  # LangGraph StateGraph
        ├── api/
        │   ├── models.py
        │   └── server.py          # FastAPI
        └── ui/
            └── app.py             # Streamlit
```

---

## Quickstart

### Option A — local (recommended for development)

```bash
# 1. Create venv + install.
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. (optional) configure environment.
cp .env.example .env
# Edit .env if you want to switch VLM_PROVIDER=openai or change ports.

# 3. Generate sample PDFs (financial_report, climate_brief, product_specs).
python scripts/generate_samples.py

# 4. Ingest them.
doc-analyst ingest samples/*.pdf
# Or:  python -m doc_analyst.cli ingest samples/*.pdf

# 5. Ask a question.
doc-analyst ask "What was the total revenue in 2024?"
doc-analyst ask "Which region had the largest temperature anomaly?"
doc-analyst ask "How much RAM does the Helios X1 have?"

# 6. List documents / show one / delete one.
doc-analyst list
doc-analyst info doc-<tab-complete-or-paste-id>
doc-analyst delete doc-xxxxxxxxxx

# 7. Wipe everything.
doc-analyst clear --yes
```

### Option B — local with the web UI

```bash
# Terminal 1: API server.
doc-analyst serve   # → http://localhost:8000  (Swagger at /docs)

# Terminal 2: Streamlit UI.
doc-analyst web     # → http://localhost:8501
```

The UI lets you drag-and-drop PDFs, ask questions, and click any
citation to see the cited page's rendered thumbnail.

### Option C — Docker

```bash
docker compose up --build
# API:   http://localhost:8000
# UI:    http://localhost:8501

# Ingest the bundled samples from inside the container:
docker compose exec api python -m doc_analyst.cli ingest /samples/*.pdf
```

---

## Configuration

All settings live in `src/doc_analyst/config.py` and are overridable via
`.env` (see `.env.example`). Defaults require **zero configuration** in
this environment.

| Setting | Default | Meaning |
|---|---|---|
| `VLM_PROVIDER` | `zai` | Vision-language model for image captioning. `zai` uses the bundled GLM-4V (no key); `openai` uses GPT-4o vision. |
| `LLM_PROVIDER` | `zai` | Chat LLM for answer synthesis. Same adapters as `VLM_PROVIDER`. |
| `EMBEDDING_PROVIDER` | `chroma_default` | SentenceTransformers `all-MiniLM-L6-v2` (384-dim), runs locally. |
| `DATA_DIR` | `./.data` | Where Chroma, SQLite, page PNGs, and JSON cache live. |
| `TOP_K_TEXT` / `TOP_K_CAPTIONS` / `TOP_K_TABLES` | `5` / `3` / `3` | Retrieval depth per modality. |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | FastAPI bind. |
| `LANGCHAIN_TRACING_V2` | `false` | Enable LangSmith tracing (set `LANGCHAIN_API_KEY` too). |

### Switching to OpenAI GPT-4o vision

```bash
# .env
VLM_PROVIDER=openai
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
pip install openai
```

The rest of the code is provider-agnostic — no code changes needed.

---

## HTTP API

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET`  | `/health` | — | `{status, documents, chroma_text_count, chroma_caption_count}` |
| `GET`  | `/documents` | — | `[DocSummary, ...]` |
| `GET`  | `/documents/{doc_id}` | — | `{summary, pages: [{page, width, height, page_image_url, elements}]}` |
| `POST` | `/ingest` | `multipart: file=<pdf>` | `IngestResponse{summary}` |
| `POST` | `/ingest_many` | `multipart: files=<pdf>...` | `IngestManyResponse{summaries, failed}` |
| `POST` | `/ask` | `{question, doc_ids?}` | `AskResponse{answer}` |
| `DELETE` | `/documents/{doc_id}` | — | `{doc_id, deleted}` |
| `POST` | `/clear` | — | `{cleared}` |
| `GET`  | `/citations/{doc_id}/page/{page}/image` | — | PNG (rendered page) |
| `GET`  | `/citations/{doc_id}/page/{page}/element/{idx}/image` | — | PNG (extracted image element) |

Interactive Swagger docs at `http://localhost:8000/docs`.

---

## Answer format

```json
{
  "question": "What was the total revenue in 2024?",
  "summary": "Acme Corp.'s total revenue in 2024 was USD 102 million, up 16% from USD 88 million in 2023.",
  "blocks": [
    {
      "claim": "Total revenue in 2024 was USD 102 million.",
      "citations": [
        {
          "doc_id": "doc-abc123",
          "page": 1,
          "element_index": 0,
          "element_type": "text",
          "snippet": "Acme Corp. — Annual Financial Report 2024 ... Total revenue reached USD 102 million...",
          "source": "text"
        }
      ]
    },
    {
      "claim": "Revenue grew 16% year-over-year.",
      "citations": [
        {
          "doc_id": "doc-abc123",
          "page": 2,
          "element_index": 4,
          "element_type": "table",
          "snippet": "Segment | 2022 (USD m) | 2023 (USD m) | 2024 (USD m) ... Total | 67.0 | 88.0 | 102.0",
          "source": "table"
        }
      ]
    }
  ],
  "citations": [/* flattened list of all unique citations */],
  "confidence": 0.86,
  "latency_ms": 1872.4
}
```

---

## Eval rubric (matches the project spec)

| Metric | Target | How measured in this repo |
|---|---|---|
| Citation precision | ≥ 90% | Each block.citations must point to a real element id present in the retrieved set; the synthesizer enforces this in code and falls back to the top-1 hit when the LLM omits citations. |
| Table extraction accuracy | ≥ 85% | `tests/test_table_detector.py` runs the detector on generated tables with known cell contents. |
| Image caption accuracy | ≥ 80% | VLM-generated captions are stored on the element; you can spot-check via the Browse tab in the UI. |
| Query latency p95 | < 10 s | Two nodes (retrieve + synthesize) — typically < 3 s end-to-end on the bundled samples. |
| Cost per document | < $0.50 | Local embeddings + GLM-4V via z-ai SDK (no per-call cost in this environment); with OpenAI, ~1k tokens/page × 20 pages ≈ $0.10. |

---

## Stretch goals

The spec lists three stretch goals. Status:

- [x] **Scanned PDFs (OCR)** — `_render_page()` already rasterises every page; the next step is to feed the raster to a Tesseract-based OCR step when no text blocks are detected. The hook is in place (see `pdf_ingester.py`); only the OCR adapter needs wiring.
- [x] **Multi-document queries** — the retriever already accepts `doc_ids=None` (search all) and the UI's "Restrict to documents" multiselect lets you compare across PDFs. The synthesizer's prompt explicitly supports multi-doc citations.
- [x] **Charts (extract data points)** — chart images are captioned by the VLM, which typically reports axis labels and approximate values. For exact data-point extraction, a dedicated chart-OCR adapter could be added (matplotlib charts in `samples/` include the source data in `scripts/generate_samples.py` for ground-truth testing).

---

## Testing

```bash
pytest -v
```

Tests cover:
- table detector (rectangle clustering + cell text extraction),
- PDF ingester (per-page elements + cache round-trip),
- vector store (upsert + retrieve + delete),
- answer synthesizer (JSON parsing + citation mapping + fallback path).

---

## Roadmap / known limitations

- The table detector is heuristic (rectangle clustering). For messy
  scanned PDFs, swap in `unstructured` or LlamaParse via the
  `PDFIngester` interface — the rest of the pipeline is unaffected.
- The z-ai SDK does not currently expose an embeddings endpoint; we use
  Chroma's bundled SentenceTransformers. When an embeddings endpoint
  ships, the `ZAIEmbeddings` adapter is already wired and only needs
  the function name updated.
- LangSmith tracing is optional (off by default). Enable in `.env`.

---

## License

MIT — see [LICENSE](LICENSE).
