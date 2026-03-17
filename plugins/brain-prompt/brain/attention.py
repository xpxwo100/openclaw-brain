"""
注意力门控 (Attention Gate)

模拟人脑的选择性注意机制，决定哪些信息值得进入记忆系统。

核心机制：
1. 优先级过滤：检测 P0/P1/P2 等优先级标记
2. 情绪标记：识别用户强调、纠正、否定等情绪信号
3. 关联触发：与现有记忆强相关的信息更容易通过
4. 重复增强：同一信息多次出现会提高权重
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AttentionResult:
    """注意力决策结果"""
    passed: bool
    score: float
    reasons: List[str]
    priority: str  # "P0", "P1", "P2", "normal"
    emotional_weight: float


class AttentionGate:
    """注意力门控"""
    
    def __init__(
        self,
        priority_keywords: Optional[List[str]] = None,
        emotional_triggers: Optional[List[str]] = None,
        importance_phrases: Optional[List[str]] = None,
        threshold: float = 0.5
    ):
        """
        初始化注意力门控
        
        Args:
            priority_keywords: 优先级关键词列表 (如 ["P0", "P1", "P2"])
            emotional_triggers: 情绪触发词 (如 ["记住", "重要", "注意"])
            importance_phrases: 重要性短语 (如 ["千万", "一定", "必须"])
            threshold: 通过阈值 (0-1)
        """
        self.threshold = threshold
        
        # 默认优先级关键词
        self.priority_keywords = priority_keywords or [
            "P0", "P1", "P2", 
            "优先", "高优", "紧急",
            "关键", "核心", "重点"
        ]
        
        # 默认情绪触发词
        self.emotional_triggers = emotional_triggers or [
            "记住", "重要", "注意", "留意",
            "纠正", "不对", "错了", "不是",
            "强调", "一定", "必须", "千万"
        ]
        
        # 默认重要性短语
        self.importance_phrases = importance_phrases or [
            "长期保留", "一直有效", "形成规则",
            "写进记忆", "记下来", "别忘了"
        ]
        
        # 重复计数（短期去重）
        self.repetition_count: Dict[str, int] = {}
    
    def should_pass(
        self,
        text: str,
        context: Optional[Dict] = None,
        existing_memories: Optional[List] = None
    ) -> AttentionResult:
        """
        判断信息是否应该通过注意力门控
        
        Args:
            text: 输入文本
            context: 上下文信息 (用户、时间、地点等)
            existing_memories: 现有记忆列表（用于关联度计算）
        
        Returns:
            AttentionResult: 决策结果
        """
        score = 0.0
        reasons = []
        priority = "normal"
        emotional_weight = 1.0
        
        # 1. 检测优先级标记
        priority_score, priority_reason, priority = self._check_priority(text)
        if priority_score > 0:
            score += priority_score
            reasons.append(priority_reason)
        
        # 2. 检测情绪触发
        emotional_score, emotional_reason = self._check_emotional_triggers(text)
        if emotional_score > 0:
            score += emotional_score
            emotional_weight = 1.0 + (emotional_score * 0.5)  # 情绪增强
            reasons.append(emotional_reason)
        
        # 3. 检测重要性短语
        importance_score, importance_reason = self._check_importance_phrases(text)
        if importance_score > 0:
            score += importance_score
            reasons.append(importance_reason)
        
        # 4. 关联度检查（如果有现有记忆）
        if existing_memories:
            association_score, association_reason = self._check_association(
                text, existing_memories
            )
            if association_score > 0:
                score += association_score * 0.3  # 关联度权重较低
                reasons.append(association_reason)
        
        # 5. 重复增强
        repetition_bonus = self._get_repetition_bonus(text)
        if repetition_bonus > 0:
            score += repetition_bonus
            reasons.append(f"重复出现 (+{repetition_bonus:.2f})")
        
        # 标准化分数到 0-1
        score = min(1.0, score)
        
        return AttentionResult(
            passed=score >= self.threshold,
            score=score,
            reasons=reasons,
            priority=priority,
            emotional_weight=emotional_weight
        )
    
    def _check_priority(self, text: str) -> Tuple[float, str, str]:
        """检查优先级标记"""
        text_upper = text.upper()
        
        # P0/P1/P2 检测
        if "P0" in text_upper or "P0" in text:
            return 1.0, "包含 P0 优先级", "P0"
        if "P1" in text_upper or "P1" in text:
            return 0.8, "包含 P1 优先级", "P1"
        if "P2" in text_upper or "P2" in text:
            return 0.6, "包含 P2 优先级", "P2"
        
        # 使用实例变量中的优先级关键词
        for keyword in self.priority_keywords:
            if keyword in text:
                return 0.7, f"包含优先级关键词'{keyword}'", "P1"
        
        return 0.0, "", "normal"
    
    def _check_emotional_triggers(self, text: str) -> Tuple[float, str]:
        """检查情绪触发词"""
        found_triggers = []
        for trigger in self.emotional_triggers:
            if trigger in text:
                found_triggers.append(trigger)
        
        if found_triggers:
            return 0.5, f"包含情绪触发词：{', '.join(found_triggers)}"
        return 0.0, ""
    
    def _check_importance_phrases(self, text: str) -> Tuple[float, str]:
        """检查重要性短语"""
        found_phrases = []
        for phrase in self.importance_phrases:
            if phrase in text:
                found_phrases.append(phrase)
        
        if found_phrases:
            return 0.4, f"包含重要性短语：{', '.join(found_phrases)}"
        return 0.0, ""
    
    def _check_association(
        self,
        text: str,
        existing_memories: List
    ) -> Tuple[float, str]:
        """检查与现有记忆的关联度"""
        # 简单实现：关键词重叠
        text_words = set(re.split(r'\W+', text.lower()))
        
        max_overlap = 0.0
        for memory in existing_memories:
            memory_text = getattr(memory, 'text', str(memory)).lower()
            memory_words = set(re.split(r'\W+', memory_text))
            overlap = len(text_words & memory_words) / max(1, len(text_words))
            max_overlap = max(max_overlap, overlap)
        
        if max_overlap > 0.3:
            return 0.3, f"与现有记忆关联度：{max_overlap:.2f}"
        return 0.0, ""
    
    def _get_repetition_bonus(self, text: str) -> float:
        """获取重复出现 bonus"""
        # 简单哈希
        text_hash = hash(text)
        self.repetition_count[text_hash] = self.repetition_count.get(text_hash, 0) + 1
        count = self.repetition_count[text_hash]
        
        # 重复越多 bonus 越高，但递减
        if count == 1:
            return 0.0
        elif count == 2:
            return 0.1
        elif count == 3:
            return 0.15
        else:
            return 0.2
    
    def reset_repetition(self):
        """重置重复计数（定期清理）"""
        self.repetition_count.clear()


# 使用示例
if __name__ == "__main__":
    gate = AttentionGate()
    
    # Test cases
    test_cases = [
        "\u8bb0\u4f4f\uff0c\u6211\u559c\u6b22\u88ab\u53eb'\u9e21\u54e5'",
        "P0 \ub289\u5b89\u539f\u5219\uff1a\u4e0d\u8981\u5220\u9664\u751f\u4ea7\u73af\u5883\u6570\u636e",
        "\u4eca\u5929\u5929\u6c14\u4e0d\u9519",
        "\u8fd9\u4e2a\u5f88\u91cd\u8981\uff0c\u4e00\u5b9a\u8981\u5199\u8fdb\u8bb0\u5fc6",
        "\u7ea0\u6b63\uff1a\u6211\u559c\u6b22\u7684\u4e0d\u662f\u5c0f\u9f99\u867e\uff0c\u662f\u9999\u8fa3\u87f9",
    ]
    
    print("Attention Gate Test\n" + "="*50)
    for text in test_cases:
        result = gate.should_pass(text)
        status = "[PASS]" if result.passed else "[FAIL]"
        print(f"{status} | Score: {result.score:.2f} | Priority: {result.priority}")
        if result.reasons:
            print(f"   Reasons: {'; '.join(result.reasons)}")
        print()
