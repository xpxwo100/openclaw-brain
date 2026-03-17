"""Common storage backend selection helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .jsonl_store import JsonlMemoryStore


def create_store(backend: str, root: str | Path) -> Any:
    backend = backend.lower()
    if backend == "jsonl":
        return JsonlMemoryStore(root)
    if backend == "lancedb":
        from .lancedb_store import LanceMemoryStore
        return LanceMemoryStore(root)
    raise ValueError(f"unsupported storage backend: {backend}")
