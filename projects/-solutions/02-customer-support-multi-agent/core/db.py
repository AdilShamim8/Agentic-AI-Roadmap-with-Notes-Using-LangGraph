"""
Tiny JSON-file "database" so the whole project runs with zero external
services. Swap this module out for a real DB client in production - every
other module only talks to the functions in `billing.py`, `orders.py`, etc.,
never to files directly, so the swap is contained to one place.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_lock = threading.Lock()
_cache: dict[str, list[dict[str, Any]]] = {}


def _path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def load(name: str) -> list[dict[str, Any]]:
    """Load a JSON table (e.g. 'orders', 'invoices', 'customers') as a list of dicts."""
    with _lock:
        if name not in _cache:
            path = _path(name)
            if not path.exists():
                raise FileNotFoundError(f"No data file for table '{name}' at {path}")
            with path.open("r", encoding="utf-8") as f:
                _cache[name] = json.load(f)
        # return a shallow copy so callers can't mutate the cache by accident
        return [dict(row) for row in _cache[name]]


def find_one(name: str, **filters: Any) -> dict[str, Any] | None:
    """Return the first row in table `name` matching all keyword filters, or None."""
    for row in load(name):
        if all(row.get(k) == v for k, v in filters.items()):
            return row
    return None


def find_many(name: str, **filters: Any) -> list[dict[str, Any]]:
    """Return all rows in table `name` matching all keyword filters."""
    return [row for row in load(name) if all(row.get(k) == v for k, v in filters.items())]


def reset_cache() -> None:
    """Clear the in-memory cache (mainly useful for tests)."""
    with _lock:
        _cache.clear()
