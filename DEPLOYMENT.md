# Deployment Guide

[中文版本 / Chinese version](./DEPLOYMENT.zh-CN.md)

## Scope

This guide covers deployment and operation on:

- Windows
- Linux
- macOS

It includes:
- local development setup
- production-ish local deployment for OpenClaw workspaces
- path guidance for hooks and plugins
- storage placement recommendations

---

## 1. Runtime requirements

### Required
- Python 3.9+
- `pip`
- Node.js 18+ (recommended when using OpenClaw plugins)

### Recommended
- virtual environment per machine
- stable workspace path
- OpenClaw already installed if you want hook/plugin integration

---

## 2. Clone and install

### Windows (PowerShell)

```powershell
git clone <your-repo-url>
cd openclaw-brain
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Linux / macOS

```bash
git clone <your-repo-url>
cd openclaw-brain
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Validate the installation

```bash
python -m pytest -q
python verify.py
```

Expected result:
- tests pass
- verify reports structure/import/plugin/test checks as OK

---

## 4. Persistence paths

### Default persistence path
The hook, prompt plugin, and `hooks/brain_cli.py` now resolve to the same default store:

```text
<workspace>/data/openclaw-brain/
```

Example:

- Windows:
  `C:\Users\you\.openclaw\workspace\data\openclaw-brain\`
- Linux/macOS:
  `/home/you/.openclaw/workspace/data/openclaw-brain/`

Resolution order:

1. explicit `store_root`
2. explicit `workspace.dir` / `OPENCLAW_WORKSPACE_DIR`
3. inferred workspace root when project lives under `<workspace>/projects/openclaw-brain`
4. fallback to `<project>/data/openclaw-brain`

This keeps JSONL/LanceDB state stable, visible, and shared across ingest + prompt injection.

---

## 5. OpenClaw hook deployment

### Unified ingest hook
Hook path:

```text
hooks/brain-ingest
```

### Prompt plugin
Plugin path:

```text
plugins/brain-prompt
```

### Example OpenClaw config snippet

> Adjust paths to match your machine.

```json5
{
  hooks: {
    "brain-ingest": {
      enabled: true,
      attention_threshold: 0.7,
      auto_consolidate: true,
      consolidation_interval: 100,
      extract_knowledge: true
    }
  },
  plugins: {
    entries: {
      brainPrompt: {
        enabled: true,
        kind: "path",
        path: "<absolute-path-to>/openclaw-brain/plugins/brain-prompt",
        hooks: {
          allowPromptInjection: true
        },
        config: {
          enabled: true,
          backend: "jsonl",
          limit: 5,
          recentWindow: 8,
          minQueryLength: 2,
          heading: "[Brain Recall]"
        }
      }
    }
  }
}
```

---

## 6. Backend selection

### JSONL backend
Choose JSONL when you want:
- simple local inspection
- manual backups
- less moving pieces
- easier debugging

### LanceDB backend
Choose LanceDB when you want:
- a more scalable data store
- future vector retrieval support
- cleaner migration toward semantic search workflows

---

## 7. OS-specific notes

### Windows
- Prefer PowerShell or a properly configured terminal
- Be careful with backslashes in JSON config paths
- If execution policy blocks venv activation, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

- If `python` maps to the Microsoft Store shim, use `py` or a full Python path

### Linux
- Make sure `python3` and `pip` target the same interpreter
- Good fit for cron-triggered consolidation or maintenance jobs
- Keep file permissions sane if memory files include sensitive data

### macOS
- `python3` is usually safer than `python`
- If using Homebrew Python, confirm the correct interpreter is in `PATH`
- Works well for local desktop-style OpenClaw usage

---

## 8. Upgrade workflow

When upgrading the project:

1. back up the persistence directory
2. pull the new code
3. reinstall dependencies if needed
4. run `python verify.py`
5. only then switch the running OpenClaw integration over

That order saves pain.

---

## 9. Backup and recovery

### Minimum backup set
- persistence directory (`jsonl` files or LanceDB directory)
- custom OpenClaw config entries that reference this project

### Recovery strategy
- restore the persistence directory
- restore the OpenClaw config snippet
- re-run `python verify.py`

---

## 10. Troubleshooting

### Plugin import fails
Check:
- Node.js is installed
- `plugins/brain-prompt/package.json` exists
- the plugin path in OpenClaw config is correct

### Brain CLI fails
Check:
- Python is installed and available in `PATH`
- required Python dependencies are installed
- the project path is valid

### No memory files appear
Check:
- hook/plugin is actually enabled
- `workspace.dir` is available in OpenClaw config/context
- attention threshold is not too strict

### Recall block is empty
Check:
- messages/tools are being ingested first
- recent duplicate suppression is not filtering everything useful
- query length is above `minQueryLength`

---

## 11. Recommended production-ish practices

- keep persistence under a dedicated data directory
- back up memory stores before structural changes
- prefer JSONL first, LanceDB second when debugging weird behavior
- document your actual deployment paths in your repo or ops notes
- test on the target OS before pretending something is cross-platform
