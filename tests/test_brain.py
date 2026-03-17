"""Test suite for OpenClaw Brain."""

from brain import (
    AttentionGate,
    WorkingMemory,
    Hippocampus,
    EpisodicStore,
    SemanticStore,
    SleepConsolidation,
    MemoryRetriever,
)


class TestAttentionGate:
    def test_should_pass_with_priority_keyword(self):
        gate = AttentionGate(
            priority_keywords=["记住", "重要", "P0"],
            emotional_triggers=["纠正", "否定"],
        )

        result = gate.should_pass(
            text="记住，我叫鸡哥",
            context={"user": "test"},
        )

        assert result.passed is True

    def test_should_pass_with_emotional_trigger(self):
        gate = AttentionGate(
            priority_keywords=["记住"],
            emotional_triggers=["纠正", "否定", "不对"],
        )

        result = gate.should_pass(
            text="不对，我叫小帅",
            context={"user": "test"},
        )

        assert result.passed is True

    def test_should_not_pass_without_triggers(self):
        gate = AttentionGate(
            priority_keywords=["记住"],
            emotional_triggers=["纠正"],
        )

        result = gate.should_pass(
            text="今天天气不错",
            context={"user": "test"},
        )

        assert result.passed is False


class TestWorkingMemory:
    def test_add_and_get(self):
        wm = WorkingMemory(capacity=5)
        wm.add("test_key", "test_value")
        assert wm.get("test_key") == "test_value"

    def test_capacity_limit(self):
        wm = WorkingMemory(capacity=3)
        wm.add("key1", "value1", importance=0.9)
        wm.add("key2", "value2", importance=0.8)
        wm.add("key3", "value3", importance=0.7)
        wm.add("key4", "value4", importance=0.1)
        assert len(wm.get_all()) <= 3

    def test_get_all(self):
        wm = WorkingMemory(capacity=10)
        wm.add("a", 1)
        wm.add("b", 2)
        wm.add("c", 3)
        assert len(wm.get_all()) == 3

    def test_rehearse_moves_important_item_out(self):
        transferred = []
        wm = WorkingMemory(capacity=5)
        wm.add("rule", "always backup config", importance=0.9)

        ok = wm.rehearse(
            "rule",
            target="semantic",
            callback=lambda key, value, target: transferred.append((key, value, target)),
        )

        assert ok is True
        assert transferred == [("rule", "always backup config", "semantic")]
        assert wm.get("rule") is None


class TestHippocampus:
    def test_encode_memory(self):
        hippocampus = Hippocampus(capacity=100)
        memory = hippocampus.encode(
            content="用户喜欢编程",
            context={"source": "conversation"},
            importance=0.8,
        )

        assert memory.content == "用户喜欢编程"
        assert memory.importance == 0.8

    def test_get_recent_memories(self):
        hippocampus = Hippocampus(capacity=100)
        hippocampus.encode("memory1", importance=0.5)
        hippocampus.encode("memory2", importance=0.7)
        assert len(hippocampus.get_recent_memories(limit=10)) == 2

    def test_consolidate(self):
        hippocampus = Hippocampus(capacity=100)
        hippocampus.encode("test memory")
        assert hippocampus.consolidate() >= 1


class TestEpisodicStore:
    def test_add_memory(self):
        store = EpisodicStore(max_size=100)
        memory = store.add(
            content="今天学习了Python",
            context={"topic": "programming"},
            emotion="happy",
        )

        assert memory.content == "今天学习了Python"
        assert memory.emotion == "happy"

    def test_get_recent(self):
        store = EpisodicStore(max_size=100)
        store.add("memory 1")
        store.add("memory 2")
        assert len(store.get_recent(hours=24)) == 2

    def test_search(self):
        store = EpisodicStore(max_size=100)
        store.add("Python is great")
        store.add("JavaScript is fast")
        results = store.search("Python")
        assert len(results) == 1
        assert "Python" in results[0].content


