# OpenClaw Brain

> A multi-layer memory system for OpenClaw, rebuilt as an actual engineering project instead of a pile of neuroscience metaphors.

[简体中文文档 / Chinese docs](./README.zh-CN.md)

## Overview

OpenClaw Brain provides a structured memory pipeline for OpenClaw agents:

- **Attention gating** decides what is worth remembering
- **Working memory** keeps short-lived task state
- **Hippocampus** encodes recent candidate memories
- **Episodic memory** stores events and experiences
- **Semantic memory** stores facts, rules, and preferences
- **Retrieval + context building** turns memory into prompt-ready recall blocks
- **Persistence backends** support JSONL and LanceDB
- **OpenClaw hooks/plugins** wire the Brain into real message and tool flows

This project is designed to run on **Windows, Linux, and macOS**.

---

## Table of Contents

- [Why this project exists](#why-this-project-exists)
- [Features](#features)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [OpenClaw integration](#openclaw-integration)
- [Storage backends](#storage-backends)
- [Cross-platform deployment](#cross-platform-deployment)
- [Documentation](#documentation)
- [Development](#development)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Why this project exists

The earlier version had the right idea but weak execution:

- concepts were richer than boundaries
- memory objects were inconsistent across modules
- no single orchestration entry point existed
- retrieval and consolidation were not wired into a coherent pipeline

This refactor fixes that by introducing:

- a **canonical memory model**: `MemoryRecord`
- a **single orchestration entry point**: `OpenClawBrain`
- a **prompt-oriented context builder**
- **persistent backends** for real deployments
- **OpenClaw hooks/plugins** for production-style usage

---

## Features

### Core memory system
- Unified memory schema with `MemoryRecord`
- Attention-based ingestion
- Working memory with TTL and capacity control
- Hippocampus-style fast encoding buffer
- Episodic and semantic stores
- Consolidation and memory promotion
- Multi-factor retrieval and reranking
- Prompt-ready context building with duplicate suppression

### Persistence
- `jsonl` backend for transparency and debugging
- `lancedb` backend for scalable retrieval workflows
- Save/load support through `OpenClawBrain.save()` and `OpenClawBrain.load()`

### OpenClaw integration
- `hooks/brain-ingest` for unified message + tool ingestion
- `plugins/brain-prompt` for `before_prompt_build` prompt injection

### Cross-platform support
- PowerShell-friendly instructions for Windows
- POSIX shell instructions for Linux/macOS
- Path guidance for both local development and OpenClaw workspace deployment

---

## Project structure

```text
openclaw-brain/
├─ brain/                     # Core memory pipeline
│  ├─ base.py                 # Canonical memory model
│  ├─ attention.py            # Attention gate
│  ├─ working_memory.py       # Short-term memory
│  ├─ hippocampus.py          # Fast encoding buffer
│  ├─ episodic.py             # Episodic store
│  ├─ semantic.py             # Semantic store
│  ├─ retrieval.py            # Recall and reranking
│  ├─ consolidation.py        # Promotion / forgetting primitives
│  ├─ context.py              # Prompt-oriented recall builder
│  └─ orchestrator.py         # OpenClawBrain entry point
├─ storage/                   # Persistence backends
├─ hooks/                     # OpenClaw hooks + Python bridge
├─ plugins/brain-prompt/      # OpenClaw prompt-injection plugin
├─ docs/                      # Architecture and deployment docs
├─ examples/                  # Usage examples
├─ tests/                     # Test suite
└─ verify.py                  # Structure/import/test verification
```

---

## Quick start

### Requirements

- Python **3.9+**
- Node.js **18+** recommended for OpenClaw plugin workflows
- OpenClaw runtime is **optional** and only needed for hook/plugin integration

### Install (development)

#### Windows PowerShell

```powershell
cd C:\path\to\openclaw-brain
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Linux / macOS

```bash
cd /path/to/openclaw-brain
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Basic usage

```python
from brain import OpenClawBrain

brain = OpenClawBrain(attention_threshold=0.4)

brain.remember(
    "Remember that the user prefers being called Chicken Bro",
    context={"kind": "preference", "source": "profile"},
    importance=0.9,
)

results = brain.recall("preferred nickname", limit=5)
for item in results:
    print(item.memory.content)

context_block = brain.build_context(
    query="How should I address the user?",
    recent_messages=["Remember that the user prefers being called Chicken Bro"],
    recent_message_ids=["m1"],
    limit=3,
)

print(context_block["context_text"])
```

---

## OpenClaw integration

This project includes two integration surfaces:

### 1. Unified ingest hook
Persists important inbound messages, turns user messages into compact preference/rule/fact/task memories, extracts assistant execution memory (commitments, results, decisions, current state), records tool usage as compact episodic memory, and extracts semantic knowledge from tool results.

Important runtime note: `hippocampus` is a staging buffer, not a forever-growing event log. After consolidation, durable history lives primarily in `episodic` and `semantic`.

- Path: `hooks/brain-ingest`
- Doc: [`hooks/brain-ingest/HOOK.md`](./hooks/brain-ingest/HOOK.md)

### 2. Prompt injection plugin
Injects compact memory recall into system-prompt space during `before_prompt_build`.

- Path: `plugins/brain-prompt`
- Doc: [`plugins/brain-prompt/README.md`](./plugins/brain-prompt/README.md)

### Intended runtime flow

```text
message/tool events
  -> OpenClawBrain persisted store
  -> build_context(query, recent_messages, ...)
  -> prependSystemContext
  -> model answer
```

---

## Storage backends

### JSONL
Use JSONL when you want:

- easy inspection
- easy backup
- zero-database local development
- deterministic debug workflows

### LanceDB
Use LanceDB when you want:

- larger persistent stores
- future vector retrieval workflows
- cleaner evolution toward semantic search

### Example

```python
from brain import OpenClawBrain

brain = OpenClawBrain(attention_threshold=0.1)
brain.remember("The user likes concise answers", context={"kind": "preference"}, importance=0.9)

brain.save("./data/brain-jsonl", backend="jsonl")
brain.save("./data/brain-lancedb", backend="lancedb")
```

---

## Cross-platform deployment

Detailed guide: [`DEPLOYMENT.md`](./DEPLOYMENT.md)

Supported targets:

- **Windows**: PowerShell, local OpenClaw workspace deployment
- **Linux**: local/server deployment, cron-friendly workflows
- **macOS**: local development and OpenClaw desktop-style deployments

Key portability rules:

- avoid hardcoding path separators in your own config
- keep Python and Node available in `PATH`
- prefer virtual environments per machine
- keep persistent stores outside ephemeral temp directories

---

## Documentation

### English
- [Architecture](./docs/architecture.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Contributing](./CONTRIBUTING.md)
- [Security](./SECURITY.md)

### 中文
- [中文 README](./README.zh-CN.md)
- [架构说明](./docs/architecture.zh-CN.md)
- [部署指南](./DEPLOYMENT.zh-CN.md)

---

## Development

### Run tests

```bash
python -m pytest -q
```

### Verify structure, imports, plugin load, and tests

```bash
python verify.py
```

### Package install (editable)

```bash
pip install -e .
```

---

## Roadmap

Near-term priorities:

- deeper LanceDB/vector retrieval integration
- stronger semantic extraction pipelines
- more production-grade repository abstractions
- richer OpenClaw configuration examples
- CI workflows for Windows/Linux/macOS validation

---

## Contributing

Pull requests are welcome.

Before opening one, please:

1. run tests
2. run `python verify.py`
3. keep docs updated when behavior changes
4. avoid breaking the public API without documenting it clearly

See [`CONTRIBUTING.md`](./CONTRIBUTING.md).

---

## License

MIT. See [`LICENSE`](./LICENSE).
