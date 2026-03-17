"""Episodic memory store built on top of the unified memory model."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import MemoryKind, MemoryRecord


class EpisodicMemory(MemoryRecord):
    """Backward-compatible episodic memory record."""

    def __init__(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        emotion: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        importance: float = 0.5,
    ) -> None:
        super().__init__(
            content=content,
            kind=MemoryKind.EPISODIC,
            context=context or {},
            importance=importance,
            emotion=emotion,
            embedding=embedding,
        )


class EpisodicStore:
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.memories: List[EpisodicMemory] = []

    def add(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        emotion: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        importance: float = 0.5,
    ) -> EpisodicMemory:
        memory = EpisodicMemory(
            content=content,
            context=context,
            emotion=emotion,
            embedding=embedding,
            importance=importance,
        )
        self.memories.append(memory)
        if len(self.memories) > self.max_size:
            self.memories = self.memories[-self.max_size :]
        return memory

    def get_recent(self, hours: int = 24, limit: int = 50) -> List[EpisodicMemory]:
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [memory for memory in self.memories if memory.created_at >= cutoff]
        recent.sort(key=lambda item: item.created_at, reverse=True)
        for item in recent[:limit]:
            item.touch()
        return recent[:limit]

    def search(self, query: str, limit: int = 10) -> List[EpisodicMemory]:
        query_lower = query.lower()
        results = []
        for memory in self.memories:
            if query_lower in memory.text_blob().lower():
                memory.touch()
                results.append(memory)
        results.sort(key=lambda item: (item.access_count, item.importance, item.created_at), reverse=True)
        return results[:limit]

    def get_by_context(self, key: str, value: Any, limit: int = 10) -> List[EpisodicMemory]:
        results = [memory for memory in self.memories if memory.context.get(key) == value]
        results.sort(key=lambda item: item.created_at, reverse=True)
        return results[:limit]

    def find_by_content(self, content: str) -> Optional[EpisodicMemory]:
        needle = content.strip().lower()
        for memory in self.memories:
            if memory.content.strip().lower() == needle:
                return memory
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_memories": len(self.memories),
            "max_size": self.max_size,
            "oldest": self.memories[0].created_at.isoformat() if self.memories else None,
            "newest": self.memories[-1].created_at.isoformat() if self.memories else None,
        }
