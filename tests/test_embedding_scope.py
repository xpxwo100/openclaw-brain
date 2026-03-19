def test_lancedb_only_embeds_semantic_and_episodic_buckets(tmp_path):
    pytest = __import__("pytest")
    try:
        from storage import LanceMemoryStore
    except ImportError:
        pytest.skip("lancedb not installed")

    from brain import MemoryKind, MemoryRecord

    store = LanceMemoryStore(tmp_path / "lancedb")
    snapshot = {
        "working": [MemoryRecord(content="temporary task note", kind=MemoryKind.WORKING, importance=0.8)],
        "hippocampus": [MemoryRecord(content="fresh event buffer item", kind=MemoryKind.EPISODIC, importance=0.7)],
        "episodic": [MemoryRecord(content="completed migration to lancedb backend", kind=MemoryKind.EPISODIC, importance=0.9)],
        "semantic": [MemoryRecord(content="user prefers being called Chicken Bro", kind=MemoryKind.PREFERENCE, importance=0.95)],
    }
    store.save_snapshot(snapshot)

    working_rows = store.db.open_table("working_records").to_arrow().to_pylist()
    hippocampus_rows = store.db.open_table("hippocampus_records").to_arrow().to_pylist()
    episodic_rows = store.db.open_table("episodic_records").to_arrow().to_pylist()
    semantic_rows = store.db.open_table("semantic_records").to_arrow().to_pylist()

    assert working_rows[0].get("embedding_dim", 0) == 0
    assert hippocampus_rows[0].get("embedding_dim", 0) == 0
    assert episodic_rows[0].get("embedding_dim", 0) > 0
    assert semantic_rows[0].get("embedding_dim", 0) > 0
