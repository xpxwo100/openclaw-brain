"""JSONL-backed persistence for OpenClaw Brain.

This module stores memory layers as newline-delimited JSON so the project can
persist state without dragging in a database too early.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from brain.base import MemoryRecord


class JsonlMemoryStore:
    """Persist brain state to a directory of JSONL files."""

    FILES = {
        "working": "working.jsonl",
        "hippocampus": "hippocampus.jsonl",
        "episodic": "episodic.jsonl",
        "semantic": "semantic.jsonl",
    }

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_records(self, name: str, records: Iterable[MemoryRecord]) -> Path:
        path = self.root / self._filename(name)
        with path.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        return path

    def append_records(self, name: str, records: Iterable[MemoryRecord]) -> Path:
        path = self.root / self._filename(name)
        with path.open("a", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        return path

    def load_records(self, name: str) -> List[MemoryRecord]:
        path = self.root / self._filename(name)
        if not path.exists():
            return []
        records: List[MemoryRecord] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                records.append(MemoryRecord.from_dict(json.loads(line)))
        return records

    def save_snapshot(self, snapshot: Dict[str, object]) -> Dict[str, Path]:
        written: Dict[str, Path] = {}
        for name in self.FILES:
            records = snapshot.get(name, [])
            written[name] = self.save_records(name, records)
        return written

    def load_snapshot(self) -> Dict[str, List[MemoryRecord]]:
        return {name: self.load_records(name) for name in self.FILES}

    def query_records(
        self,
        name: str,
        query: str = "",
        limit: int = 20,
        *,
        kinds: Optional[Sequence[str]] = None,
        min_importance: float = 0.0,
        recent_hours: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryRecord]:
        context = context or {}
        allowed_kinds = {str(kind) for kind in kinds} if kinds else None
        cutoff = datetime.now() - timedelta(hours=recent_hours) if recent_hours else None
        query_terms = self._tokenize(query)

        ranked: List[tuple[tuple[float, float, float, float], MemoryRecord]] = []
        for record in self.load_records(name):
            if record.importance < min_importance:
                continue
            kind = record.kind.value if hasattr(record.kind, "value") else str(record.kind)
            if allowed_kinds and kind not in allowed_kinds:
                continue
            if cutoff and record.created_at < cutoff:
                continue

            context_match = self._context_match_score(context, record.context or {})
            lexical = self._lexical_score(query, query_terms, record)
            if query_terms and lexical <= 0.0 and context_match <= 0.0:
                continue

            freshness = record.created_at.timestamp() if hasattr(record.created_at, "timestamp") else 0.0
            ranked.append(((lexical, context_match, float(record.importance), freshness + float(record.access_count)), record))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in ranked[:limit]]

    def clear(self) -> None:
        for filename in self.FILES.values():
            path = self.root / filename
            if path.exists():
                path.unlink()

    def _filename(self, name: str) -> str:
        if name not in self.FILES:
            raise KeyError(f"unknown memory bucket: {name}")
        return self.FILES[name]

    def _tokenize(self, text: str) -> List[str]:
        return [token for token in re.findall(r"\w+", (text or "").lower()) if token]

    def _context_match_score(self, query_context: Dict[str, Any], memory_context: Dict[str, Any]) -> float:
        if not query_context or not memory_context:
            return 0.0
        matches = 0
        total = 0
        for key, value in query_context.items():
            if value in (None, ""):
                continue
            total += 1
            if memory_context.get(key) == value:
                matches += 1
        if total == 0:
            return 0.0
        return matches / total

    def _lexical_score(self, query: str, query_terms: List[str], record: MemoryRecord) -> float:
        if not query_terms:
            return 0.0
        haystack = record.text_blob().lower()
        query_lower = (query or "").lower().strip()
        if query_lower and query_lower in haystack:
            return 1.0
        content_terms = set(self._tokenize(haystack))
        if not content_terms:
            return 0.0
        matches = len(set(query_terms) & content_terms)
        return matches / max(1, len(set(query_terms)))
