---
name: brain-tool-call
description: "Record tool calls to episodic memory and extract semantic knowledge"
metadata:
  {
    "openclaw":
      {
        "emoji": "🔧",
        "events": ["tool_call", "tool_result"],
        "requires": { "config": ["workspace.dir"] },
        "install": [{ "id": "local", "kind": "path", "label": "Local Workspace Hook" }],
      },
  }
---

# Brain Tool Call Hook

Records tool调用历史到情景记忆，并从工具结果中提取语义知识。

## Features

- **Episodic Memory**: Records tool call history with arguments and results
- **Knowledge Extraction**: Extracts structured knowledge from tool results
- **Pattern Recognition**: Identifies reusable tool usage patterns

## Configuration

```yaml
hooks:
  brain-tool-call:
    enabled: true
    extract_knowledge: true       # Enable knowledge extraction
    max_history: 100               # Maximum episodic memory entries
    knowledge_threshold: 0.5       # Minimum importance for knowledge
```

## Events

- `tool_call` - Records when a tool is invoked
- `tool_result` - Records tool execution results and extracts knowledge
