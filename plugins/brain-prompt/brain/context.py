"""Prompt/context-oriented recall helpers for OpenClaw Brain.

This module is intentionally opinionated:
- prefer semantic memories over recent chat echoes
- filter memories already covered by recent conversation
- render compact prompt-ready context blocks instead of raw transcripts
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Any, Dict, Iterable, List, Optional

from .base import MemoryKind
from .retrieval import RetrievedMemory

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_TRIVIAL_TEXTS = {
    "继续", "好", "好的", "嗯", "行", "收到", "在吗", "ok", "okay", "yes", "no", "哈哈", "哈", "测试", "再试一次"
}
_PROGRESS_QUERY_RE = re.compile(r"修到哪|做到哪|进度|当前状态|现在状态|做到哪里|卡在哪|什么情况|最新进展|where are we|progress|current status|latest status|what's the status", re.IGNORECASE)


@dataclass
class ContextItem:
    kind: str
    text: str
    score: float
    source: Optional[str] = None
    memory_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "score": round(self.score, 4),
            "source": self.source,
            "memory_id": self.memory_id,
        }


_ASSISTANT_SOURCE_SUBTYPE_PRIORITY = {
    "assistant_state": 4.0,
    "assistant_decision": 3.5,
    "assistant_result": 3.0,
    "assistant_commit": 2.5,
}


class BrainContextBuilder:
    """Build compact context blocks from recalled memories."""

    def __init__(
        self,
        recent_hours_window: float = 2.0,
        semantic_kinds: Optional[Iterable[str]] = None,
        semantic_limit: int = 4,
        episodic_limit: int = 1,
    ) -> None:
        self.recent_hours_window = recent_hours_window
        self.semantic_kinds = set(semantic_kinds or {"semantic", "summary", "rule", "preference", "fact", "task"})
        self.semantic_limit = semantic_limit
        self.episodic_limit = episodic_limit

    def build(
        self,
        query: str,
        recalled: List[RetrievedMemory],
        recent_messages: Optional[List[str]] = None,
        recent_message_ids: Optional[List[str]] = None,
        max_items: int = 5,
        max_chars: Optional[int] = None,
        max_estimated_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        recent_messages = recent_messages or []
        recent_message_ids = set(recent_message_ids or [])
        recent_blobs = [self._normalize(text) for text in recent_messages if text]
        progress_query = self._is_progress_query(query)

        ranked = sorted(recalled, key=lambda candidate: self._priority_key(candidate, progress_query=progress_query), reverse=True)
        items: List[ContextItem] = []
        seen: set[str] = set()
        semantic_count = 0
        episodic_count = 0

        for candidate in ranked:
            memory = candidate.memory
            context = getattr(memory, "context", {}) or {}
            source_subtype = str(context.get("source_subtype") or "").strip().lower()
            normalized = self._normalize(self._memory_blob(memory))
            is_state_summary = source_subtype == "assistant_state_summary"
            if not normalized or normalized in seen:
                continue
            if self._is_trivial_text(normalized):
                continue
            if self._is_irrelevant(candidate, progress_query=progress_query) and not is_state_summary:
                continue
            if self._is_recent_chat_echo(memory, recent_message_ids) and not is_state_summary:
                continue

            kind = getattr(memory, "kind", MemoryKind.EPISODIC)
            kind_value = kind.value if hasattr(kind, "value") else str(kind)
            is_semantic = kind_value in self.semantic_kinds or is_state_summary

            if is_semantic and semantic_count >= min(max_items, self.semantic_limit) and not is_state_summary:
                continue
            if (not is_semantic) and episodic_count >= min(max_items, self.episodic_limit):
                continue
            if (not is_semantic) and self._overlaps_recent_context(normalized, recent_blobs):
                continue

            item = self._to_context_item(candidate)
            item_normalized = self._normalize(item.text) if item else ""
            item_signature = self._normalize(self._item_signature(item)) if item else ""
            if not item or not item_normalized:
                continue
            if item_normalized in seen or (item_signature and item_signature in seen):
                continue
            if self._overlaps_recent_context(item_normalized, recent_blobs) and not (progress_query and is_state_summary):
                continue
            if source_subtype in _ASSISTANT_SOURCE_SUBTYPE_PRIORITY and (
                self._overlaps_recent_context(normalized, recent_blobs)
                or (item_signature and self._overlaps_recent_context(item_signature, recent_blobs))
            ) and not (progress_query and is_state_summary):
                continue
            if item_signature and any(
                item_signature == blob or item_signature in blob or blob in item_signature or self._token_overlap(item_signature, blob) >= 0.75
                for blob in seen
            ):
                continue

            if self._would_exceed_budget(items, item, max_chars=max_chars, max_estimated_tokens=max_estimated_tokens):
                continue

            items.append(item)
            seen.add(normalized)
            seen.add(item_normalized)
            if item_signature:
                seen.add(item_signature)
            if is_semantic:
                semantic_count += 1
            else:
                episodic_count += 1
            if len(items) >= max_items:
                break

        context_text = self._render_block(items)
        return {
            "query": query,
            "count": len(items),
            "items": [item.to_dict() for item in items],
            "context_text": context_text,
            "context_chars": len(context_text),
            "estimated_tokens": self._estimate_tokens(context_text),
        }

    def _priority_key(self, candidate: RetrievedMemory, progress_query: bool = False) -> tuple[float, float, float, float, float, float, float, float]:
        memory = candidate.memory
        kind = getattr(memory, "kind", MemoryKind.EPISODIC)
        kind_value = kind.value if hasattr(kind, "value") else str(kind)
        context = getattr(memory, "context", {}) or {}
        source_subtype = str(context.get("source_subtype") or "").strip().lower()
        source_role = str(context.get("role") or "").strip().lower()
        category = str(context.get("category") or "").strip().lower()

        assistant_priority = _ASSISTANT_SOURCE_SUBTYPE_PRIORITY.get(source_subtype, 0.0)
        if source_subtype == "assistant_state_summary":
            assistant_priority = 5.0 if progress_query else 2.0
        semantic_boost = 1.0 if kind_value in self.semantic_kinds else 0.0
        if kind_value == "summary":
            semantic_boost += 0.9 if progress_query else 0.35
        if kind_value == "working":
            semantic_boost += 0.45
        if category in {"state", "state_summary"}:
            semantic_boost += 0.3
        if source_role == "assistant":
            semantic_boost += 0.25

        importance = float(getattr(memory, "importance", 0.5))
        score = candidate.score.total()
        relevance = float(getattr(candidate.score, "relevance", 0.0))
        recency = float(getattr(memory, "access_count", 0))
        freshness = self._freshness_score(memory)
        progress_boost = 1.0 if progress_query and source_subtype == "assistant_state_summary" else 0.0
        return (progress_boost, assistant_priority, relevance, score, semantic_boost, importance, freshness, recency)

    def _is_irrelevant(self, candidate: RetrievedMemory, progress_query: bool = False) -> bool:
        if progress_query:
            return False

        memory = candidate.memory
        kind = getattr(memory, "kind", MemoryKind.EPISODIC)
        kind_value = kind.value if hasattr(kind, "value") else str(kind)
        relevance = float(getattr(candidate.score, "relevance", 0.0))
        context_match = float(getattr(candidate.score, "context_match", 0.0))

        if relevance >= 0.12 or context_match >= 0.5:
            return False

        return kind_value in {"working", "episodic", "semantic", "summary", "rule", "preference", "fact", "task"}

    def _is_recent_chat_echo(self, memory: Any, recent_message_ids: set[str]) -> bool:
        kind = getattr(memory, "kind", MemoryKind.EPISODIC)
        kind_value = kind.value if hasattr(kind, "value") else str(kind)
        if kind_value in self.semantic_kinds:
            return False

        context = getattr(memory, "context", {}) or {}
        if recent_message_ids and context.get("message_id") in recent_message_ids:
            return True

        created_at = getattr(memory, "created_at", None)
        if isinstance(created_at, datetime):
            cutoff = datetime.now() - timedelta(hours=self.recent_hours_window)
            if created_at >= cutoff and context.get("source") == "message":
                return True
        return False

    def _overlaps_recent_context(self, normalized_memory: str, recent_blobs: List[str]) -> bool:
        if not normalized_memory:
            return False
        for blob in recent_blobs:
            if not blob:
                continue
            if normalized_memory == blob:
                return True
            if normalized_memory in blob or blob in normalized_memory:
                return True
            if self._token_overlap(normalized_memory, blob) >= 0.75:
                return True
        return False

    def _to_context_item(self, candidate: RetrievedMemory) -> Optional[ContextItem]:
        memory = candidate.memory
        kind = getattr(memory, "kind", MemoryKind.EPISODIC)
        kind_value = kind.value if hasattr(kind, "value") else str(kind)
        context = getattr(memory, "context", {}) or {}
        source_subtype = str(context.get("source_subtype") or "").strip().lower()
        text: Optional[str] = None

        if source_subtype == "assistant_commit":
            text = f"我承诺的下一步：{context.get('definition') or getattr(memory, 'content', '')}"
        elif source_subtype == "assistant_result":
            text = f"我已确认：{context.get('definition') or getattr(memory, 'content', '')}"
        elif source_subtype == "assistant_decision":
            text = f"我的判断：{context.get('definition') or getattr(memory, 'content', '')}"
        elif source_subtype == "assistant_state":
            text = f"当前进展：{context.get('definition') or getattr(memory, 'content', '')}"
        elif source_subtype == "assistant_state_summary" or kind_value == "summary":
            text = f"状态摘要：{context.get('definition') or getattr(memory, 'content', '')}"
        elif kind_value == "preference":
            text = f"用户偏好：{context.get('definition') or getattr(memory, 'content', '')}"
        elif kind_value == "rule":
            text = f"规则：{context.get('definition') or getattr(memory, 'content', '')}"
        elif kind_value == "fact":
            text = f"事实：{context.get('definition') or getattr(memory, 'content', '')}"
        elif kind_value == "task":
            text = f"待办：{context.get('definition') or getattr(memory, 'content', '')}"
        elif kind_value == "semantic":
            text = f"知识：{context.get('definition') or getattr(memory, 'content', '')}"
        elif kind_value == "episodic":
            text = f"相关历史：{getattr(memory, 'content', '')}"
        elif kind_value == "working":
            text = f"当前相关状态：{getattr(memory, 'content', '')}"
        else:
            text = getattr(memory, 'content', None)

        if not text:
            return None

        return ContextItem(
            kind=kind_value,
            text=text,
            score=candidate.score.total(),
            source=context.get("source") or getattr(memory, "source", None),
            memory_id=getattr(memory, "id", None),
        )

    def _render_block(self, items: List[ContextItem]) -> str:
        if not items:
            return ""
        lines = ["[Brain Recall]"]
        lines.extend(f"- {item.text}" for item in items)
        return "\n".join(lines)

    def _would_exceed_budget(
        self,
        items: List[ContextItem],
        item: ContextItem,
        *,
        max_chars: Optional[int],
        max_estimated_tokens: Optional[int],
    ) -> bool:
        if max_chars is None and max_estimated_tokens is None:
            return False
        trial_text = self._render_block([*items, item])
        if max_chars is not None and len(trial_text) > max_chars:
            return True
        if max_estimated_tokens is not None and self._estimate_tokens(trial_text) > max_estimated_tokens:
            return True
        return False

    def _item_signature(self, item: Optional[ContextItem]) -> str:
        if not item:
            return ""
        return re.sub(r"^[^：:]+[：:]\s*", "", item.text or "")

    def _is_trivial_text(self, text: str) -> bool:
        normalized = self._normalize(text)
        if not normalized:
            return True
        if normalized in _TRIVIAL_TEXTS:
            return True
        if len(normalized) <= 2:
            return True
        if len(normalized) <= 6 and normalized.rstrip("。！？!?.,，") in _TRIVIAL_TEXTS:
            return True
        return False

    def _is_progress_query(self, query: str) -> bool:
        return bool(_PROGRESS_QUERY_RE.search(query or ""))

    def _memory_blob(self, memory: Any) -> str:
        if hasattr(memory, "text_blob"):
            return memory.text_blob()
        return str(getattr(memory, "content", ""))

    def _freshness_score(self, memory: Any) -> float:
        created_at = getattr(memory, "created_at", None)
        if not isinstance(created_at, datetime):
            return 0.0
        age = max((datetime.now() - created_at).total_seconds(), 0.0)
        if age <= 900:
            return 1.0
        if age <= 3600:
            return 0.7
        if age <= 86400:
            return 0.35
        return 0.0

    def _normalize(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def _token_overlap(self, left: str, right: str) -> float:
        left_tokens = set(_WORD_RE.findall(left))
        right_tokens = set(_WORD_RE.findall(right))
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / max(1, min(len(left_tokens), len(right_tokens)))

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        # Conservative heuristic that behaves reasonably for mixed Chinese/English text.
        return max(1, len(text) // 4 + len(_WORD_RE.findall(text)) // 3)
