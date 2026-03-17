"""
情景记忆 (Episodic Memory)

存储个人经历的事件，带有时间戳和情境信息。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time


class EpisodicMemory:
    """情景记忆单元"""
    
    def __init__(
        self,
        content: str,
        context: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        emotion: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ):
        self.id = f"episodic_{int(time.time() * 100000)}"
        self.content = content
        self.context = context
        self.timestamp = timestamp or datetime.now()
        self.emotion = emotion
        self.embedding = embedding
        self.access_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "emotion": self.emotion,
            "access_count": self.access_count
        }


class EpisodicStore:
    """
    情景记忆存储
    
    负责存储和检索带有时间戳的情境记忆。
    """
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.memories: List[EpisodicMemory] = []
    
    def add(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        emotion: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ) -> EpisodicMemory:
        """添加情景记忆"""
        memory = EpisodicMemory(
            content=content,
            context=context or {},
            emotion=emotion,
            embedding=embedding
        )
        
        self.memories.append(memory)
        
        # 容量管理
        if len(self.memories) > self.max_size:
            self.memories.pop(0)  # 移除最旧的
        
        return memory
    
    def get_recent(self, hours: int = 24, limit: int = 50) -> List[EpisodicMemory]:
        """获取最近N小时的情景记忆"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [m for m in self.memories if m.timestamp >= cutoff]
        recent.sort(key=lambda m: m.timestamp, reverse=True)
        return recent[:limit]
    
    def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[EpisodicMemory]:
        """搜索情景记忆"""
        results = []
        query_lower = query.lower()
        
        for memory in self.memories:
            if query_lower in memory.content.lower():
                results.append(memory)
                memory.access_count += 1
        
        results.sort(key=lambda m: m.access_count, reverse=True)
        return results[:limit]
    
    def get_by_context(self, key: str, value: Any, limit: int = 10) -> List[EpisodicMemory]:
        """根据上下文键值搜索"""
        results = [
            m for m in self.memories 
            if m.context.get(key) == value
        ]
        results.sort(key=lambda m: m.timestamp, reverse=True)
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_memories": len(self.memories),
            "max_size": self.max_size,
            "oldest": self.memories[0].timestamp.isoformat() if self.memories else None,
            "newest": self.memories[-1].timestamp.isoformat() if self.memories else None
        }
