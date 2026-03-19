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


def test_preference_promotes_to_semantic_only_after_repeat(tmp_path):
    store_root = tmp_path / "semantic-promotion"
    payload = {
        "action": "remember-message",
        "store_root": str(store_root),
        "attention_threshold": 0.1,
        "message": {
            "content": "remember: user prefers being called Chicken Bro",
            "author": "tester",
            "channel": "telegram",
        },
        "importance": 0.95,
        "trigger_consolidation": True,
    }

    first = run_cli(payload)
    assert first["remembered"] is True
    assert "preference" not in first["memory_kinds"]

    second = run_cli(payload)
    assert second["remembered"] is True
    assert "preference" in second["memory_kinds"]


def test_assistant_result_promotes_to_semantic_only_after_repeat(tmp_path):
    store_root = tmp_path / "assistant-promotion"
    payload = {
        "action": "remember-message",
        "store_root": str(store_root),
        "message": {
            "content": "done updated the gateway config path",
            "author": "assistant",
            "role": "assistant",
            "channel": "telegram",
        },
        "importance": 0.8,
        "trigger_consolidation": True,
    }

    first = run_cli(payload)
    assert "fact" not in first["memory_kinds"]

    second = run_cli(payload)
    assert "fact" in second["memory_kinds"]
