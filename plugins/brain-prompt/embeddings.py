"""Embedding helpers for OpenClaw Brain.

Prefer sentence-transformers when available; fall back to deterministic hashing
so recall keeps working offline and in constrained environments.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from functools import lru_cache
from typing import Iterable, List, Sequence

import numpy as np

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_HASH_DIM = 128


class _HashingEmbedder:
    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        return [_hash_embed(text) for text in texts]


@lru_cache(maxsize=1)
def _get_sentence_transformer():
    model_name = os.environ.get("OPENCLAW_BRAIN_EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip() or "all-MiniLM-L6-v2"
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


@lru_cache(maxsize=1)
def _get_embedder():
    preferred = (os.environ.get("OPENCLAW_BRAIN_EMBEDDER") or "auto").strip().lower()
    if preferred == "hash":
        return _HashingEmbedder()

    try:
        return _get_sentence_transformer()
    except Exception:
        return _HashingEmbedder()


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    cleaned = [str(text or "").strip() for text in texts]
    if not cleaned:
        return []

    embedder = _get_embedder()
    vectors = embedder.encode(cleaned)
    return [_normalize_vector(vector) for vector in vectors]


def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right:
        return 0.0
    a = np.asarray(left, dtype=np.float32)
    b = np.asarray(right, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _hash_embed(text: str) -> List[float]:
    vector = np.zeros(_HASH_DIM, dtype=np.float32)
    tokens = _TOKEN_RE.findall((text or "").lower())
    if not tokens:
        return vector.tolist()

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % _HASH_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + (digest[5] / 255.0) * 0.25
        vector[bucket] += sign * weight
    return _normalize_vector(vector)


def _normalize_vector(vector: Iterable[float]) -> List[float]:
    arr = np.asarray(list(vector), dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm <= 0.0:
        return arr.tolist()
    return (arr / norm).astype(np.float32).tolist()
