"""LanceDB-backed persistence for OpenClaw Brain.

This backend stores each memory bucket in its own LanceDB table. Besides the
full payload JSON, it also keeps commonly useful scalar columns so the store is
inspectable now and can evolve toward richer filtering/search later.
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
        rows = [self._row(name, record) for record in records]
        if table_name in self._table_names():
            self.db.drop_table(table_name)
        self.db.create_table(table_name, data=rows or [self._placeholder_row(name)])
        if not rows:
            self.db.open_table(table_name).delete("id = '__empty__'")
        return table_name

    def append_records(self, name: str, records: Iterable[MemoryRecord]) -> str:
        table_name = self._table_name(name)
        rows = [self._row(name, record) for record in records]
        if not rows:
            if table_name not in self._table_names():
                self.db.create_table(table_name, data=[self._placeholder_row(name)])
                self.db.open_table(table_name).delete("id = '__empty__'")
            return table_name

        if table_name not in self._table_names():
            self.db.create_table(table_name, data=rows)
            return table_name

        table = self.db.open_table(table_name)
        ids = [row["id"] for row in rows if row.get("id")]
        if ids:
            escaped = [self._quote_sql(value) for value in ids]
            table.delete(f"id IN ({', '.join(escaped)})")
        table.add(rows)
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
        records.sort(key=lambda item: item.created_at)
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

    def _placeholder_row(self, bucket: str) -> Dict[str, object]:
        return {
            "id": "__empty__",
            "bucket": bucket,
            "content": "",
            "kind": "empty",
            "source": None,
            "importance": 0.0,
            "strength": 0.0,
            "emotion": None,
            "access_count": 0,
            "ttl_minutes": None,
            "created_at": "",
            "last_accessed": "",
            "text_blob": "",
            "context_json": "{}",
            "metadata_json": "{}",
            "embedding_json": None,
            "embedding_dim": 0,
            "payload": json.dumps({"id": "__empty__"}),
        }

    def _row(self, bucket: str, record: MemoryRecord) -> Dict[str, object]:
        data = record.to_dict()
        embedding = data.get("embedding")
        return {
            "id": record.id,
            "bucket": bucket,
            "content": record.content,
            "kind": record.kind.value,
            "source": record.source,
            "importance": float(record.importance),
            "strength": float(record.strength),
            "emotion": record.emotion,
            "access_count": int(record.access_count),
            "ttl_minutes": record.ttl_minutes,
            "created_at": record.created_at.isoformat(),
            "last_accessed": record.last_accessed.isoformat(),
            "text_blob": record.text_blob(),
            "context_json": json.dumps(record.context, ensure_ascii=False),
            "metadata_json": json.dumps(record.metadata, ensure_ascii=False),
            "embedding_json": json.dumps(embedding, ensure_ascii=False) if embedding is not None else None,
            "embedding_dim": len(embedding) if isinstance(embedding, list) else 0,
            "payload": json.dumps(data, ensure_ascii=False),
        }

    def _quote_sql(self, value: str) -> str:
        return "'" + str(value).replace("'", "''") + "'"
