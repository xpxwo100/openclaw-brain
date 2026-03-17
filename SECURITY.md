# Security Policy

## Scope

OpenClaw Brain may store user preferences, rules, tool outputs, and other sensitive memory material.

Treat persisted memory as potentially sensitive data.

## Recommendations

- store persistence files in a protected directory
- avoid committing real memory data to Git
- back up stores securely
- restrict file permissions where possible
- review extracted semantic knowledge before using it in high-trust workflows

## OpenClaw integration notes

If you inject recalled context into prompts, remember:
- bad memory can become bad answers
- prompt injection and poisoned tool output are real risks
- semantic extraction should stay conservative unless reviewed

## Reporting

If you find a security issue, report it privately to the project maintainers instead of opening a public issue with exploit details.
