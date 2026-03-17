"""LanceDB-backed persistence for OpenClaw Brain.

This backend stores each memory bucket in its own LanceDB table. We keep the
full MemoryRecord payload as JSON for robust round-tripping, while also exposing
basic columns for later filtering/search.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from brain.base import MemoryRecord

try:
    import lancedb
except ImportError:  # pragma: no cover - handled by runtime/tests
    lancedb = None


class LanceMemoryStore:
    """Persist brain state in LanceDB tables."""

    TABLES = {
        "working": "working_records",
        "hippocampus": "hippocampus_records",
        "episodic": "episodic_records",
        "semantic": "semantic_records",
    }

    def __init__(self, root: str | Path):
        if lancedb is None:
            raise ImportError("lancedb is not installed")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(self.root))

    def save_records(self, name: str, records: Iterable[MemoryRecord]) -> str:
        table_name = self._table_name(name)
        rows = [self._row(record) for record in records]
        if table_name in self._table_names():
            self.db.drop_table(table_name)
        self.db.create_table(table_name, data=rows or [{"id": "__empty__", "content": "", "kind": "empty", "created_at": "", "payload": "{}"}])
        if not rows:
            table = self.db.open_table(table_name)
            table.delete("id = '__empty__'")
        return table_name

    def load_records(self, name: str) -> List[MemoryRecord]:
        table_name = self._table_name(name)
        if table_name not in self._table_names():
            return []
        table = self.db.open_table(table_name)
        rows = table.to_arrow().to_pylist()
        records: List[MemoryRecord] = []
        for row in rows:
            payload = row.get("payload")
            if not payload:
                continue
            data = json.loads(payload)
            if data.get("id") == "__empty__":
                continue
            records.append(MemoryRecord.from_dict(data))
        return records

    def save_snapshot(self, snapshot: Dict[str, object]) -> Dict[str, str]:
        written: Dict[str, str] = {}
        for name in self.TABLES:
            records = snapshot.get(name, [])
            written[name] = self.save_records(name, records)
        return written

    def load_snapshot(self) -> Dict[str, List[MemoryRecord]]:
        return {name: self.load_records(name) for name in self.TABLES}

    def clear(self) -> None:
        for table_name in self.TABLES.values():
            if table_name in self._table_names():
                self.db.drop_table(table_name)

    def _table_name(self, name: str) -> str:
        if name not in self.TABLES:
            raise KeyError(f"unknown memory bucket: {name}")
        return self.TABLES[name]

    def _table_names(self) -> List[str]:
        response = self.db.list_tables()
        return list(getattr(response, "tables", []) or [])

    def _row(self, record: MemoryRecord) -> Dict[str, object]:
        return {
            "id": record.id,
            "content": record.content,
            "kind": record.kind.value,
            "created_at": record.created_at.isoformat(),
            "payload": json.dumps(record.to_dict(), ensure_ascii=False),
        }
