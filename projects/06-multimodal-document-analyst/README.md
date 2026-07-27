# Project 06 - Multimodal document analyst

Difficulty: ⭐⭐⭐
Estimated time: 2-3 weeks
Status: spec

## Problem

Given a PDF with text, images, tables, and charts, produce a structured report answering user questions, with each answer grounded in a specific page and element (text block, image, table cell). The system must handle heterogeneous content and provide element-level citations.

This project exercises multimodal ingestion (text + images + tables), multimodal retrieval, and structured output with fine-grained citations. It is the canonical "multimodal" project.

## Architecture

1. Ingestion: PDF parsed per-page, with layout-aware extraction separating text, images, and tables.
2. Indexing: text embedded for vector search; images captioned (via a VLM) and captions embedded; tables structured as JSON.
3. Retrieval agent: LangGraph with multimodal retrieval - vector search on text and captions, plus structured queries on tables.
4. Response: structured answer with element-level citations (page N, element M).

## Stack

- Orchestration: LangGraph 0.2.x
- Ingestion: LlamaParse or Unstructured
- VLM: GPT-4o vision or Claude vision (for image captioning)
- Storage: Postgres + pgvector
- MCP: retrieval tool server
- Observability: LangSmith

## Eval rubric

| Metric | Target | How measured |
|--------|--------|--------------|
| Citation precision | 90%+ | Citations point to the correct page and element |
| Table extraction accuracy | 85%+ | Cells extracted correctly on a held-out set |
| Image caption accuracy | 80%+ | LLM-as-judge on caption quality |
| Query latency p95 | under 10s | Wall-clock |
| Cost per document | under $0.50 | Sum of LLM call costs |

## Datasets

- 20 PDFs with mixed content (text, images, tables, charts)
- Hand-labeled element boundaries for 5 PDFs
- 30 questions with expected answer sources

## Stretch goals

- Handle scanned PDFs (OCR)
- Handle multi-document queries (compare across PDFs)
- Handle charts (extract data points from chart images)

## References

- [LlamaParse](https://www.llamaindex.ai/llamaparse) - production ingestion
- [Unstructured](https://github.com/Unstructured-IO/unstructured) - open-source ingestion
- Real job postings: search "AI engineer" + "document" + "multimodal" on builtin.com

## Solution

Reference solution: [projects/-solutions/06-multimodal-document-analyst/](-solutions/06-multimodal-document-analyst/) (coming soon). Build your own first.
