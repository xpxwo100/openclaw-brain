"""
记忆提取 (Memory Retrieval)

基于情境、情绪、关联度的智能检索。
"""

from typing import List, Dict, Any, Optional, Callable
import time


class RetrievalScore:
    """检索评分"""
    
    def __init__(
        self,
        relevance: float,
        recency: float,
        importance: float,
        context_match: float = 0.0,
        emotion_match: float = 0.0,
        association_strength: float = 0.0
    ):
        self.relevance = relevance
        self.recency = recency
        self.importance = importance
        self.context_match = context_match
        self.emotion_match = emotion_match
        self.association_strength = association_strength
    
    def total(self, weights: Optional[Dict[str, float]] = None) -> float:
        """计算总评分"""
        weights = weights or {
            "relevance": 0.4,
            "recency": 0.2,
            "importance": 0.2,
            "context_match": 0.1,
            "emotion_match": 0.05,
            "association_strength": 0.05
        }
        
        return (
            self.relevance * weights["relevance"] +
            self.recency * weights["recency"] +
            self.importance * weights["importance"] +
            self.context_match * weights["context_match"] +
            self.emotion_match * weights["emotion_match"] +
            self.association_strength * weights["association_strength"]
        )


class RetrievedMemory:
    """检索到的记忆"""
    
    def __init__(
        self,
        memory: Any,
        score: RetrievalScore,
        matched_terms: Optional[List[str]] = None
    ):
        self.memory = memory
        self.score = score
        self.matched_terms = matched_terms or []
    
    def __repr__(self):
        return f"RetrievedMemory(score={self.score.total():.3f})"


class MemoryRetriever:
    """
    记忆检索系统
    
    基于多维度评分的智能检索。
    """
    
    def __init__(
        self,
        default_limit: int = 10,
        min_score_threshold: float = 0.1
    ):
        self.default_limit = default_limit
        self.min_score_threshold = min_score_threshold
    
    def retrieve(
        self,
        query: str,
        memories: List[Any],
        context: Optional[Dict[str, Any]] = None,
        emotion: Optional[str] = None,
        limit: Optional[int] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> List[RetrievedMemory]:
        """
        检索记忆
        
        Args:
            query: 查询文本
            memories: 记忆列表
            context: 上下文信息
            emotion: 情绪状态
            limit: 返回数量限制
            weights: 评分权重
        
        Returns:
            List[RetrievedMemory]: 按相关性排序的记忆列表
        """
        if not memories:
            return []
        
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        
        results = []
        current_time = time.time()
        
        for memory in memories:
            # 计算相关性
            relevance = self._calculate_relevance(
                query_lower, query_terms, memory
            )
            
            # 计算时间衰减
            recency = self._calculate_recency(memory, current_time)
            
            # 获取重要性
            importance = getattr(memory, "importance", 0.5)
            
            # 上下文匹配
            context_match = self._calculate_context_match(
                context or {}, memory
            )
            
            # 情绪匹配
            emotion_match = self._calculate_emotion_match(
                emotion, memory
            )
            
            # 关联强度
            association = self._calculate_association(memory)
            
            score = RetrievalScore(
                relevance=relevance,
                recency=recency,
                importance=importance,
                context_match=context_match,
                emotion_match=emotion_match,
                association_strength=association
            )
            
            if score.total() >= self.min_score_threshold:
                results.append(RetrievedMemory(
                    memory=memory,
                    score=score,
                    matched_terms=list(query_terms)
                ))
        
        # 按总评分排序
        results.sort(key=lambda r: r.score.total(weights), reverse=True)
        
        limit = limit or self.default_limit
        return results[:limit]
    
    def _calculate_relevance(
        self,
        query: str,
        query_terms: set,
        memory: Any
    ) -> float:
        """计算相关性"""
        content = getattr(memory, "content", "")
        if not content:
            return 0.0
        
        content_lower = content.lower()
        
        # 精确匹配
        if query in content_lower:
            return 1.0
        
        # 关键词匹配
        content_terms = set(content_lower.split())
        matches = len(query_terms & content_terms)
        
        if matches > 0:
            return min(matches / len(query_terms), 1.0)
        
        return 0.0
    
    def _calculate_recency(self, memory: Any, current_time: float) -> float:
        """计算时间衰减"""
        created_at = getattr(memory, "created_at", None)
        if not created_at:
            return 0.5
        
        if hasattr(created_at, "timestamp"):
            age_seconds = current_time - created_at.timestamp()
        elif hasattr(created_at, "timestamp"):
            age_seconds = current_time - created_at.timestamp()
        else:
            return 0.5
        
        # 使用指数衰减：1小时后衰减到50%
        age_hours = age_seconds / 3600
        return math.exp(-age_hours) if age_hours > 0 else 1.0
    
    def _calculate_context_match(
        self,
        context: Dict[str, Any],
        memory: Any
    ) -> float:
        """计算上下文匹配"""
        if not context:
            return 0.0
        
        memory_context = getattr(memory, "context", {})
        if not memory_context:
            return 0.0
        
        matches = 0
        total = len(context)
        
        for key, value in context.items():
            if key in memory_context and memory_context[key] == value:
                matches += 1
        
        return matches / total if total > 0 else 0.0
    
    def _calculate_emotion_match(
        self,
        emotion: Optional[str],
        memory: Any
    ) -> float:
        """计算情绪匹配"""
        if not emotion:
            return 0.0
        
        memory_emotion = getattr(memory, "emotion", None)
        if not memory_emotion:
            return 0.0
        
        return 1.0 if memory_emotion == emotion else 0.0
    
    def _calculate_association(self, memory: Any) -> float:
        """计算关联强度"""
        # 简化的关联计算
        access_count = getattr(memory, "access_count", 0)
        
        # 归一化访问次数
        return min(access_count / 10.0, 1.0)


import math  # 确保 math 被导入
