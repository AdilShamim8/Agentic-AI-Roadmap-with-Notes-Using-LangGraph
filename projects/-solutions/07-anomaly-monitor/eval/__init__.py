"""Eval framework for anomaly-monitor.

Precision / recall / latency / response-correctness rubric, an LLM-as-judge
for response appropriateness, and a CLI (``python -m eval.run_eval``) that
replays a JSONL data file through the pipeline and scores it.
"""
