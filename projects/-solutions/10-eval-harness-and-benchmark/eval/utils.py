"""Small utilities used across the harness."""

from __future__ import annotations

import importlib
import json
import random
import re
from pathlib import Path
from typing import Any, Iterable

from eval.schemas import DatasetRow


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts.

    Blank lines and lines starting with `#` are skipped (so JSONL files can
    have header comments).
    """

    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    """Write a list of dicts as JSONL."""

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_dataset_rows(path: str | Path) -> list[DatasetRow]:
    """Read a JSONL file and validate each row into a DatasetRow."""

    raw = read_jsonl(path)
    return [DatasetRow(**r) for r in raw]


# ---------------------------------------------------------------------------
# Dynamic loading (for --agent module:Class)
# ---------------------------------------------------------------------------


def import_string(dotted: str) -> Any:
    """Import a dotted path like 'eval.agents.sample_agents:ReActSampleAgent'.

    Accepts both `module:attr` (preferred) and `module.attr` styles.
    """

    if ":" in dotted:
        module_name, attr = dotted.split(":", 1)
    elif "." in dotted:
        module_name, attr = dotted.rsplit(".", 1)
    else:
        raise ValueError(
            f"Cannot import {dotted!r}: expected 'module:Attr' or 'module.attr'."
        )

    module = importlib.import_module(module_name)
    try:
        return getattr(module, attr)
    except AttributeError as exc:
        raise ImportError(
            f"Module {module_name!r} has no attribute {attr!r}."
        ) from exc


# ---------------------------------------------------------------------------
# String normalisation for rule-based evaluators
# ---------------------------------------------------------------------------


_WS_RE = re.compile(r"\s+")


def normalize_answer(text: str) -> str:
    """Normalise an answer string for fuzzy comparison.

    - lowercases
    - strips
    - collapses internal whitespace
    - strips trailing punctuation
    """

    if not isinstance(text, str):
        text = str(text)
    text = text.strip().lower()
    text = _WS_RE.sub(" ", text)
    text = text.rstrip(".,;:!?")
    return text


def answer_to_str(answer: Any) -> str:
    """Coerce an answer (str | dict | list | None) to a single string."""

    if answer is None:
        return ""
    if isinstance(answer, str):
        return answer
    if isinstance(answer, (dict, list)):
        return json.dumps(answer, ensure_ascii=False, sort_keys=True)
    return str(answer)


# ---------------------------------------------------------------------------
# Sampling / reproducibility
# ---------------------------------------------------------------------------


def make_rng(seed: int) -> random.Random:
    """Create a seeded RNG (so tests are deterministic)."""

    return random.Random(seed)


def chunked(items: list[Any], n: int) -> list[list[Any]]:
    """Split a list into n roughly-equal chunks."""

    if n <= 1:
        return [list(items)]
    k, m = divmod(len(items), n)
    out = []
    for i in range(n):
        start = i * k + min(i, m)
        end = (i + 1) * k + min(i + 1, m)
        out.append(items[start:end])
    return out
