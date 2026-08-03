"""Small, dependency-free helper functions.

Everything here is pure Python so it can be unit tested without a network
connection, an API key, or any third-party package installed.
"""

from __future__ import annotations

import json
import re
from typing import Any, List, Optional


def safe_json_parse(text: str) -> Optional[Any]:
    """Best-effort JSON parsing of an LLM response.

    LLMs frequently wrap JSON in markdown code fences or add a sentence
    of preamble. This tries, in order:
      1. Parsing the raw text directly.
      2. Stripping ```json ... ``` / ``` ... ``` fences.
      3. Extracting the first {...} or [...] block found in the text.
    Returns None if nothing parses.
    """

    text = text.strip()

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                continue

    return None


def chunk_text(text: str, max_chars: int = 4000, overlap: int = 200) -> List[str]:
    """Split long text into overlapping chunks on whitespace boundaries.

    Used so a long fetched web page or local document doesn't blow past
    an LLM's context window when it's dropped into a prompt.
    """

    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            # try to break on a whitespace boundary near the end
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def truncate(text: str, max_chars: int = 1500, suffix: str = " …") -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + suffix


_TRACKING_PARAM_RE = re.compile(r"^(utm_\w+|ref|source|fbclid|gclid)$", re.IGNORECASE)


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication purposes (strip trailing slash,
    fragment, and common tracking params)."""

    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    url = url.strip()
    parts = urlsplit(url)

    kept_params = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _TRACKING_PARAM_RE.match(k)]
    query = urlencode(kept_params)

    path = parts.path.rstrip("/") or ""
    normalized = urlunsplit((parts.scheme, parts.netloc, path, query, ""))
    return normalized.lower()


def slugify(text: str, max_len: int = 60) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:max_len].rstrip("-") or "untitled"


def dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result
