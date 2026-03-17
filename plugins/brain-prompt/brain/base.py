"""Core data types shared across the OpenClaw Brain package."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class MemoryKind(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    RULE = "rule"
    PREFERENCE = "preference"
    FACT = "fact"
    TASK = "task"
    TOOL = "tool"
    SUMMARY = "summary"


@dataclass
class MemoryRecord:
    """Unified memory model used across all layers."""

    content: str
    kind: MemoryKind = MemoryKind.EPISODIC
    context: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    strength: float = 0.5
    emotion: Optional[str] = None
    embedding: Optional[List[float]] = None
    source: Optional[str] = None
    ttl_minutes: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"mem_{uuid4().hex[:12]}")
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def __post_init__(self) -> None:
        self.importance = max(0.0, min(1.0, self.importance))
        self.strength = max(0.0, min(1.0, self.strength))
        if isinstance(self.kind, str):
            self.kind = MemoryKind(self.kind)

    def touch(self) -> None:
        self.access_count += 1
        self.last_accessed = datetime.now()

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self.ttl_minutes is None:
            return False
        now = now or datetime.now()
        return now - self.created_at > timedelta(minutes=self.ttl_minutes)

    def text_blob(self) -> str:
        parts = [self.content]
        if self.context:
            parts.extend(str(v) for v in self.context.values())
        if self.metadata:
            parts.extend(str(v) for v in self.metadata.values())
        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "content": self.content,
            "context": self.context,
            "importance": self.importance,
            "strength": self.strength,
            "emotion": self.emotion,
            "embedding": self.embedding,
            "source": self.source,
            "ttl_minutes": self.ttl_minutes,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        return cls(
            id=data.get("id", f"mem_{uuid4().hex[:12]}"),
            content=data["content"],
            kind=data.get("kind", MemoryKind.EPISODIC.value),
            context=data.get("context", {}),
            importance=data.get("importance", 0.5),
            strength=data.get("strength", 0.5),
            emotion=data.get("emotion"),
            embedding=data.get("embedding"),
            source=data.get("source"),
            ttl_minutes=data.get("ttl_minutes"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else datetime.now(),
            access_count=data.get("access_count", 0),
        )


@dataclass
class ScoredMemory:
    memory: Any
    score: float
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "reasons": self.reasons,
            "memory": self.memory.to_dict() if hasattr(self.memory, "to_dict") else str(self.memory),
        }
