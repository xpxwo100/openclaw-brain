"""OpenClaw Brain package.

Refactored around a unified memory model and a top-level orchestrator while
keeping the original public modules available.
"""

from .attention import AttentionGate, AttentionResult
from .base import MemoryKind, MemoryRecord, ScoredMemory
from .consolidation import EbbinghausCurve, MemoryStrength, SleepConsolidation
from .context import BrainContextBuilder, ContextItem
from .episodic import EpisodicMemory, EpisodicStore
from .hippocampus import Hippocampus, MemoryItem
from .orchestrator import OpenClawBrain
from .repository import InMemoryRepository
from .retrieval import MemoryRetriever, RetrievedMemory, RetrievalScore
from .semantic import SemanticConcept, SemanticStore
from .working_memory import WorkingMemory, WorkingMemoryItem

__version__ = "0.2.0"
__author__ = "OpenClaw Brain Contributors"

__all__ = [
    "AttentionGate",
    "AttentionResult",
    "MemoryKind",
    "MemoryRecord",
    "ScoredMemory",
    "WorkingMemoryItem",
    "WorkingMemory",
    "ContextItem",
    "BrainContextBuilder",
    "MemoryItem",
    "Hippocampus",
    "EpisodicMemory",
    "EpisodicStore",
    "SemanticConcept",
    "SemanticStore",
    "EbbinghausCurve",
    "MemoryStrength",
    "SleepConsolidation",
    "RetrievalScore",
    "RetrievedMemory",
    "MemoryRetriever",
    "InMemoryRepository",
    "OpenClawBrain",
]
