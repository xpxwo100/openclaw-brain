---
name: brain-message
description: "Process messages through Brain's attention gate and memory system"
metadata:
  {
    "openclaw":
      {
        "emoji": "🧠",
        "events": ["message"],
        "requires": { "config": ["workspace.dir"] },
        "install": [{ "id": "local", "kind": "path", "label": "Local Workspace Hook" }],
      },
  }
---

# Brain Message Hook

Processes incoming messages through the Brain's attention gate mechanism to determine if the message should be remembered.

## Features

- **Attention Gate**: Scores message importance based on keywords, length, and patterns
- **Working Memory**: Stores important messages temporarily
- **Auto-consolidation**: Automatically consolidates working memory to long-term storage

## Configuration

```yaml
hooks:
  brain-message:
    enabled: true
    attention_threshold: 0.7      # Minimum importance score to remember (0-1)
    working_memory_limit: 10    # Maximum messages in working memory
    auto_consolidate: true       # Enable auto-consolidation
    consolidation_interval: 100  # Messages before consolidation
```

## Events

- `message` - Processes each incoming message