class TestSemanticStore:
    def test_add_concept(self):
        store = SemanticStore()
        concept = store.add_concept(
            name="Python",
            definition="一种编程语言",
            category="programming",
        )

        assert concept.name == "Python"
        assert concept.category == "programming"

    def test_search_concepts(self):
        store = SemanticStore()
        store.add_concept("Python", "一种编程语言")
        store.add_concept("JavaScript", "另一种编程语言")
        assert len(store.search("Python")) == 1

    def test_get_by_category(self):
        store = SemanticStore()
        store.add_concept("Python", "编程语言", "language")
        store.add_concept("JavaScript", "编程语言", "language")
        store.add_concept("Cat", "动物", "animal")
        assert len(store.get_by_category("language")) >= 2


class TestSleepConsolidation:
    def test_ebbinghaus_curve(self):
        from brain.consolidation import EbbinghausCurve

        curve = EbbinghausCurve(halflife_hours=24)
        assert curve.retention(0) == 1.0

    def test_consolidation_strengthens_memory(self):
        from brain.consolidation import MemoryStrength

        consolidation = SleepConsolidation()
        memory = MemoryStrength(initial_strength=0.5)
        consolidation.consolidate([memory])
        assert memory.strength > 0.5

    def test_should_consolidate(self):
        consolidation = SleepConsolidation()
        assert isinstance(consolidation.should_consolidate(interval_hours=4), bool)


class TestMemoryRetriever:
    def test_retrieve_with_relevance(self):
        from brain.hippocampus import MemoryItem

        retriever = MemoryRetriever()
        memories = [
            MemoryItem(content="Python is great", importance=0.8),
            MemoryItem(content="JavaScript is fast", importance=0.6),
            MemoryItem(content="Weather is nice", importance=0.5),
        ]

        results = retriever.retrieve("Python", memories)
        assert len(results) >= 1
        assert "Python" in results[0].memory.content

    def test_retrieve_with_limit(self):
        from brain.hippocampus import MemoryItem

        retriever = MemoryRetriever(default_limit=2)
        memories = [MemoryItem(content=f"memory {i}", importance=0.5) for i in range(10)]
        results = retriever.retrieve("memory", memories)
        assert len(results) <= 2


class TestOpenClawBrain:
    def test_remember_and_recall(self):
        from brain import OpenClawBrain

        brain = OpenClawBrain(attention_threshold=0.4)
        brain.remember("记住，用户喜欢被叫鸡哥", context={"kind": "preference", "source": "profile"})

        results = brain.recall("鸡哥", limit=5)
        assert len(results) >= 1
        assert any("鸡哥" in item.memory.content for item in results)

    def test_consolidate_promotes_semantic_memory(self):
        from brain import OpenClawBrain

        brain = OpenClawBrain(attention_threshold=0.1)
        brain.remember(
            "改配置前先备份",
            context={"kind": "rule", "definition": "任何配置改动前必须先备份", "source": "ops"},
            importance=0.9,
        )

        report = brain.consolidate()
        assert report["promoted_episodic"] >= 1
        assert report["promoted_semantic"] >= 1

    def test_snapshot_round_trip(self, tmp_path):
        from brain import OpenClawBrain

        root = tmp_path / "brain-store"
        brain = OpenClawBrain(attention_threshold=0.1)
        brain.remember("记住，用户喜欢被叫鸡哥", context={"kind": "preference", "definition": "用户喜欢昵称鸡哥"}, importance=0.9)
        brain.remember("今天修好了持久化", context={"source": "devlog"}, importance=0.8)
        brain.remember("临时任务", mode="working", importance=0.95)
        brain.consolidate()
        brain.save(root)

        restored = OpenClawBrain.load(root, attention_threshold=0.1)

        recall = restored.recall("鸡哥", limit=5)
        assert len(recall) >= 1
        assert any("鸡哥" in item.memory.content for item in recall)
        assert len(restored.working.get_all()) >= 1
        assert len(restored.episodic.memories) >= 1


