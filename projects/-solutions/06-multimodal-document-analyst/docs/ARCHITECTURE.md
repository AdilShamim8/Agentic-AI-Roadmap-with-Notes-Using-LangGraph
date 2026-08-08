# Architecture

## Pipeline

```
PDF
  │
  ▼
PDFIngester (PyMuPDF)             ◀── ingest/pdf_ingester.py
  │   for each page:
  │     1. render to PNG               (used by UI + as OCR fallback)
  │     2. detect tables               (rectangle clustering)
  │     3. extract text blocks         (skip those overlapping a table)
  │     4. extract embedded images     (PNG)
  │   → writes JSON cache: .data/pdf_cache/<doc_id>.json
  ▼
Indexer                             ◀── storage/indexer.py
  │   1. for each IMAGE element: caption via VLM (z-ai / openai)
  │   2. upsert text+table elements → ChromaDB doc_text
  │   3. upsert image captions     → ChromaDB doc_captions
  │   4. upsert summary            → SQLite documents table
  ▼
Retrieval (LangGraph)              ◀── agents/retrieval_agent.py
  │   retrieve node:
  │     - vector search on doc_text     (text blocks + tables)
  │     - vector search on doc_captions (image captions)
  │     - merge & de-duplicate by element_id
  │   synthesize node:
  │     - LLM (json_mode) emits {summary, blocks, citations}
  │     - validate citation ids against retrieved set
  │     - fallback path on LLM failure: top-1 retrieval as the answer
  ▼
Answer {summary, blocks[], citations[], confidence, latency_ms}
```

## Key design choices

### 1. Stable element ids

Every element gets an id of the form `<doc_id>::p<page>::e<element_index>`.
This id is:
- the ChromaDB row id,
- the citation id passed to the LLM,
- the lookup key the API/UI uses to fetch the cited page PNG.

So a citation flows end-to-end without any translation.

### 2. Pluggable providers

`VLMClient` (vlm.py) and `EmbeddingClient` (embeddings.py) are abstract
bases with two adapters each (`zai`, `openai`). The factory reads
`settings.vlm_provider` / `settings.embedding_provider` and returns the
right adapter. No other module knows which provider is in use.

### 3. Two ChromaDB collections, not three

Tables are stored as TEXT rows in `doc_text` (serialised via
`_table_to_text`). This is deliberate: a single vector search returns
both text blocks and tables, ranked together. The retriever then splits
the hits by `element_type` if the caller wants tables only.

### 4. LangGraph with two nodes

The graph is intentionally small (`retrieve → synthesize → END`). The
value of using LangGraph over a plain async function is:

- future extensibility (add a `rewrite_query` node, a `critique` loop,
  a `route_to_table_lookup` conditional edge),
- built-in state persistence (`AgentState` is a Pydantic model, so it
  serialises cleanly),
- LangSmith tracing picks up the graph automatically when
  `LANGCHAIN_TRACING_V2=true`.

### 5. Storage layout

```
.data/
├── chroma/            ← ChromaDB persistent index
│   ├── doc_text/
│   └── doc_captions/
├── pdf_cache/         ← JSON dump of every ingested doc
│   └── <doc_id>.json
├── page_images/       ← rendered page PNGs + extracted image PNGs
│   ├── <doc_id>_p1.png
│   ├── <doc_id>_p1_img0.png
│   └── ...
└── documents.db       ← SQLite registry of ingested docs
```

`doc_id` is `short_id(sha256(pdf_bytes))`, so re-ingesting the same PDF
is idempotent — the cache and the index are simply overwritten.
