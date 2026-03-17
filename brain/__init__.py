"""
OpenClaw Brain - 类脑记忆系统

模拟人脑的多层级记忆、注意力门控与记忆巩固机制
"""

from .attention import AttentionGate
from .working_memory import WorkingMemory
from .hippocampus import Hippocampus
from .episodic import EpisodicStore
from .semantic import SemanticStore
from .consolidation import SleepConsolidation
from .retrieval import MemoryRetriever

__version__ = "0.1.0"
__author__ = "OpenClaw Brain Contributors"

__all__ = [
    "AttentionGate",
    "WorkingMemory",
    "Hippocampus",
    "EpisodicStore",
    "SemanticStore",
    "SleepConsolidation",
    "MemoryRetriever",
]