class TestBrainContext:
    def test_build_context_prefers_semantic_and_filters_recent_chat(self):
        from brain import OpenClawBrain

        brain = OpenClawBrain(attention_threshold=0.1)
        brain.remember(
            "记住，用户喜欢被叫鸡哥",
            context={"kind": "preference", "definition": "用户喜欢被叫鸡哥", "source": "profile"},
            importance=0.95,
        )
        brain.remember(
            "记住，用户喜欢被叫鸡哥",
            context={"source": "message", "message_id": "m-recent"},
            importance=0.9,
            mode="episodic",
        )
        brain.consolidate()

        result = brain.build_context(
            query="我喜欢什么称呼",
            recent_messages=["记住，用户喜欢被叫鸡哥"],
            recent_message_ids=["m-recent"],
            limit=5,
        )

        assert result["count"] >= 1
        assert any(item["kind"] == "preference" for item in result["items"])
        assert result["context_text"].count("鸡哥") == 1
        assert "用户偏好" in result["context_text"]

    def test_recall_dedup_prefers_semantic_over_episodic(self):
        from brain import OpenClawBrain

        brain = OpenClawBrain(attention_threshold=0.1)
        brain.remember(
            "改配置前先备份",
            context={"source": "message", "message_id": "m1"},
            importance=0.8,
            mode="episodic",
        )
        brain.remember(
            "改配置前先备份",
            context={"kind": "rule", "definition": "任何配置改动前必须先备份", "source": "ops"},
            importance=0.95,
            mode="semantic",
        )

        results = brain.recall("备份", limit=5)
        assert len(results) >= 1
        assert results[0].memory.kind.value == "rule"


class TestJsonlMemoryStore:
    def test_append_and_load_records(self, tmp_path):
        from brain import MemoryKind, MemoryRecord
        from storage import JsonlMemoryStore

        store = JsonlMemoryStore(tmp_path)
        records = [
            MemoryRecord(content="a", kind=MemoryKind.FACT, importance=0.8),
            MemoryRecord(content="b", kind=MemoryKind.EPISODIC, importance=0.6),
        ]
        store.append_records("episodic", records)
        loaded = store.load_records("episodic")

        assert [item.content for item in loaded] == ["a", "b"]
        assert loaded[0].kind == MemoryKind.FACT


class TestLanceMemoryStore:
    def test_save_and_load_snapshot(self, tmp_path):
        pytest = __import__("pytest")
        try:
            from storage import LanceMemoryStore
        except ImportError:
            pytest.skip("lancedb not installed")

        from brain import MemoryKind, MemoryRecord

        store = LanceMemoryStore(tmp_path / "lancedb")
        snapshot = {
            "working": [MemoryRecord(content="task", kind=MemoryKind.WORKING, importance=0.9)],
            "hippocampus": [MemoryRecord(content="event", kind=MemoryKind.EPISODIC, importance=0.8)],
            "episodic": [MemoryRecord(content="episode", kind=MemoryKind.EPISODIC, importance=0.7)],
            "semantic": [MemoryRecord(content="rule", kind=MemoryKind.RULE, importance=0.95)],
        }

        store.save_snapshot(snapshot)
        restored = store.load_snapshot()

        assert restored["working"][0].content == "task"
        assert restored["semantic"][0].kind == MemoryKind.RULE

    def test_brain_round_trip_with_lancedb(self, tmp_path):
        pytest = __import__("pytest")
        try:
            import lancedb  # noqa: F401
        except ImportError:
            pytest.skip("lancedb not installed")

        from brain import OpenClawBrain

        root = tmp_path / "brain-lancedb"
        brain = OpenClawBrain(attention_threshold=0.1)
        brain.remember("记住，用户喜欢被叫鸡哥", context={"kind": "preference", "definition": "用户喜欢昵称鸡哥"}, importance=0.9)
        brain.consolidate()
        brain.save(root, backend="lancedb")

        restored = OpenClawBrain.load(root, backend="lancedb", attention_threshold=0.1)
        recall = restored.recall("鸡哥", limit=5)
        assert len(recall) >= 1
