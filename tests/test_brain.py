"""
测试套件 - OpenClaw Brain
"""

import pytest
from brain import (
    AttentionGate,
    WorkingMemory,
    Hippocampus,
    EpisodicStore,
    SemanticStore,
    SleepConsolidation,
    MemoryRetriever
)


class TestAttentionGate:
    """测试注意力门�?""
    
    def test_should_pass_with_priority_keyword(self):
        """测试包含优先级关键词时应通过"""
        gate = AttentionGate(
            priority_keywords=["记住", "重要", "P0"],
            emotional_triggers=["纠正", "否定"]
        )
        
        result = gate.should_pass(
            text="记住，我叫鸡�?,
            context={"user": "test"}
        )
        
        assert result.passed is True
    
    def test_should_pass_with_emotional_trigger(self):
        """测试情绪触发时应通过"""
        gate = AttentionGate(
            priority_keywords=["记住"],
            emotional_triggers=["纠正", "否定", "不对"]
        )
        
        result = gate.should_pass(
            text="不对，我叫小�?,
            context={"user": "test"}
        )
        
        assert result.passed is True
    
    def test_should_not_pass_without_triggers(self):
        """测试无触发条件时不通过"""
        gate = AttentionGate(
            priority_keywords=["记住"],
            emotional_triggers=["纠正"]
        )
        
        result = gate.should_pass(
            text="今天天气不错",
            context={"user": "test"}
        )
        
        assert result.passed is False


class TestWorkingMemory:
    """测试工作记忆"""
    
    def test_add_and_get(self):
        """测试添加和获�?""
        wm = WorkingMemory(capacity=5)
        
        wm.add("test_key", "test_value")
        
        result = wm.get("test_key")
        
        assert result == "test_value"
    
    def test_capacity_limit(self):
        """测试容量限制"""
        wm = WorkingMemory(capacity=3)
        
        wm.add("key1", "value1")
        wm.add("key2", "value2")
        wm.add("key3", "value3")
        wm.add("key4", "value4")  # 应该触发修剪
        
        items = wm.get_all()
        
        assert len(items) <= 3
    
    def test_get_all(self):
        """测试获取所有项"""
        wm = WorkingMemory(capacity=10)
        
        wm.add("a", 1)
        wm.add("b", 2)
        wm.add("c", 3)
        
        items = wm.get_all()
        
        assert len(items) == 3


class TestHippocampus:
    """测试海马�?""
    
    def test_encode_memory(self):
        """测试记忆编码"""
        hippocampus = Hippocampus(capacity=100)
        
        memory = hippocampus.encode(
            content="用户喜欢编程",
            context={"source": "conversation"},
            importance=0.8
        )
        
        assert memory.content == "用户喜欢编程"
        assert memory.importance == 0.8
    
    def test_get_recent_memories(self):
        """测试获取最近记�?""
        hippocampus = Hippocampus(capacity=100)
        
        hippocampus.encode("memory1", importance=0.5)
        hippocampus.encode("memory2", importance=0.7)
        
        recent = hippocampus.get_recent_memories(limit=10)
        
        assert len(recent) == 2
    
    def test_consolidate(self):
        """测试记忆巩固"""
        hippocampus = Hippocampus(capacity=100)
        
        hippocampus.encode("test memory")
        
        count = hippocampus.consolidate()
        
        assert count >= 1


class TestEpisodicStore:
    """测试情景记忆"""
    
    def test_add_memory(self):
        """测试添加情景记忆"""
        store = EpisodicStore(max_size=100)
        
        memory = store.add(
            content="今天学习了Python",
            context={"topic": "programming"},
            emotion="happy"
        )
        
        assert memory.content == "今天学习了Python"
        assert memory.emotion == "happy"
    
    def test_get_recent(self):
        """测试获取最近记�?""
        store = EpisodicStore(max_size=100)
        
        store.add("memory 1")
        store.add("memory 2")
        
        recent = store.get_recent(hours=24)
        
        assert len(recent) == 2
    
    def test_search(self):
        """测试搜索"""
        store = EpisodicStore(max_size=100)
        
        store.add("Python is great")
        store.add("JavaScript is fast")
        
        results = store.search("Python")
        
        assert len(results) == 1
        assert "Python" in results[0].content


class TestSemanticStore:
    """测试语义记忆"""
    
    def test_add_concept(self):
        """测试添加概念"""
        store = SemanticStore()
        
        concept = store.add_concept(
            name="Python",
            definition="一种编程语言",
            category="programming"
        )
        
        assert concept.name == "Python"
        assert concept.category == "programming"
    
    def test_search_concepts(self):
        """测试搜索概念"""
        store = SemanticStore()
        
        store.add_concept("Python", "一种编程语言")
        store.add_concept("JavaScript", "另一种编程语言")
        
        results = store.search("Python")
        
        assert len(results) == 1
    
    def test_get_by_category(self):
        """测试按类别获�?""
        store = SemanticStore()
        
        store.add_concept("Python", "编程语言", "language")
        store.add_concept("JavaScript", "编程语言", "language")
        store.add_concept("Cat", "动物", "animal")
        
        languages = store.get_by_category("language")
        
        # 至少应该�?Python �?JavaScript
        assert len(languages) >= 2


class TestSleepConsolidation:
    """测试记忆巩固"""
    
    def test_ebbinghaus_curve(self):
        """测试艾宾浩斯曲线"""
        from brain.consolidation import EbbinghausCurve
        
        curve = EbbinghausCurve(halflife_hours=24)
        
        # 0小时保留率应�?.0
        retention = curve.retention(0)
        assert retention == 1.0
    
    def test_consolidation_strengthens_memory(self):
        """测试巩固强化记忆"""
        from brain.consolidation import SleepConsolidation, MemoryStrength
        
        consolidation = SleepConsolidation()
        memory = MemoryStrength(initial_strength=0.5)
        
        consolidation.consolidate([memory])
        
        assert memory.strength > 0.5
    
    def test_should_consolidate(self):
        """测试是否应该执行巩固"""
        consolidation = SleepConsolidation()
        
        # 新创建时不需要立即巩�?        result = consolidation.should_consolidate(interval_hours=4)
        
        assert isinstance(result, bool)


class TestMemoryRetriever:
    """测试记忆检�?""
    
    def test_retrieve_with_relevance(self):
        """测试相关性检�?""
        from brain.hippocampus import MemoryItem
        
        retriever = MemoryRetriever()
        
        memories = [
            MemoryItem(content="Python is great", importance=0.8),
            MemoryItem(content="JavaScript is fast", importance=0.6),
            MemoryItem(content="Weather is nice", importance=0.5)
        ]
        
        results = retriever.retrieve("Python", memories)
        
        assert len(results) >= 1
        assert "Python" in results[0].memory.content
    
    def test_retrieve_with_limit(self):
        """测试结果限制"""
        from brain.hippocampus import MemoryItem
        
        retriever = MemoryRetriever(default_limit=2)
        
        memories = [
            MemoryItem(content=f"memory {i}", importance=0.5)
            for i in range(10)
        ]
        
        results = retriever.retrieve("memory", memories)
        
        assert len(results) <= 2
