"""Working memory for OpenClaw Brain.

A small, short-lived store for the agent's current task state.
It keeps only a limited number of items, expires stale entries,
and can rehearse important items into longer-term memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .base import MemoryKind, MemoryRecord


@dataclass
class WorkingMemoryItem:
    """A single working-memory entry."""

    key: str
    value: Any
    importance: float = 0.5
    ttl_minutes: int = 30
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """Return True when the item has exceeded its TTL."""
        now = now or datetime.now()
        return now - self.created_at > timedelta(minutes=self.ttl_minutes)

    def access(self) -> None:
        """Mark the item as accessed."""
        self.access_count += 1
        self.last_accessed = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the item to a JSON-friendly dict."""
        return {
            "key": self.key,
            "value": self.value,
            "importance": self.importance,
            "ttl_minutes": self.ttl_minutes,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
        }

    def to_memory_record(self) -> MemoryRecord:
        return MemoryRecord(
            content=self.value if isinstance(self.value, str) else str(self.value),
            kind=MemoryKind.WORKING,
            context={"key": self.key},
            importance=self.importance,
            ttl_minutes=self.ttl_minutes,
            created_at=self.created_at,
            last_accessed=self.last_accessed,
            access_count=self.access_count,
            metadata={"working_key": self.key, "raw_value": self.value},
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkingMemoryItem":
        return cls(
            key=data["key"],
            value=data.get("value"),
            importance=data.get("importance", 0.5),
            ttl_minutes=data.get("ttl_minutes", 30),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else datetime.now(),
            access_count=data.get("access_count", 0),
        )


class WorkingMemory:
    """Limited-capacity working memory with TTL and simple rehearsal support."""

    def __init__(self, capacity: int = 20, default_ttl_minutes: int = 30):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if default_ttl_minutes <= 0:
            raise ValueError("default_ttl_minutes must be positive")

        self.capacity = capacity
        self.default_ttl_minutes = default_ttl_minutes
        self._items: Dict[str, WorkingMemoryItem] = {}

    def add(
        self,
        key: str,
        value: Any,
        importance: float = 0.5,
        ttl_minutes: Optional[int] = None,
    ) -> WorkingMemoryItem:
        """Add or update an item in working memory."""
        self._prune_expired()

        if key in self._items:
            item = self._items[key]
            item.value = value
            item.importance = importance
            item.ttl_minutes = ttl_minutes or item.ttl_minutes
            item.access()
            return item

        if len(self._items) >= self.capacity:
            self._evict()

        item = WorkingMemoryItem(
            key=key,
            value=value,
            importance=max(0.0, min(1.0, importance)),
            ttl_minutes=ttl_minutes or self.default_ttl_minutes,
        )
        self._items[key] = item
        return item

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key, or None when missing/expired."""
        item = self._items.get(key)
        if item is None:
            return None

        if item.is_expired():
            self.remove(key)
            return None

        item.access()
        return item.value

    def get_item(self, key: str) -> Optional[WorkingMemoryItem]:
        """Get the full item object."""
        item = self._items.get(key)
        if item and item.is_expired():
            self.remove(key)
            return None
        return item

    def remove(self, key: str) -> bool:
        """Remove an item by key."""
        return self._items.pop(key, None) is not None

    def rehearse(
        self,
        key: str,
        target: str = "semantic",
        callback: Optional[Callable[[str, Any, str], None]] = None,
    ) -> bool:
        """Promote a sufficiently important item to longer-term memory.

        Returns True only when the item exists, is important enough, and the
        transfer succeeds.
        """
        item = self.get_item(key)
        if item is None:
            return False
        if item.importance < 0.7:
            return False

        if callback is not None:
            callback(key, item.value, target)

        self.remove(key)
        return True

    def get_all(self) -> List[WorkingMemoryItem]:
        """Return all live items sorted by importance, recency, then usage."""
        self._prune_expired()
        return sorted(
            self._items.values(),
            key=lambda item: (
                item.importance,
                item.last_accessed,
                item.access_count,
            ),
            reverse=True,
        )

    def clear(self) -> None:
        """Clear the store."""
        self._items.clear()

    def load_items(self, items: List[WorkingMemoryItem]) -> None:
        """Replace current contents with provided working-memory items."""
        self._items = {item.key: item for item in items}
        self._prune_expired()
        while len(self._items) > self.capacity:
            self._evict()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize working memory state."""
        items = self.get_all()
        return {
            "capacity": self.capacity,
            "count": len(items),
            "items": [item.to_dict() for item in items],
        }

    def _prune_expired(self) -> None:
        """Drop all expired items."""
        expired_keys = [key for key, item in self._items.items() if item.is_expired()]
        for key in expired_keys:
            self._items.pop(key, None)

    def _evict(self) -> None:
        """Evict the most disposable item.

        Higher eviction score means an item is a better removal candidate:
        low importance, low access frequency, and older access time all push it
        closer to the chopping block.
        """
        if not self._items:
            return

        def eviction_score(item: WorkingMemoryItem) -> float:
            age_minutes = max(
                0.0,
                (datetime.now() - item.last_accessed).total_seconds() / 60.0,
            )
            normalized_age = min(age_minutes / max(item.ttl_minutes, 1), 1.0)
            return (
                (1.0 - item.importance) * 0.6
                + (1.0 / (item.access_count + 1)) * 0.25
                + normalized_age * 0.15
            )

        victim_key = max(self._items, key=lambda key: eviction_score(self._items[key]))
        self.remove(victim_key)


if __name__ == "__main__":
    wm = WorkingMemory(capacity=3)
    wm.add("user_nickname", "鸡哥", importance=0.9)
    wm.add("current_task", "优化 OpenClaw Brain", importance=0.8)
    wm.add("temp_counter", 42, importance=0.2)
    wm.add("scratch", "will evict something", importance=0.1)
    print(wm.to_dict())
