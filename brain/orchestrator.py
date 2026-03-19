"""Top-level orchestration layer for OpenClaw Brain."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .attention import AttentionGate
from .base import MemoryKind, MemoryRecord
from .consolidation import SleepConsolidation
from .context import BrainContextBuilder
from .episodic import EpisodicStore
from .hippocampus import Hippocampus
from .retrieval import MemoryRetriever, RetrievedMemory, RetrievalScore
from .semantic import SemanticStore
from .working_memory import WorkingMemory, WorkingMemoryItem


STATE_SUMMARY_KEY = "assistant_state_summary"


class OpenClawBrain:
    """Unified entry point for memory ingestion, recall, and consolidation."""

    def __init__(
        self,
        workspace: Optional[str] = None,
        attention_threshold: float = 0.5,
        working_memory_capacity: int = 20,
        hippocampus_capacity: int = 1000,
        consolidation_interval_hours: float = 4.0,
    ) -> None:
        self.workspace = workspace
        self.attention_gate = AttentionGate(threshold=attention_threshold)
        self.working = WorkingMemory(capacity=working_memory_capacity)
        self.hippocampus = Hippocampus(capacity=hippocampus_capacity)
        self.episodic = EpisodicStore(max_size=hippocampus_capacity * 10)
        self.semantic = SemanticStore()
        self.retriever = MemoryRetriever()
        self.context_builder = BrainContextBuilder()
        self.consolidator = SleepConsolidation()
        self.consolidation_interval_hours = consolidation_interval_hours

    def remember(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
        mode: str = "auto",
    ) -> Optional[MemoryRecord]:
        """Ingest a piece of information into the brain.

        mode:
        - auto: gate it first, then store
        - working: force into working memory
        - episodic: force into hippocampus buffer only; episodic store is populated by consolidate()
        - semantic: force into semantic memory
        """
        context = context or {}

        if mode == "semantic":
            return self._remember_semantic(text, context, importance)

        if mode == "working":
            score = importance if importance is not None else 0.8
            self.working.add(text, text, importance=score)
            return MemoryRecord(content=text, kind=MemoryKind.WORKING, context=context, importance=score)

        if mode == "episodic":
            score = importance if importance is not None else 0.7
            memory = self.hippocampus.encode(text, context=context, importance=score)
            if score >= 0.7:
                self.working.add(text, text, importance=score)
            return memory

        gate_result = self.attention_gate.should_pass(text, context=context)
        score = importance if importance is not None else max(gate_result.score, 0.1)
        if not gate_result.passed and importance is None:
            return None

        memory = self.hippocampus.encode(text, context=context, importance=score)
        if score >= 0.65:
            self.working.add(text, text, importance=score)
        return memory

    def _remember_semantic(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
    ) -> MemoryRecord:
        context = context or {}
        name = context.get("name") or text[:40]
        definition = context.get("definition") or text
        category = context.get("category") or context.get("kind") or "general"
        concept = self.semantic.add_concept(name=name, definition=definition, category=category, properties=context)
        return concept.to_memory_record(importance=importance or 0.8)

    def recall(
        self,
        query: str,
        limit: int = 5,
        context: Optional[Dict[str, Any]] = None,
        emotion: Optional[str] = None,
    ) -> List[Any]:
        """Recall memories from all active layers with reranking."""
        candidates: List[Any] = []

        working_candidates = [item.to_memory_record() for item in self.working.get_all()]
        candidates.extend(working_candidates)
        candidates.extend(self.hippocampus.get_recent_memories(limit=100))
        candidates.extend(self.episodic.memories)
        candidates.extend([concept.to_memory_record() for concept in self.semantic.concepts.values()])

        best_by_blob: Dict[str, Any] = {}
        for candidate in candidates:
            blob = getattr(candidate, "content", str(candidate)).strip().lower()
            if not blob:
                continue
            existing = best_by_blob.get(blob)
            if existing is None or self._candidate_rank(candidate) > self._candidate_rank(existing):
                best_by_blob[blob] = candidate

        deduped = list(best_by_blob.values())

        return self.retriever.retrieve(
            query=query,
            memories=deduped,
            context=context,
            emotion=emotion,
            limit=limit,
        )

    def build_context(
        self,
        query: str,
        recent_messages: Optional[List[str]] = None,
        recent_message_ids: Optional[List[str]] = None,
        limit: int = 5,
        context: Optional[Dict[str, Any]] = None,
        emotion: Optional[str] = None,
        max_chars: Optional[int] = None,
        max_estimated_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        recalled = self.recall(query=query, limit=max(limit * 4, 10), context=context, emotion=emotion)
        if self._is_progress_query(query):
            state_summary = self._state_summary_candidate()
            if state_summary is not None:
                recalled = [state_summary, *recalled]
        return self.context_builder.build(
            query=query,
            recalled=recalled,
            recent_messages=recent_messages,
            recent_message_ids=recent_message_ids,
            max_items=limit,
            max_chars=max_chars,
            max_estimated_tokens=max_estimated_tokens,
        )

    def consolidate(self) -> Dict[str, Any]:
        """Run a simple consolidation pass.

        The orchestrator currently does three things:
        1. deduplicates hippocampus buffer events by content
        2. promotes durable hippocampus winners into episodic memory
        3. extracts obvious semantic memories from rule/preference/fact contexts
        """
        staged = self.hippocampus.get_recent_memories(limit=self.hippocampus.capacity)
        grouped: Dict[str, List[MemoryRecord]] = defaultdict(list)
        for record in staged:
            grouped[record.content.strip().lower()].append(record)

        promoted_episodic = 0
        promoted_semantic = 0
        strengthened = 0

        for _, records in grouped.items():
            winner = max(records, key=lambda item: (item.importance, item.strength, item.access_count))
            winner.strength = min(1.0, winner.strength + 0.1 * max(1, len(records) - 1))
            strengthened += max(0, len(records) - 1)

            if self.episodic.find_by_content(winner.content) is None:
                self.episodic.add(winner.content, context=winner.context, emotion=winner.emotion, importance=winner.importance)
                promoted_episodic += 1

            semantic_kind = winner.context.get("kind")
            if semantic_kind in {"rule", "preference", "fact"}:
                if self.semantic.find_by_name(winner.content) is None:
                    self.semantic.add_concept(
                        name=winner.content,
                        definition=winner.context.get("definition", winner.content),
                        category=semantic_kind,
                        properties=winner.context,
                    )
                    promoted_semantic += 1

        pruned_hippocampus = self.hippocampus.prune_retention()

        return {
            "promoted_episodic": promoted_episodic,
            "promoted_semantic": promoted_semantic,
            "strengthened": strengthened,
            "source_events": len(staged),
            "pruned_hippocampus": pruned_hippocampus,
        }

    def _is_progress_query(self, query: str) -> bool:
        query = (query or "").strip().lower()
        progress_markers = [
            "修到哪", "做到哪", "进度", "当前状态", "现在状态", "做到哪里", "卡在哪", "最新进展",
            "where are we", "progress", "current status", "latest status", "what's the status",
        ]
        return any(marker in query for marker in progress_markers)

    def _state_summary_candidate(self) -> Optional[RetrievedMemory]:
        concept = self.semantic.find_by_name(STATE_SUMMARY_KEY)
        if concept is None:
            return None
        memory = concept.to_memory_record(importance=0.98)
        memory.context.update({
            "definition": concept.definition,
            "category": "state_summary",
            "source_subtype": "assistant_state_summary",
            **concept.properties,
        })
        memory.content = STATE_SUMMARY_KEY
        return RetrievedMemory(
            memory=memory,
            score=RetrievalScore(relevance=1.0, recency=0.85, importance=0.98, context_match=1.0),
            matched_terms=["state_summary"],
        )

    def _candidate_rank(self, candidate: Any) -> tuple[float, float, float, float]:
        kind = getattr(candidate, "kind", MemoryKind.EPISODIC)
        kind_value = kind.value if hasattr(kind, "value") else str(kind)
        kind_priority = {
            "summary": 5.5,
            "preference": 5.0,
            "rule": 5.0,
            "fact": 4.5,
            "task": 4.4,
            "semantic": 4.0,
            "episodic": 3.0,
            "working": 2.0,
        }.get(kind_value, 1.0)
        return (
            kind_priority,
            float(getattr(candidate, "importance", 0.5)),
            float(getattr(candidate, "strength", 0.5)),
            float(getattr(candidate, "access_count", 0)),
        )

    def snapshot(self) -> Dict[str, List[MemoryRecord]]:
        """Export the brain state into serializable memory records."""
        return {
            "working": [item.to_memory_record() for item in self.working.get_all()],
            "hippocampus": list(self.hippocampus.encoding_buffer),
            "episodic": list(self.episodic.memories),
            "semantic": [concept.to_memory_record() for concept in self.semantic.concepts.values()],
        }

    def save(self, root: str | Path, backend: str = "jsonl") -> Dict[str, Any]:
        """Persist current state to the selected storage backend."""
        from storage import create_store

        store = create_store(backend, root)
        return store.save_snapshot(self.snapshot())

    @classmethod
    def load(cls, root: str | Path, backend: str = "jsonl", **kwargs: Any) -> "OpenClawBrain":
        """Restore a brain instance from the selected storage backend."""
        from storage import create_store

        store = create_store(backend, root)
        snapshot = store.load_snapshot()
        brain = cls(**kwargs)
        brain.load_snapshot(snapshot)
        return brain

    def load_snapshot(self, snapshot: Dict[str, List[MemoryRecord]]) -> None:
        """Replace current in-memory state from a snapshot payload."""
        working_items = []
        for record in snapshot.get("working", []):
            raw_value = record.metadata.get("raw_value", record.content)
            working_items.append(
                WorkingMemoryItem(
                    key=record.metadata.get("working_key", record.context.get("key", record.content)),
                    value=raw_value,
                    importance=record.importance,
                    ttl_minutes=record.ttl_minutes or self.working.default_ttl_minutes,
                    created_at=record.created_at,
                    last_accessed=record.last_accessed,
                    access_count=record.access_count,
                )
            )
        self.working.load_items(working_items)

        self.hippocampus.encoding_buffer = [MemoryRecord.from_dict(record.to_dict()) if not isinstance(record, MemoryRecord) else record for record in snapshot.get("hippocampus", [])]
        self.episodic.memories = [MemoryRecord.from_dict(record.to_dict()) if not isinstance(record, MemoryRecord) else record for record in snapshot.get("episodic", [])]

        self.semantic.concepts.clear()
        self.semantic.name_index.clear()
        for record in snapshot.get("semantic", []):
            if not isinstance(record, MemoryRecord):
                record = MemoryRecord.from_dict(record.to_dict())
            category = record.context.get("category", record.kind.value)
            definition = record.context.get("definition", record.content)
            properties = dict(record.metadata)
            properties.update({k: v for k, v in record.context.items() if k not in {"category", "definition"}})
            concept = self.semantic.add_concept(
                name=record.content,
                definition=definition,
                category=category,
                properties=properties,
            )
            concept.access_count = record.access_count

    def should_consolidate(self) -> bool:
        return self.consolidator.should_consolidate(self.consolidation_interval_hours)
