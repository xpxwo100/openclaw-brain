"""
记忆巩固 (Memory Consolidation)

模拟睡眠时的记忆重放、整合与强化过程。
应用艾宾浩斯遗忘曲线。
"""

from typing import List, Dict, Any, Optional
import math
import time


class EbbinghausCurve:
    """艾宾浩斯遗忘曲线"""
    
    def __init__(self, halflife_hours: float = 24.0):
        self.halflife_hours = halflife_hours
    
    def retention(self, hours: float) -> float:
        """
        计算记忆保留率
        
        Args:
            hours: 距离上次复习的小时数
        
        Returns:
            float: 保留率 (0-1)
        """
        # 使用指数衰减模型: R = e^(-t/S)
        # 其中 S 是半衰期
        return math.exp(-hours / self.halflife_hours)
    
    def next_review(self, current_retention: float) -> Optional[float]:
        """
        计算下次复习时间
        
        Args:
            current_retention: 当前保留率
        
        Returns:
            float: 距离下次复习的小时数，如果不需要复习返回None
        """
        if current_retention > 0.9:
            return None  # 记忆仍然清晰
        
        # 反推时间: t = -S * ln(R)
        hours = -self.halflife_hours * math.log(current_retention)
        return max(hours, 0.1)


class MemoryStrength:
    """记忆强度"""
    
    def __init__(
        self,
        initial_strength: float = 0.5,
        max_strength: float = 1.0
    ):
        self.strength = initial_strength
        self.max_strength = max_strength
        self.last_review = time.time()
    
    def strengthen(self, factor: float = 1.2):
        """强化记忆"""
        self.strength = min(self.strength * factor, self.max_strength)
        self.last_review = time.time()
    
    def decay(self, hours: float, curve: EbbinghausCurve):
        """应用遗忘曲线衰减"""
        retention = curve.retention(hours)
        self.strength *= retention
    
    def apply_forgetting(self, curve: EbbinghausCurve):
        """应用遗忘"""
        hours = (time.time() - self.last_review) / 3600
        self.decay(hours, curve)


class SleepConsolidation:
    """
    睡眠记忆巩固
    
    模拟睡眠时的记忆重放和整合过程。
    """
    
    def __init__(
        self,
        halflife_hours: float = 24.0,
        replay_factor: float = 1.5,
        prune_threshold: float = 0.1
    ):
        self.curve = EbbinghausCurve(halflife_hours)
        self.replay_factor = replay_factor
        self.prune_threshold = prune_threshold
        self.last_consolidation = time.time()
        self.consolidation_count = 0
    
    def consolidate(
        self,
        memories: List[MemoryStrength]
    ) -> Dict[str, Any]:
        """
        执行记忆巩固
        
        Args:
            memories: 需要巩固的记忆列表
        
        Returns:
            Dict: 巩固结果统计
        """
        result = {
            "strengthened": 0,
            "weakened": 0,
            "pruned": 0,
            "total": len(memories)
        }
        
        for memory in memories:
            # 应用遗忘
            memory.apply_forgetting(self.curve)
            
            # 如果记忆强度足够，进行重放强化
            if memory.strength > 0.3:
                memory.strengthen(self.replay_factor)
                result["strengthened"] += 1
            else:
                result["weakened"] += 1
            
            # 修剪过弱的记忆
            if memory.strength < self.prune_threshold:
                result["pruned"] += 1
        
        self.last_consolidation = time.time()
        self.consolidation_count += 1
        
        return result
    
    def should_consolidate(self, interval_hours: float = 4.0) -> bool:
        """
        检查是否应该执行巩固
        
        Args:
            interval_hours: 巩固间隔（小时）
        
        Returns:
            bool: 是否应该执行巩固
        """
        hours_since = (time.time() - self.last_consolidation) / 3600
        return hours_since >= interval_hours
    
    def time_until_next(self, interval_hours: float = 4.0) -> float:
        """距离下次巩固的时间（小时）"""
        hours_since = (time.time() - self.last_consolidation) / 3600
        return max(0, interval_hours - hours_since)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "last_consolidation": self.last_consolidation,
            "consolidation_count": self.consolidation_count,
            "halflife_hours": self.curve.halflife_hours,
            "replay_factor": self.replay_factor,
            "prune_threshold": self.prune_threshold
        }
