#!/usr/bin/env python3
"""Verification script for the refactored OpenClaw Brain project."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


PROJECT_ROOT = Path(__file__).parent
VERIFY_BASETEMP = PROJECT_ROOT / ".tmp-test" / "verify-pytest"


def verify_structure():
    required_dirs = ["brain", "models", "storage", "hooks", "plugins", "tests", "examples", "docs"]
    required_files = [
        "README.md",
        "README.zh-CN.md",
        "requirements.txt",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "DEPLOYMENT.md",
        "DEPLOYMENT.zh-CN.md",
        "mkdocs.yml",
        "docs/architecture.md",
        "docs/architecture.zh-CN.md",
        "hooks/brain-ingest/handler.js",
        "hooks/brain-ingest/HOOK.md",
        "plugins/brain-prompt/index.js",
        "plugins/brain-prompt/README.md",
        "plugins/brain-prompt/package.json",
    ]
    errors = []

    for name in required_dirs:
        path = PROJECT_ROOT / name
        if not path.exists():
            errors.append(f"missing directory: {name}")
        elif not path.is_dir():
            errors.append(f"not a directory: {name}")

    for name in required_files:
        path = PROJECT_ROOT / name
        if not path.exists():
            errors.append(f"missing file: {name}")

    return errors


def verify_modules():
    errors = []
    required_modules = [
        "brain",
        "brain.base",
        "brain.attention",
        "brain.working_memory",
        "brain.hippocampus",
        "brain.episodic",
        "brain.semantic",
        "brain.retrieval",
        "brain.consolidation",
        "brain.orchestrator",
    ]

    sys.path.insert(0, str(PROJECT_ROOT))
    for module in required_modules:
        try:
            __import__(module)
        except Exception as exc:
            errors.append(f"module import failed: {module} - {exc}")
    return errors


def verify_tests():
    try:
        VERIFY_BASETEMP.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--basetemp", str(VERIFY_BASETEMP)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return ["tests timed out (180s)"]
    except Exception as exc:
        return [f"failed to run tests: {exc}"]

    if result.returncode != 0:
        return [f"tests failed:\n{result.stdout}\n{result.stderr}"]
    return []


def verify_plugin_import():
    try:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                "import(process.env.pluginPath).then((m)=>{ if (!m.default) throw new Error('missing default export'); console.log('ok'); })",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "pluginPath": (PROJECT_ROOT / "plugins" / "brain-prompt" / "index.js").resolve().as_uri()},
        )
    except FileNotFoundError:
        return ["node not found for plugin import check"]
    except subprocess.TimeoutExpired:
        return ["plugin import check timed out (30s)"]
    except Exception as exc:
        return [f"failed to run plugin import check: {exc}"]

    if result.returncode != 0:
        return [f"plugin import failed:\n{result.stdout}\n{result.stderr}"]
    return []


def main() -> int:
    print("=" * 60)
    print("OpenClaw Brain Verification Report")
    print("=" * 60)

    all_errors = []
    for title, fn in [
        ("structure", verify_structure),
        ("imports", verify_modules),
        ("plugin", verify_plugin_import),
        ("tests", verify_tests),
    ]:
        print(f"\n[{title}]")
        errors = fn()
        if errors:
            all_errors.extend(errors)
            for error in errors:
                print(f"  [X] {error}")
        else:
            print("  [OK]")

    print("\n" + "=" * 60)
    if all_errors:
        print(f"Verification FAILED: {len(all_errors)} error(s)")
        return 1
    print("[OK] Verification PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
