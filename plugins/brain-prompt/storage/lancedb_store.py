"""LanceDB-backed persistence for OpenClaw Brain.

This backend stores each memory bucket in its own LanceDB table. Besides the
full payload JSON, it also keeps commonly useful scalar columns so the store is
inspectable now and can evolve toward richer filtering/search later.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from brain.base import MemoryRecord
from embeddings import cosine_similarity, embed_text, embed_texts

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
    EMBEDDING_BUCKETS = {"episodic", "semantic"}

    def __init__(self, root: str | Path):
        if lancedb is None:
            raise ImportError("lancedb is not installed")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(self.root))

    def save_records(self, name: str, records: Iterable[MemoryRecord]) -> str:
        table_name = self._table_name(name)
        rows = self._rows(name, records)
        if table_name in self._table_names():
            self.db.drop_table(table_name)
        if rows:
            self.db.create_table(table_name, data=rows)
        return table_name

    def append_records(self, name: str, records: Iterable[MemoryRecord]) -> str:
        table_name = self._table_name(name)
        rows = self._rows(name, records)
        if not rows:
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
        table_name = self._table_name(name)
        if table_name not in self._table_names():
            return []

        context = context or {}
        query_terms = self._tokenize(query)
        allowed_kinds = {str(kind) for kind in kinds} if kinds else None
        cutoff = datetime.now() - timedelta(hours=recent_hours) if recent_hours else None
        query_embedding = embed_text(query) if query.strip() else []

        ranked: List[tuple[tuple[float, float, float, float], Dict[str, Any]]] = []
        table = self.db.open_table(table_name)
        rows = self._search_rows(table, query_embedding, limit=max(limit * 8, 24))
        for row in rows:
            importance = float(row.get("importance") or 0.0)
            if importance < min_importance:
                continue

            kind = str(row.get("kind") or "")
            if allowed_kinds and kind not in allowed_kinds:
                continue

            created_at = self._parse_dt(row.get("created_at"))
            if cutoff and created_at and created_at < cutoff:
                continue

            memory_context = self._parse_json_object(row.get("context_json"))
            context_match = self._context_match_score(context, memory_context)
            lexical = self._lexical_score(query, query_terms, row, memory_context)
            vector = self._parse_vector(row.get("vector"))
            vector_score = cosine_similarity(query_embedding, vector) if query_embedding and vector else 0.0

            if query_terms and lexical <= 0.0 and context_match <= 0.0 and vector_score <= 0.0:
                continue

            access_count = float(row.get("access_count") or 0.0)
            freshness = created_at.timestamp() if created_at else 0.0
            ranked.append(((max(vector_score, lexical), vector_score, context_match, importance + (freshness * 1e-9) + (access_count * 1e-3)), row))

        ranked.sort(key=lambda item: item[0], reverse=True)
        records: List[MemoryRecord] = []
        for _, row in ranked[:limit]:
            payload = row.get("payload")
            if not payload:
                continue
            records.append(MemoryRecord.from_dict(json.loads(payload)))
        return records

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

    def _row(self, bucket: str, record: MemoryRecord) -> Dict[str, object]:
        data = record.to_dict()
        embedding = self._ensure_embedding(bucket, record, data)
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
            "vector": embedding,
            "embedding_json": json.dumps(embedding, ensure_ascii=False) if embedding is not None else None,
            "embedding_dim": len(embedding) if isinstance(embedding, list) else 0,
            "payload": json.dumps(data, ensure_ascii=False),
        }

    def _quote_sql(self, value: str) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    def _parse_json_object(self, value: Any) -> Dict[str, Any]:
        if not value:
            return {}
        if isinstance(value, dict):
            return value
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _parse_dt(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

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

    def _lexical_score(self, query: str, query_terms: List[str], row: Dict[str, Any], memory_context: Dict[str, Any]) -> float:
        if not query_terms:
            return 0.0
        haystacks = [
            str(row.get("content") or ""),
            str(row.get("text_blob") or ""),
            " ".join(str(value) for value in memory_context.values()),
        ]
        normalized = " ".join(haystacks).lower()
        if not normalized.strip():
            return 0.0
        query_lower = (query or "").lower().strip()
        if query_lower and query_lower in normalized:
            return 1.0
        content_terms = set(self._tokenize(normalized))
        if not content_terms:
            return 0.0
        matches = len(set(query_terms) & content_terms)
        return matches / max(1, len(set(query_terms)))

    def _ensure_embedding(self, bucket: str, record: MemoryRecord, data: Dict[str, Any]) -> Optional[List[float]]:
        bucket = str(bucket or "")
        if bucket not in self.EMBEDDING_BUCKETS:
            return None
        existing = data.get("embedding") or getattr(record, "embedding", None)
        if isinstance(existing, list) and existing:
            return existing
        text = record.text_blob().strip()
        if not text:
            return None
        embedding = embed_text(text)
        record.embedding = embedding
        data["embedding"] = embedding
        return embedding

    def _rows(self, bucket: str, records: Iterable[MemoryRecord]) -> List[Dict[str, object]]:
        prepared = list(records)
        if not prepared:
            return []

        missing_indices: List[int] = []
        texts: List[str] = []
        for index, record in enumerate(prepared):
            if record.embedding:
                continue
            text = record.text_blob().strip()
            if not text:
                continue
            missing_indices.append(index)
            texts.append(text)

        if texts:
            embeddings = embed_texts(texts)
            for index, embedding in zip(missing_indices, embeddings):
                prepared[index].embedding = embedding

        return [self._row(bucket, record) for record in prepared]

    def _parse_vector(self, value: Any) -> Optional[List[float]]:
        if isinstance(value, list):
            return [float(item) for item in value]
        if not value:
            return None
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(parsed, list):
            return None
        return [float(item) for item in parsed]

    def _search_rows(self, table: Any, query_embedding: List[float], limit: int) -> List[Dict[str, Any]]:
        if query_embedding:
            try:
                return table.search(query_embedding).limit(limit).to_list()
            except Exception:
                pass
        return table.to_arrow().to_pylist()
