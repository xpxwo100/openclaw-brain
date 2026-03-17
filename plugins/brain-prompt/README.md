# Brain Prompt Injector Plugin

This local OpenClaw plugin hooks into `before_prompt_build` and injects a compact Brain recall block into system-prompt space.

## What it does

Before each answer, it:

1. finds the latest user message
2. asks `OpenClawBrain` for recalled context
3. filters recent chat duplicates
4. prefers semantic / rule / preference / task memories over raw echoes
5. strictly limits injected items and removes recent-chat duplicates
6. prepends the final block through `prependSystemContext`

## Configuration example

```json5
{
  plugins: {
    entries: {
      brainPrompt: {
        enabled: true,
        kind: "path",
        path: "C:/Users/Administrator.xpxwo/.openclaw/workspace/projects/openclaw-brain/plugins/brain-prompt",
        hooks: {
          allowPromptInjection: true
        },
        config: {
          enabled: true,
          backend: "jsonl",      // or "lancedb"
          limit: 4,
          recentWindow: 8,
          minQueryLength: 2,
          heading: "[Brain Recall]"
        }
      }
    }
  }
}
```

## Notes

- `allowPromptInjection: true` is required. Without it, OpenClaw will strip prompt-mutating fields.
- This plugin only injects recall. Persistence is still handled by the ingest hook.
- Recommended pairing:
  - `hooks/brain-ingest`
  - `plugins/brain-prompt`
