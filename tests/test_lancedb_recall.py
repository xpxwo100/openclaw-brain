from pathlib import Path


def test_lancedb_query_records_prefilters_semantic_hits(tmp_path):
    pytest = __import__("pytest")
    try:
        from storage import LanceMemoryStore
    except ImportError:
        pytest.skip("lancedb not installed")

    from brain import MemoryKind, MemoryRecord

    store = LanceMemoryStore(tmp_path / "lancedb")
    snapshot = {
        "working": [],
        "hippocampus": [],
        "episodic": [
            MemoryRecord(content="today fixed the gateway task runner", kind=MemoryKind.EPISODIC, importance=0.5),
            MemoryRecord(content="weather is nice outside", kind=MemoryKind.EPISODIC, importance=0.3),
        ],
        "semantic": [
            MemoryRecord(content="user prefers being called Chicken Bro", kind=MemoryKind.PREFERENCE, importance=0.95, context={"channel": "telegram"}),
            MemoryRecord(content="backup before changing config", kind=MemoryKind.RULE, importance=0.9, context={"channel": "telegram"}),
        ],
    }
    store.save_snapshot(snapshot)

    results = store.query_records(
        "semantic",
        query="what should I call the user",
        limit=5,
        kinds=["preference", "rule"],
        min_importance=0.4,
        context={"channel": "telegram"},
    )

    assert len(results) >= 1
    assert results[0].kind == MemoryKind.PREFERENCE

