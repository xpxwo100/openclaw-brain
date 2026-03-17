"""Memory consolidation primitives and a lightweight consolidation pass."""

from __future__ import annotations

import math
import time
from typing import Any, Dict, Iterable, List, Optional


class EbbinghausCurve:
    def __init__(self, halflife_hours: float = 24.0):
        self.halflife_hours = halflife_hours

    def retention(self, hours: float) -> float:
        if hours <= 0:
            return 1.0
        return math.exp(-hours / self.halflife_hours)

    def next_review(self, current_retention: float) -> Optional[float]:
        if current_retention > 0.9:
            return None
        return max(-self.halflife_hours * math.log(max(current_retention, 1e-6)), 0.1)


class MemoryStrength:
    def __init__(self, initial_strength: float = 0.5, max_strength: float = 1.0):
        self.strength = initial_strength
        self.max_strength = max_strength
        self.last_review = time.time()

    def strengthen(self, factor: float = 1.2) -> None:
        self.strength = min(self.strength * factor, self.max_strength)
        self.last_review = time.time()

    def decay(self, hours: float, curve: EbbinghausCurve) -> None:
        self.strength *= curve.retention(hours)

    def apply_forgetting(self, curve: EbbinghausCurve) -> None:
        hours = (time.time() - self.last_review) / 3600.0
        self.decay(hours, curve)


class SleepConsolidation:
    def __init__(self, halflife_hours: float = 24.0, replay_factor: float = 1.2, prune_threshold: float = 0.1):
        self.curve = EbbinghausCurve(halflife_hours)
        self.replay_factor = replay_factor
        self.prune_threshold = prune_threshold
        self.last_consolidation = time.time()
        self.consolidation_count = 0

    def consolidate(self, memories: Iterable[Any]) -> Dict[str, Any]:
        result = {"strengthened": 0, "weakened": 0, "pruned": 0, "total": 0}
        for memory in memories:
            result["total"] += 1

            if hasattr(memory, "apply_forgetting") and hasattr(memory, "strengthen"):
                memory.apply_forgetting(self.curve)
                if memory.strength > 0.3:
                    memory.strengthen(self.replay_factor)
                    result["strengthened"] += 1
                else:
                    result["weakened"] += 1
                if memory.strength < self.prune_threshold:
                    result["pruned"] += 1
                continue

            strength = getattr(memory, "strength", None)
            if strength is None:
                result["weakened"] += 1
                continue

            age_hours = 0.0
            created_at = getattr(memory, "created_at", None)
            if hasattr(created_at, "timestamp"):
                age_hours = max((time.time() - created_at.timestamp()) / 3600.0, 0.0)
            retained = self.curve.retention(age_hours)
            new_strength = max(0.0, min(1.0, strength * retained))
            if new_strength > 0.3:
                new_strength = min(1.0, new_strength * self.replay_factor)
                result["strengthened"] += 1
            else:
                result["weakened"] += 1
            if hasattr(memory, "strength"):
                memory.strength = new_strength
            if new_strength < self.prune_threshold:
                result["pruned"] += 1

        self.last_consolidation = time.time()
        self.consolidation_count += 1
        return result

    def should_consolidate(self, interval_hours: float = 4.0) -> bool:
        hours_since = (time.time() - self.last_consolidation) / 3600.0
        return hours_since >= interval_hours

    def time_until_next(self, interval_hours: float = 4.0) -> float:
        hours_since = (time.time() - self.last_consolidation) / 3600.0
        return max(0.0, interval_hours - hours_since)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "last_consolidation": self.last_consolidation,
            "consolidation_count": self.consolidation_count,
            "halflife_hours": self.curve.halflife_hours,
            "replay_factor": self.replay_factor,
            "prune_threshold": self.prune_threshold,
        }
