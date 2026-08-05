"""Metric implementations."""
from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Iterable

from knowledge_manager.storage.db import get_conn

LABELS_PATH = Path(__file__).resolve().parent / "data" / "labels" / "labels.jsonl"
QA_PATH = Path(__file__).resolve().parent / "data" / "qa" / "qa_pairs.jsonl"


# --------------------------------------------------------------------------
# Loading helpers
# --------------------------------------------------------------------------


def load_labels() -> list[dict]:
    out = []
    with LABELS_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_qa() -> list[dict]:
    out = []
    with QA_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# --------------------------------------------------------------------------
# 1. Retrieval precision@5
# --------------------------------------------------------------------------


def retrieval_precision_at_k(
    retriever, qa_pairs: list[dict], k: int = 5
) -> tuple[float, list[dict]]:
    """For each Q&A pair, run `retriever(question, top_k=k)` and check whether
    any of the `expected_sources` filenames appear in the top-k retrieved
    chunks' paths. Returns (precision, per_question_detail)."""
    n_correct = 0
    details = []
    for qa in qa_pairs:
        hits = retriever(qa["question"], top_k=k)
        retrieved_paths = {Path(h.path).name for h in hits}
        expected = set(qa["expected_sources"])
        hit = bool(retrieved_paths & expected)
        if hit:
            n_correct += 1
        details.append(
            {
                "id": qa["id"],
                "question": qa["question"],
                "expected": sorted(expected),
                "retrieved": sorted(retrieved_paths),
                "hit": hit,
            }
        )
    return n_correct / max(1, len(qa_pairs)), details


# --------------------------------------------------------------------------
# 2. Entity extraction F1
# --------------------------------------------------------------------------


def _entity_key(name: str, kind: str) -> tuple[str, str]:
    return (name.strip().lower(), (kind or "other").strip().lower())


def _extracted_entities_for(doc_files: list[str]) -> set[tuple[str, str]]:
    """Return the set of (name, kind) tuples extracted for the given doc paths."""
    if not doc_files:
        return set()
    placeholders = ",".join("?" * len(doc_files))
    out: set[tuple[str, str]] = set()
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT DISTINCT e.name, e.kind FROM entities e "
            f"JOIN documents d ON d.id = e.doc_id "
            f"WHERE d.path LIKE ? OR d.path IN ({placeholders})",
            (f"%{doc_files[0]}%", *doc_files),
        ).fetchall()
        # The above query is conservative; do a second pass that matches by
        # basename to handle the case where stored path is absolute/relative.
        rows2 = conn.execute(
            "SELECT DISTINCT e.name, e.kind FROM entities e JOIN documents d ON d.id = e.doc_id"
        ).fetchall()
    for r in rows2:
        # path basename match
        # need to re-resolve from DB; the rows2 doesn't have path. Redo properly:
        pass
    # Do it properly: fetch entities joined with the doc path basename.
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT e.name, e.kind, d.path FROM entities e JOIN documents d ON d.id = e.doc_id"
        ).fetchall()
    target = set(doc_files)
    for r in rows:
        if Path(r["path"]).name in target:
            out.add(_entity_key(r["name"], r["kind"]))
    return out


def entity_f1(labels: list[dict]) -> tuple[float, list[dict]]:
    """Compute macro-averaged F1 over (name, kind) pairs across labeled docs."""
    f1s = []
    details = []
    for entry in labels:
        gold = {_entity_key(e["name"], e["kind"]) for e in entry["entities"]}
        pred = _extracted_entities_for([entry["file"]])
        tp = len(gold & pred)
        fp = len(pred - gold)
        fn = len(gold - pred)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        f1s.append(f1)
        details.append(
            {
                "file": entry["file"],
                "title": entry["title"],
                "gold_n": len(gold),
                "pred_n": len(pred),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            }
        )
    return statistics.mean(f1s) if f1s else 0.0, details


# --------------------------------------------------------------------------
# 3. Provenance accuracy
# --------------------------------------------------------------------------


def provenance_accuracy(asker, qa_pairs: list[dict]) -> tuple[float, list[dict]]:
    """For each Q&A, ask the agent and check that every cited source is one
    of the expected source files. (We do NOT verify claim-level support;
    that requires an LLM-as-judge, which we add as an optional pass below.)
    """
    n_ok = 0
    details = []
    for qa in qa_pairs:
        resp = asker(qa["question"])
        expected = set(qa["expected_sources"])
        cited_paths = {Path(p["path"]).name for p in resp.provenance}
        if not cited_paths:
            # No citations — fail.
            ok = False
        else:
            ok = cited_paths.issubset(expected) or bool(cited_paths & expected)
        if ok:
            n_ok += 1
        details.append(
            {
                "id": qa["id"],
                "question": qa["question"],
                "answer_len": len(resp.answer),
                "cited": sorted(cited_paths),
                "expected": sorted(expected),
                "ok": ok,
                "elapsed_s": round(resp.elapsed_s, 3),
            }
        )
    return n_ok / max(1, len(qa_pairs)), details


# --------------------------------------------------------------------------
# 4. Query latency p95
# --------------------------------------------------------------------------


def latency_p95(asker, qa_pairs: list[dict]) -> tuple[float, list[float]]:
    times = []
    for qa in qa_pairs:
        resp = asker(qa["question"])
        times.append(resp.elapsed_s)
    if not times:
        return 0.0, []
    times_sorted = sorted(times)
    # p95 via nearest-rank method
    n = len(times_sorted)
    idx = max(0, min(n - 1, int(0.95 * n) - 1))
    return times_sorted[idx], times


# --------------------------------------------------------------------------
# Optional: LLM-as-judge for provenance claim-level support
# --------------------------------------------------------------------------


_JUDGE_PROMPT = """You are a strict judge of citation accuracy.

You will be given:
1. A user question.
2. An answer with numbered citations like [1].
3. A list of sources, each with an id, a title, and a passage.

For EACH citation [n] in the answer, decide whether the cited source's
passage actually supports the claim it is attached to. Return STRICT JSON:

  {"citations": [{"id": 1, "supported": true|false, "reason": "..."}, ...]}

A citation is "supported" if reading the source passage gives reasonable
evidence for the claim. Be strict but fair.
"""


def judge_provenance(question: str, answer: str, sources: list[dict]) -> dict:
    """Use the chat model to judge whether each citation is supported by its
    source. Returns {citation_id: supported_bool}.

    NOTE: This calls the LLM, so it costs tokens. The eval harness calls this
    only when `--judge` is passed.
    """
    from knowledge_manager.llm import get_llm

    if not sources or not answer:
        return {}
    src_text = "\n\n".join(
        f"[{i}] title={s.get('title','')!r}\n{s.get('text','')}"
        for i, s in enumerate(sources, start=1)
    )
    llm = get_llm()
    resp = llm.invoke(
        [
            {"role": "system", "content": _JUDGE_PROMPT},
            {
                "role": "user",
                "content": f"QUESTION: {question}\n\nANSWER:\n{answer}\n\nSOURCES:\n{src_text}",
            },
        ]
    )
    raw = resp.content if hasattr(resp, "content") else str(resp)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        data = json.loads(m.group(0)) if m else {"citations": []}
    return {c["id"]: bool(c.get("supported")) for c in data.get("citations", [])}
