"""Hippocampus layer: fast event encoding before consolidation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import MemoryKind, MemoryRecord


class MemoryItem(MemoryRecord):
    """Backward-compatible alias for encoded memory records."""

    def __init__(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        embedding: Optional[List[float]] = None,
        emotion: Optional[str] = None,
        source: Optional[str] = None,
        strength: float = 0.5,
    ) -> None:
        super().__init__(
            content=content,
            kind=MemoryKind.EPISODIC,
            context=context or {},
            importance=importance,
            strength=strength,
            embedding=embedding,
            emotion=emotion,
            source=source,
        )


class Hippocampus:
    """Fast-write buffer for newly observed events."""

    def __init__(
        self,
        capacity: int = 1000,
        encoding_interval_minutes: int = 30,
        retention_hours: int = 72,
        keep_recent: int = 200,
        preserve_importance_threshold: float = 0.85,
    ):
        self.capacity = capacity
        self.encoding_interval_minutes = encoding_interval_minutes
        self.retention_hours = retention_hours
        self.keep_recent = keep_recent
        self.preserve_importance_threshold = preserve_importance_threshold
        self.encoding_buffer: List[MemoryItem] = []
        self.associations: Dict[str, List[str]] = {}
        self._consolidation_count = 0

    def encode(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        embedding: Optional[List[float]] = None,
        emotion: Optional[str] = None,
        source: Optional[str] = None,
    ) -> MemoryItem:
        memory = MemoryItem(
            content=content,
            context=context,
            importance=importance,
            embedding=embedding,
            emotion=emotion,
            source=source,
        )
        self.encoding_buffer.append(memory)
        self._update_associations(memory)
        if len(self.encoding_buffer) > self.capacity:
            self._prune_buffer()
        return memory

    def _rebuild_associations(self) -> None:
        self.associations = {}
        for memory in self.encoding_buffer:
            self._update_associations(memory)

    def _prune_buffer(self) -> None:
        self.encoding_buffer.sort(
            key=lambda item: (item.importance, item.strength, item.last_accessed),
            reverse=True,
        )
        self.encoding_buffer = self.encoding_buffer[: self.capacity]
        self._rebuild_associations()

    def prune_retention(self, now: Optional[datetime] = None) -> int:
        now = now or datetime.now()
        cutoff = now - timedelta(hours=self.retention_hours)
        recent_sorted = sorted(self.encoding_buffer, key=lambda item: item.created_at, reverse=True)
        keep_ids = {item.id for item in recent_sorted[: self.keep_recent]}

        retained: List[MemoryItem] = []
        removed = 0
        for item in self.encoding_buffer:
            should_keep = (
                item.created_at >= cutoff
                or item.importance >= self.preserve_importance_threshold
                or item.id in keep_ids
            )
            if should_keep:
                retained.append(item)
            else:
                removed += 1

        self.encoding_buffer = retained
        if len(self.encoding_buffer) > self.capacity:
            self._prune_buffer()
        else:
            self._rebuild_associations()
        return removed

    def _update_associations(self, memory: MemoryItem) -> None:
        source = memory.context.get("source", "default")
        self.associations.setdefault(source, []).append(memory.id)

    def get_recent_memories(self, limit: int = 10) -> List[MemoryItem]:
        recent = sorted(self.encoding_buffer, key=lambda item: item.created_at, reverse=True)[:limit]
        for item in recent:
            item.touch()
        return recent

    def consolidate(self) -> int:
        self._consolidation_count += 1
        return len(self.encoding_buffer)

    def search(self, query: str, limit: int = 5, threshold: float = 0.3) -> List[MemoryItem]:
        query_lower = query.lower()
        results = []
        for memory in self.encoding_buffer:
            blob = memory.text_blob().lower()
            if query_lower in blob:
                memory.touch()
                results.append(memory)
        results.sort(key=lambda item: (item.importance, item.strength, item.access_count), reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "buffer_size": len(self.encoding_buffer),
            "capacity": self.capacity,
            "retention_hours": self.retention_hours,
            "keep_recent": self.keep_recent,
            "preserve_importance_threshold": self.preserve_importance_threshold,
            "associations_count": len(self.associations),
            "consolidation_count": self._consolidation_count,
        }
