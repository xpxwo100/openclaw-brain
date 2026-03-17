---
name: brain-ingest
description: "Unified OpenClaw Brain ingress hook for messages and tool activity"
metadata:
  {
    "openclaw":
      {
        "emoji": "🧠",
        "events": ["message", "message:received", "before_tool_call", "tool_result_persist"],
        "requires": { "config": ["workspace.dir"] },
        "install": [{ "id": "local", "kind": "path", "label": "Local Workspace Hook" }],
      },
  }
---

# Brain Ingest Hook

Unified ingress hook for OpenClaw Brain.

It handles both:
- incoming messages
- tool calls / tool results

So you get one config surface, one persistence path, and one memory pipeline.

## Features

- attention-based message scoring
- persistent memory across gateway restarts
- episodic recording of tool activity
- semantic extraction from tool results
- optional auto-consolidation
- shared store with `plugins/brain-prompt`
- backward-compatible config fallback for legacy `brain-message` / `brain-tool-call` keys

## Configuration

```yaml
hooks:
  brain-ingest:
    enabled: true
    attention_threshold: 0.7      # minimum importance score to remember message input (0-1)
    working_memory_limit: 10      # short-term memory capacity passed to Python brain
    auto_consolidate: true        # whether to periodically consolidate memory
    consolidation_interval: 100   # consolidate every N remembered messages
    extract_knowledge: true       # try to extract structured semantic knowledge from tool results
    max_history: 100              # used to derive periodic consolidation for tool events
    knowledge_threshold: 0.5      # reserved compatibility field for future extraction filtering
    persist_all_messages: true    # always persist inbound chat as episodic memory, even if semantic extraction is weak
```

## Event support

- `message`
- `message:received`
- `before_tool_call`
- `tool_result_persist`

## Runtime semantics

### Message ingestion
- inbound user chat is persisted when `persist_all_messages: true`, even if semantic extraction is weak
- assistant replies are not treated as generic chat spam: commitment / result / decision / state language is force-persisted into execution memory
- duplicate inbound message ids are ignored inside a short in-process dedupe window

### Layer behavior
- `working.jsonl`: short-lived active task state
- `hippocampus.jsonl`: staging buffer, **not** an append-only audit log
- `episodic.jsonl`: durable event history after consolidation
- `semantic.jsonl`: extracted facts, rules, preferences, decisions, and state summaries

### Auto-consolidation
`hippocampus` is expected to churn. New records may be promoted and pruned, so `hippocampus.jsonl` may stop growing even while memory is healthy. If you want durable history, inspect `episodic.jsonl` instead of treating `hippocampus.jsonl` as the source of truth.

## Migration

Old configs can be merged into the new unified hook:

```yaml
# old
hooks:
  brain-message:
    attention_threshold: 0.7
  brain-tool-call:
    extract_knowledge: true

# new
hooks:
  brain-ingest:
    attention_threshold: 0.7
    extract_knowledge: true
```

The handler still reads legacy config keys as a fallback, but new installs should use only `brain-ingest`.

## Notes

- Default shared persistence path: `<workspace>/data/openclaw-brain/`.
- You can still override it with explicit `store_root` in the Python bridge payload if needed.
- Recommended pairing:
  - `plugins/brain-prompt`
