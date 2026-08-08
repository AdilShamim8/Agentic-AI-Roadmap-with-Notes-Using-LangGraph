"""Hashing helpers."""
from __future__ import annotations

import hashlib
from pathlib import Path


def file_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def short_id(seed: str, prefix: str = "", n: int = 10) -> str:
    """Short deterministic id from an arbitrary string seed."""
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:n]
    return f"{prefix}{digest}" if prefix else digest
