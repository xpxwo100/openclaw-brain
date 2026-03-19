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
7. logs candidate count, selected items, character count, and estimated token usage

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
          backend: "lancedb",    // or "jsonl"
          limit: 4,
          recentWindow: 8,
          minQueryLength: 2,
          maxChars: 900,
          maxEstimatedTokens: 240,
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
- `maxChars` and `maxEstimatedTokens` are hard budgets, not just display hints.
- When loaded inside an OpenClaw workspace, the plugin can fall back to reading `openclaw.json` from disk if runtime config propagation is incomplete.
- A missing `working_records.lance` table is normal when working memory has expired or is empty.
- Recommended pairing:
  - `hooks/brain-ingest`
  - `plugins/brain-prompt`
