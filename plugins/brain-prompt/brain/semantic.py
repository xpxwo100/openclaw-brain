"""Semantic memory store for facts, rules, and preferences."""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Set

from .base import MemoryKind, MemoryRecord


class SemanticConcept:
    def __init__(
        self,
        name: str,
        definition: str,
        category: str = "general",
        relations: Optional[Dict[str, List[str]]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ):
        self.id = f"concept_{uuid.uuid4().hex[:12]}"
        self.name = name
        self.definition = definition
        self.category = category
        self.relations = relations or {"is_a": [], "related_to": [], "part_of": []}
        self.properties = properties or {}
        self.created_at = time.time()
        self.access_count = 0

    def add_relation(self, rel_type: str, target_id: str) -> None:
        self.relations.setdefault(rel_type, [])
        if target_id not in self.relations[rel_type]:
            self.relations[rel_type].append(target_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "definition": self.definition,
            "category": self.category,
            "relations": self.relations,
            "properties": self.properties,
            "access_count": self.access_count,
        }

    def to_memory_record(self, importance: float = 0.7) -> MemoryRecord:
        category_map = {
            "rule": MemoryKind.RULE,
            "preference": MemoryKind.PREFERENCE,
            "fact": MemoryKind.FACT,
            "task": MemoryKind.TASK,
            "summary": MemoryKind.SUMMARY,
            "state_summary": MemoryKind.SUMMARY,
        }
        kind = category_map.get(self.category, MemoryKind.SEMANTIC)
        return MemoryRecord(
            content=self.name,
            kind=kind,
            context={"definition": self.definition, "category": self.category},
            importance=importance,
            metadata={"relations": self.relations, **self.properties},
            access_count=self.access_count,
        )


class SemanticStore:
    def __init__(self):
        self.concepts: Dict[str, SemanticConcept] = {}
        self.name_index: Dict[str, Set[str]] = {}

    def add_concept(
        self,
        name: str,
        definition: str,
        category: str = "general",
        relations: Optional[Dict[str, List[str]]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> SemanticConcept:
        existing = self.find_by_name(name)
        if existing:
            existing.definition = definition
            existing.category = category
            if properties:
                existing.properties.update(properties)
            return existing

        concept = SemanticConcept(
            name=name,
            definition=definition,
            category=category,
            relations=relations,
            properties=properties,
        )
        self.concepts[concept.id] = concept
        key = name.lower()
        self.name_index.setdefault(key, set()).add(concept.id)
        return concept

    def get_concept(self, concept_id: str) -> Optional[SemanticConcept]:
        concept = self.concepts.get(concept_id)
        if concept:
            concept.access_count += 1
        return concept

    def find_by_name(self, name: str) -> Optional[SemanticConcept]:
        concept_ids = self.name_index.get(name.lower(), set())
        for concept_id in concept_ids:
            return self.concepts.get(concept_id)
        return None

    def search(self, query: str, limit: int = 10) -> List[SemanticConcept]:
        query_lower = query.lower()
        results = []
        for concept in self.concepts.values():
            haystack = f"{concept.name} {concept.definition}".lower()
            if query_lower in haystack:
                concept.access_count += 1
                results.append(concept)
        results.sort(key=lambda item: (item.access_count, item.name), reverse=True)
        return results[:limit]

    def get_by_category(self, category: str) -> List[SemanticConcept]:
        return [concept for concept in self.concepts.values() if concept.category == category]

    def add_relation(self, concept_id: str, rel_type: str, target_id: str) -> bool:
        concept = self.concepts.get(concept_id)
        if concept and target_id in self.concepts:
            concept.add_relation(rel_type, target_id)
            return True
        return False

    def get_related(self, concept_id: str, rel_type: str) -> List[SemanticConcept]:
        concept = self.concepts.get(concept_id)
        if not concept:
            return []
        return [self.concepts[target_id] for target_id in concept.relations.get(rel_type, []) if target_id in self.concepts]

    def get_stats(self) -> Dict[str, Any]:
        categories: Dict[str, int] = {}
        for concept in self.concepts.values():
            categories[concept.category] = categories.get(concept.category, 0) + 1
        return {
            "total_concepts": len(self.concepts),
            "categories": categories,
            "indexed_names": len(self.name_index),
        }
