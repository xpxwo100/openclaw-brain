"""
海马体 (Hippocampus)

负责记忆的快速编码、模式识别与初步整合。
在睡眠时主导记忆巩固过程。
"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime


class MemoryItem:
    """记忆单元"""
    
    def __init__(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        embedding: Optional[List[float]] = None
    ):
        self.id = f"mem_{int(time.time() * 1000)}"
        self.content = content
        self.context = context or {}
        self.importance = importance
        self.embedding = embedding
        self.created_at = datetime.now()
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "context": self.context,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count
        }


class Hippocampus:
    """
    海马体记忆系统
    
    负责：
    - 快速编码新事件
    - 模式识别与关联
    - 睡眠时巩固到长期记忆
    """
    
    def __init__(
        self,
        capacity: int = 1000,
        encoding_interval_minutes: int = 30
    ):
        self.capacity = capacity
        self.encoding_interval_minutes = encoding_interval_minutes
        self.encoding_buffer: List[MemoryItem] = []
        self.associations: Dict[str, List[str]] = {}
        self.last_consolidation = time.time()
    
    def encode(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        embedding: Optional[List[float]] = None
    ) -> MemoryItem:
        """
        快速编码新事件到海马体
        
        Args:
            content: 记忆内容
            context: 上下文信息
            importance: 重要性 (0-1)
            embedding: 向量嵌入（可选）
        
        Returns:
            MemoryItem: 创建的记忆单元
        """
        memory = MemoryItem(
            content=content,
            context=context,
            importance=importance,
            embedding=embedding
        )
        
        self.encoding_buffer.append(memory)
        
        # 如果超过容量，移除最旧的低重要性记忆
        if len(self.encoding_buffer) > self.capacity:
            self._prune_buffer()
        
        # 更新关联
        self._update_associations(memory)
        
        return memory
    
    def _prune_buffer(self):
        """修剪缓冲区，移除低重要性记忆"""
        # 按重要性排序，保留最重要的
        self.encoding_buffer.sort(key=lambda m: m.importance, reverse=True)
        self.encoding_buffer = self.encoding_buffer[:self.capacity]
    
    def _update_associations(self, memory: MemoryItem):
        """更新记忆关联"""
        # 基于上下文或关键词创建关联
        context_key = memory.context.get("source", "default")
        if context_key not in self.associations:
            self.associations[context_key] = []
        self.associations[context_key].append(memory.id)
    
    def get_recent_memories(self, limit: int = 10) -> List[MemoryItem]:
        """获取最近的记忆"""
        sorted_memories = sorted(
            self.encoding_buffer,
            key=lambda m: m.created_at,
            reverse=True
        )
        return sorted_memories[:limit]
    
    def consolidate(self) -> int:
        """
        执行记忆巩固
        
        Returns:
            int: 巩固的记忆数量
        """
        count = len(self.encoding_buffer)
        self.last_consolidation = time.time()
        return count
    
    def search(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.3
    ) -> List[MemoryItem]:
        """
        搜索记忆
        
        Args:
            query: 查询文本
            limit: 返回数量限制
            threshold: 相似度阈值
        
        Returns:
            List[MemoryItem]: 匹配的记忆列表
        """
        # 简单的文本匹配搜索
        results = []
        for memory in self.encoding_buffer:
            if query.lower() in memory.content.lower():
                results.append(memory)
        
        # 按重要性排序
        results.sort(key=lambda m: m.importance, reverse=True)
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "buffer_size": len(self.encoding_buffer),
            "capacity": self.capacity,
            "associations_count": len(self.associations),
            "last_consolidation": self.last_consolidation
        }
