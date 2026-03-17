"""
语义记忆 (Semantic Memory)

存储事实、概念、规则等结构化知识。
"""

from typing import List, Dict, Any, Optional, Set
import time
import uuid


class SemanticConcept:
    """语义概念单元"""
    
    def __init__(
        self,
        name: str,
        definition: str,
        category: str = "general",
        relations: Optional[Dict[str, List[str]]] = None,
        properties: Optional[Dict[str, Any]] = None
    ):
        self.id = f"concept_{uuid.uuid4().hex[:12]}"
        self.name = name
        self.definition = definition
        self.category = category
        self.relations = relations or {
            "is_a": [],
            "related_to": [],
            "part_of": []
        }
        self.properties = properties or {}
        self.created_at = time.time()
        self.access_count = 0
    
    def add_relation(self, rel_type: str, target_id: str):
        """添加关系"""
        if rel_type in self.relations:
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
            "access_count": self.access_count
        }


class SemanticStore:
    """
    语义记忆存储
    
    存储结构化知识、概念网络和事实。
    """
    
    def __init__(self):
        self.concepts: Dict[str, SemanticConcept] = {}
        self.name_index: Dict[str, Set[str]] = {}  # name -> concept_ids
    
    def add_concept(
        self,
        name: str,
        definition: str,
        category: str = "general",
        relations: Optional[Dict[str, List[str]]] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> SemanticConcept:
        """添加概念"""
        concept = SemanticConcept(
            name=name,
            definition=definition,
            category=category,
            relations=relations,
            properties=properties
        )
        
        self.concepts[concept.id] = concept
        
        # 更新索引
        name_lower = name.lower()
        if name_lower not in self.name_index:
            self.name_index[name_lower] = set()
        self.name_index[name_lower].add(concept.id)
        
        return concept
    
    def get_concept(self, concept_id: str) -> Optional[SemanticConcept]:
        """获取概念"""
        concept = self.concepts.get(concept_id)
        if concept:
            concept.access_count += 1
        return concept
    
    def search(self, query: str, limit: int = 10) -> List[SemanticConcept]:
        """搜索概念"""
        query_lower = query.lower()
        results = []
        
        for concept in self.concepts.values():
            if query_lower in concept.name.lower() or query_lower in concept.definition.lower():
                concept.access_count += 1
                results.append(concept)
        
        # 按访问次数和相关性排序
        results.sort(key=lambda c: (c.access_count, c.name), reverse=True)
        return results[:limit]
    
    def get_by_category(self, category: str) -> List[SemanticConcept]:
        """按类别获取概念"""
        return [
            c for c in self.concepts.values() 
            if c.category == category
        ]
    
    def add_relation(
        self,
        concept_id: str,
        rel_type: str,
        target_id: str
    ) -> bool:
        """添加概念间的关系"""
        concept = self.concepts.get(concept_id)
        if concept and target_id in self.concepts:
            concept.add_relation(rel_type, target_id)
            return True
        return False
    
    def get_related(self, concept_id: str, rel_type: str) -> List[SemanticConcept]:
        """获取相关概念"""
        concept = self.concepts.get(concept_id)
        if not concept:
            return []
        
        related_ids = concept.relations.get(rel_type, [])
        return [
            self.concepts[rid] 
            for rid in related_ids 
            if rid in self.concepts
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        categories: Dict[str, int] = {}
        for concept in self.concepts.values():
            categories[concept.category] = categories.get(concept.category, 0) + 1
        
        return {
            "total_concepts": len(self.concepts),
            "categories": categories,
            "indexed_names": len(self.name_index)
        }
