# Contributing

Thanks for contributing to OpenClaw Brain.

This project is still evolving, so clean changes and clear docs matter more than flashy churn.

## Ground rules

- keep the public API stable when practical
- if behavior changes, update docs in the same PR
- if architecture changes, update `docs/architecture.md`
- if deployment behavior changes, update `DEPLOYMENT.md`
- do not sneak in unrelated refactors

## Development setup

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Before you open a PR

Run:

```bash
python -m pytest -q
python verify.py
```

If you touched docs-heavy areas, also review:
- `README.md`
- `README.zh-CN.md`
- `docs/architecture.md`
- `docs/architecture.zh-CN.md`
- `DEPLOYMENT.md`
- `DEPLOYMENT.zh-CN.md`

## Coding style

- prefer explicit, boring code over clever code
- preserve cross-platform path handling
- avoid hardcoding environment-specific assumptions
- keep module ownership clear
- write tests when changing behavior

## Documentation policy

This repository supports both English and Simplified Chinese readers.

When updating core user-facing docs, keep both language versions aligned where practical.

## Good PR examples

- fix retrieval scoring and update tests
- add a backend feature and document deployment implications
- improve prompt injection behavior and update hook/plugin docs

## Bad PR examples

- drive-by renames with no architectural value
- refactors that break imports without migration notes
- adding platform-specific hacks with no fallback

## Issues

When filing an issue, include:
- OS and version
- Python version
- whether you are using JSONL or LanceDB
- whether you are running standalone or inside OpenClaw
- reproduction steps
