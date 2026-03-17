"""JSONL-backed persistence for OpenClaw Brain.

This module stores memory layers as newline-delimited JSON so the project can
persist state without dragging in a database too early.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

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

    def clear(self) -> None:
        for filename in self.FILES.values():
            path = self.root / filename
            if path.exists():
                path.unlink()

    def _filename(self, name: str) -> str:
        if name not in self.FILES:
            raise KeyError(f"unknown memory bucket: {name}")
        return self.FILES[name]
