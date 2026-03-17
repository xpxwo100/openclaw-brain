"""Repository primitives for storing and querying memory records."""

from __future__ import annotations

from typing import Iterable, List, Optional

from .base import MemoryKind, MemoryRecord


class InMemoryRepository:
    """A tiny repository used by the refactored brain as the default store."""

    def __init__(self) -> None:
        self._records: List[MemoryRecord] = []

    def add(self, record: MemoryRecord) -> MemoryRecord:
        self._records.append(record)
        return record

    def extend(self, records: Iterable[MemoryRecord]) -> None:
        self._records.extend(records)

    def all(self) -> List[MemoryRecord]:
        return list(self._records)

    def recent(self, limit: int = 10) -> List[MemoryRecord]:
        return sorted(self._records, key=lambda item: item.created_at, reverse=True)[:limit]

    def by_kind(self, kind: MemoryKind | str) -> List[MemoryRecord]:
        kind_value = kind.value if isinstance(kind, MemoryKind) else str(kind)
        return [record for record in self._records if record.kind.value == kind_value]

    def remove(self, record_id: str) -> bool:
        before = len(self._records)
        self._records = [record for record in self._records if record.id != record_id]
        return len(self._records) != before

    def find_exact(self, content: str, kind: Optional[MemoryKind | str] = None) -> Optional[MemoryRecord]:
        kind_value = None
        if kind is not None:
            kind_value = kind.value if isinstance(kind, MemoryKind) else str(kind)
        for record in self._records:
            if record.content != content:
                continue
            if kind_value and record.kind.value != kind_value:
                continue
            return record
        return None
