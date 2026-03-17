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


def test_brain_cli_explain_store_defaults_to_workspace_data_path():
    result = run_cli({"action": "explain-store"})

    assert result["project_root"] == str(PROJECT_ROOT)
    assert result["cli_path"] == str(CLI_PATH)
    assert result["resolved_store_root"] == str(PROJECT_ROOT.parent.parent / "data" / "openclaw-brain")


def test_brain_cli_remember_message_extracts_preference_semantically(tmp_path):
    store_root = tmp_path / "hook-store"
    result = run_cli(
        {
            "action": "remember-message",
            "store_root": str(store_root),
            "attention_threshold": 0.1,
            "working_memory_capacity": 5,
            "message": {
                "content": "记住，用户喜欢被叫鸡哥",
                "author": "tester",
                "channel": "telegram",
                "message_id": "m1",
            },
            "importance": 0.9,
            "mode": "episodic",
            "trigger_consolidation": True,
        }
    )

    assert result["remembered"] is True
    assert "preference" in result["memory_kinds"]
    assert result["resolved_store_root"] == str(store_root)
    assert (store_root / "semantic.jsonl").exists()
    semantic_rows = (store_root / "semantic.jsonl").read_text(encoding="utf-8")
    assert "鸡哥" in semantic_rows
    assert (store_root / "hippocampus.jsonl").exists()


def test_brain_cli_build_context_filters_recent_duplicates(tmp_path):
    store_root = tmp_path / "hook-store"
    run_cli(
        {
            "action": "remember-message",
            "store_root": str(store_root),
            "attention_threshold": 0.1,
            "message": {
                "content": "记住，用户喜欢被叫鸡哥",
                "author": "tester",
                "channel": "telegram",
                "message_id": "m1",
            },
            "importance": 0.95,
            "mode": "episodic",
            "trigger_consolidation": True,
        }
    )
    run_cli(
        {
            "action": "remember-tool",
            "store_root": str(store_root),
            "extract_knowledge": True,
            "tool": {
                "name": "profile_sync",
                "arguments": {},
                "result": {"nickname_preference": "鸡哥"},
                "success": True,
            },
        }
    )

    result = run_cli(
        {
            "action": "build-context",
            "store_root": str(store_root),
            "query": "我喜欢什么称呼",
            "recent_messages": ["记住，用户喜欢被叫鸡哥"],
            "recent_message_ids": ["m1"],
            "limit": 5,
        }
    )

    assert result["count"] >= 1
    assert result["context_text"].startswith("[Brain Recall]")
    assert result["context_text"].count("鸡哥") == 1
    assert "相关历史" not in result["context_text"]


def test_brain_cli_remember_assistant_message_only_keeps_commitment_or_result(tmp_path):
    store_root = tmp_path / "hook-store"
    result = run_cli(
        {
            "action": "remember-message",
            "store_root": str(store_root),
            "message": {
                "content": "我会修复 JSONL 落盘路径，并已更新测试。",
                "author": "assistant",
                "role": "assistant",
                "channel": "telegram",
                "message_id": "a1",
            },
            "importance": 0.8,
        }
    )

    assert result["remembered"] is True
    semantic_rows = (store_root / "semantic.jsonl").read_text(encoding="utf-8")
    assert "jsonl 落盘路径" in semantic_rows.lower()
    assert "我会修复" not in semantic_rows


def test_brain_cli_remember_tool(tmp_path):
    store_root = tmp_path / "hook-store"
    result = run_cli(
        {
            "action": "remember-tool",
            "store_root": str(store_root),
            "extract_knowledge": True,
            "tool": {
                "name": "web_search",
                "arguments": {"query": "OpenClaw"},
                "result": {"title": "OpenClaw Docs", "url": "https://docs.openclaw.ai"},
                "success": True,
            },
        }
    )

    assert result["episodic_recorded"] is True
    assert result["knowledge_count"] >= 1
    assert (store_root / "semantic.jsonl").exists()
    episodic_rows = (store_root / "episodic.jsonl").read_text(encoding="utf-8")
    assert "tool=web_search" in episodic_rows
