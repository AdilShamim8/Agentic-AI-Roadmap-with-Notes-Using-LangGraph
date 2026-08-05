# Eval harness

Implements the four metrics from the project README rubric:

| Metric | Target | How measured |
|---|---|---|
| Retrieval precision@5 | ≥ 80% | hybrid retriever returns ≥1 expected source in top-5 |
| Entity extraction F1 | ≥ 85% | macro-F1 over (name, kind) pairs vs hand-labeled set |
| Provenance accuracy | 100% | every cited source is one of the expected source files |
| Indexing latency | < 30s / doc | wall-clock during `ingest_directory` |
| Query latency p95 | < 5s | wall-clock, 95th percentile over Q&A set |

## Files

- `generate_dataset.py` — builds the sample dataset (53 docs + 20 labels + 35 Q&A)
- `metrics.py` — metric implementations
- `run_eval.py` — CLI driver, prints rich table + writes JSON
- `agent_stub.py` — offline stub for `--stub` mode (no OpenAI calls)
- `data/documents/` — 53 sample docs (mix of .md / .html / .pdf)
- `data/labels/labels.jsonl` — 20 hand-curated entity + relationship sets
- `data/qa/qa_pairs.jsonl` — 35 Q&A pairs with expected source filenames

## Running

```bash
# 0. Make sure the sample dataset is generated
python eval/generate_dataset.py

# 1. Ingest it (so the retriever has something to query)
make ingest-eval

# 2. Run the full eval (requires OPENAI_API_KEY)
make eval

# OR: stub mode (no OpenAI calls — vector-only retrieval + empty provenance)
python eval/run_eval.py --stub --no-qa

# OR: skip the Q&A-dependent metrics (provenance, latency)
python eval/run_eval.py --no-qa
```

## Output

The harness prints a rich table to stdout and writes a JSON snapshot to
`eval/out/<timestamp>.json` containing:

```json
{
  "started_at": "...",
  "retrieval_precision@5": 0.8571,
  "retrieval_detail": [...],
  "entity_f1": 0.72,
  "entity_detail": [...],
  "provenance_accuracy": 0.94,
  "provenance_detail": [...],
  "query_latency_p95_s": 3.42,
  "latency_samples": [...],
  "finished_at": "..."
}
```

## Regenerating the dataset

```bash
python eval/generate_dataset.py
```

This is idempotent — re-running overwrites the same files deterministically
(`random.seed(42)` is set at module top).

## Adding your own Q&A pairs

Append a line to `data/qa/qa_pairs.jsonl`:

```json
{"id": 36, "question": "...", "expected_sources": ["file1.md", "file2.html"], "expected_answer_summary": "..."}
```

`expected_sources` is a list of **filenames** (basename only). The precision@5
metric treats the QA as "hit" if any of the expected source filenames appears
in the top-5 retrieved chunk paths.
