import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "hooks" / "brain_cli.py"


def run_cli(payload):
    result = subprocess.run(
        [sys.executable, str(CLI_PATH)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        cwd=PROJECT_ROOT,
        check=True,
    )
    return json.loads(result.stdout)


def test_brain_cli_build_context_uses_lancedb_prefilter(tmp_path):
    pytest = __import__("pytest")
    try:
        import lancedb  # noqa: F401
    except ImportError:
        pytest.skip("lancedb not installed")

    store_root = tmp_path / "hook-store-lancedb"
    run_cli(
        {
            "action": "remember-message",
            "store_root": str(store_root),
            "backend": "lancedb",
            "attention_threshold": 0.1,
            "message": {
                "content": "remember: user prefers being called Chicken Bro",
                "author": "tester",
                "channel": "telegram",
                "message_id": "m1",
            },
            "importance": 0.95,
            "trigger_consolidation": True,
        }
    )
    run_cli(
        {
            "action": "remember-tool",
            "store_root": str(store_root),
            "backend": "lancedb",
            "extract_knowledge": True,
            "tool": {
                "name": "profile_sync",
                "arguments": {},
                "result": {"nickname_preference": "Chicken Bro"},
                "success": True,
            },
        }
    )

    result = run_cli(
        {
            "action": "build-context",
            "store_root": str(store_root),
            "backend": "lancedb",
            "query": "what should I call the user",
            "recent_messages": [],
            "recent_message_ids": [],
            "limit": 5,
        }
    )

    assert result["recall_mode"] == "store_prefilter"
    assert result["candidate_count"] >= 1
    assert result["context_text"].startswith("[Brain Recall]")


def test_brain_cli_resume_query_filters_out_preference_memories(tmp_path):
    pytest = __import__("pytest")
    try:
        import lancedb  # noqa: F401
    except ImportError:
        pytest.skip("lancedb not installed")

    store_root = tmp_path / "hook-store-resume"

    run_cli(
        {
            "action": "remember-message",
            "store_root": str(store_root),
            "backend": "lancedb",
            "attention_threshold": 0.1,
            "message": {
                "content": "Please call me Chicken Bro",
                "author": "tester",
                "channel": "telegram",
                "message_id": "m1",
            },
            "importance": 0.92,
            "trigger_consolidation": True,
        }
    )

    for message_id in ("m2", "m3"):
        run_cli(
            {
                "action": "remember-message",
                "store_root": str(store_root),
                "backend": "lancedb",
                "attention_threshold": 0.1,
                "message": {
                    "content": "user works on AI agent projects for enterprise automation",
                    "author": "tester",
                    "channel": "telegram",
                    "message_id": message_id,
                },
                "importance": 0.94,
                "trigger_consolidation": True,
            }
        )

    result = run_cli(
        {
            "action": "build-context",
            "store_root": str(store_root),
            "backend": "lancedb",
            "query": "write an ai agent project experience for resume",
            "recent_messages": [],
            "recent_message_ids": [],
            "limit": 4,
        }
    )

    assert result["query_profile"] == "resume"
    assert result["recall_mode"] == "store_prefilter"
    assert "ai agent" in result["context_text"].lower()
    assert "chicken bro" not in result["context_text"].lower()
