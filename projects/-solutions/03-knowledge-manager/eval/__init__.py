"""Eval harness — metrics + driver.

Implements the four metrics from the README rubric:

1. Retrieval precision@5  — does the hybrid retriever return the right docs?
2. Entity extraction F1    — do extracted entities match the hand-labeled set?
3. Provenance accuracy     — does every cited source actually support the claim?
4. Latency p95             — query latency, 95th percentile

The harness loads `eval/data/qa/qa_pairs.jsonl` (35 Q&A pairs with expected
source docs) and `eval/data/labels/labels.jsonl` (20 hand-labeled entity
sets). Both files are produced by `eval/generate_dataset.py`.
"""
