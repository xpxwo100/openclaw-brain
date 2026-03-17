"""Basic integration smoke test for memory retrieval wiring."""

from brain import AttentionGate, Hippocampus, MemoryRetriever


def test_injection():
    """Ensure the basic components can be wired together sanely."""
    gate = AttentionGate()
    hippocampus = Hippocampus()
    retriever = MemoryRetriever()

    gate_result = gate.should_pass("记住，这是重要信息")
    assert gate_result.passed is True

    hippocampus.encode("用户叫小帅", context={"source": "conversation"}, importance=0.9)
    memories = retriever.retrieve("小帅", hippocampus.get_recent_memories(limit=10), limit=3)

    assert len(memories) >= 1
    assert "小帅" in memories[0].memory.content


if __name__ == "__main__":
    test_injection()
    print("✅ smoke test passed")
