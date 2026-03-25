"""Memory retrieval and reranking across heterogeneous memory objects."""

from __future__ import annotations

import math
import re
import time
from typing import Any, Dict, List, Optional

_WORD_RE = re.compile(r"[A-Za-z0-9_]+", re.UNICODE)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


class RetrievalScore:
    def __init__(
        self,
        relevance: float,
        recency: float,
        importance: float,
        context_match: float = 0.0,
        emotion_match: float = 0.0,
        association_strength: float = 0.0,
    ):
        self.relevance = relevance
        self.recency = recency
        self.importance = importance
        self.context_match = context_match
        self.emotion_match = emotion_match
        self.association_strength = association_strength

    def total(self, weights: Optional[Dict[str, float]] = None) -> float:
        weights = weights or {
            "relevance": 0.45,
            "recency": 0.2,
            "importance": 0.2,
            "context_match": 0.1,
            "emotion_match": 0.03,
            "association_strength": 0.02,
        }
        return (
            self.relevance * weights["relevance"]
            + self.recency * weights["recency"]
            + self.importance * weights["importance"]
            + self.context_match * weights["context_match"]
            + self.emotion_match * weights["emotion_match"]
            + self.association_strength * weights["association_strength"]
        )


class RetrievedMemory:
    def __init__(self, memory: Any, score: RetrievalScore, matched_terms: Optional[List[str]] = None):
        self.memory = memory
        self.score = score
        self.matched_terms = matched_terms or []

    def __repr__(self) -> str:
        return f"RetrievedMemory(score={self.score.total():.3f})"


class MemoryRetriever:
    def __init__(self, default_limit: int = 10, min_score_threshold: float = 0.1):
        self.default_limit = default_limit
        self.min_score_threshold = min_score_threshold

    def retrieve(
        self,
        query: str,
        memories: List[Any],
        context: Optional[Dict[str, Any]] = None,
        emotion: Optional[str] = None,
        limit: Optional[int] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> List[RetrievedMemory]:
        if not memories:
            return []

        query_lower = query.lower()
        query_terms = set(query_lower.split())
        results: List[RetrievedMemory] = []
        current_time = time.time()

        for memory in memories:
            relevance = self._calculate_relevance(query_lower, query_terms, memory)
            recency = self._calculate_recency(memory, current_time)
            importance = float(getattr(memory, "importance", 0.5))
            context_match = self._calculate_context_match(context or {}, memory)
            emotion_match = self._calculate_emotion_match(emotion, memory)
            association = self._calculate_association(memory)

            score = RetrievalScore(
                relevance=relevance,
                recency=recency,
                importance=importance,
                context_match=context_match,
                emotion_match=emotion_match,
                association_strength=association,
            )
            total = score.total(weights)
            if total >= self.min_score_threshold:
                results.append(RetrievedMemory(memory=memory, score=score, matched_terms=sorted(query_terms)))

        results.sort(key=lambda item: item.score.total(weights), reverse=True)
        return results[: (limit or self.default_limit)]

    def _memory_text(self, memory: Any) -> str:
        if hasattr(memory, "text_blob"):
            return memory.text_blob()
        content = getattr(memory, "content", None)
        if content:
            return str(content)
        name = getattr(memory, "name", "")
        definition = getattr(memory, "definition", "")
        return f"{name} {definition}".strip()

    def _calculate_relevance(self, query: str, query_terms: set[str], memory: Any) -> float:
        content_lower = self._memory_text(memory).lower()
        if not content_lower:
            return 0.0
        if query in content_lower:
            return 1.0
        query_tokens = self._tokenize(query)
        content_tokens = self._tokenize(content_lower)
        if not query_tokens or not content_tokens:
            return 0.0

        query_token_set = set(query_tokens)
        content_token_set = set(content_tokens)
        token_matches = len(query_token_set & content_token_set) / max(1, len(query_token_set))

        query_ngrams = self._char_ngrams(query)
        content_ngrams = self._char_ngrams(content_lower)
        ngram_matches = 0.0
        if query_ngrams and content_ngrams:
            ngram_matches = len(query_ngrams & content_ngrams) / max(1, len(query_ngrams))

        return min(max(token_matches, ngram_matches), 1.0)

    def _tokenize(self, text: str) -> List[str]:
        text = (text or "").lower()
        tokens = [token for token in _WORD_RE.findall(text) if token]
        for segment in _CJK_RE.findall(text):
            if len(segment) == 1:
                tokens.append(segment)
                continue
            tokens.extend(segment[index:index + 2] for index in range(len(segment) - 1))
        return tokens

    def _char_ngrams(self, text: str, size: int = 2) -> set[str]:
        cleaned = re.sub(r"\s+", "", (text or "").lower())
        if len(cleaned) < size:
            return {cleaned} if cleaned else set()
        return {cleaned[index:index + size] for index in range(len(cleaned) - size + 1)}

    def _calculate_recency(self, memory: Any, current_time: float) -> float:
        created_at = getattr(memory, "created_at", None)
        if created_at is None:
            return 0.5
        if hasattr(created_at, "timestamp"):
            age_seconds = current_time - created_at.timestamp()
        elif isinstance(created_at, (int, float)):
            age_seconds = current_time - float(created_at)
        else:
            return 0.5
        age_hours = max(age_seconds, 0.0) / 3600.0
        return math.exp(-age_hours / 24.0)

    def _calculate_context_match(self, context: Dict[str, Any], memory: Any) -> float:
        if not context:
            return 0.0
        memory_context = getattr(memory, "context", {}) or {}
        if not memory_context:
            return 0.0
        matches = sum(1 for key, value in context.items() if memory_context.get(key) == value)
        return matches / len(context)

    def _calculate_emotion_match(self, emotion: Optional[str], memory: Any) -> float:
        if not emotion:
            return 0.0
        return 1.0 if getattr(memory, "emotion", None) == emotion else 0.0

    def _calculate_association(self, memory: Any) -> float:
        access_count = getattr(memory, "access_count", 0)
        strength = getattr(memory, "strength", 0.5)
        return min((access_count / 10.0) * 0.5 + strength * 0.5, 1.0)
