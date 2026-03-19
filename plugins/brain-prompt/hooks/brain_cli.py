#!/usr/bin/env python3
"""CLI bridge used by JS hooks/plugins to talk to OpenClawBrain persistence.

The JS hooks stay thin; Python owns memory semantics and on-disk state.
"""

from __future__ import annotations

import json
import inspect
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain import OpenClawBrain  # noqa: E402


PREFERENCE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(?:用户|对方|ta|他|她).{0,12}(?:喜欢|偏好|习惯|希望|想要)(.+)",
        r"(?:please|pls)?\s*(?:call|address)\s+(?:the user|me)\s+(.+)",
        r"(?:user|they)\s+(?:likes?|prefers?)\s+(.+)",
        r"(?:我)?喜欢被叫(.+)",
        r"(?:叫我|称呼我)(.+)",
        r"(?:nickname|call me as)\s*[:：]?\s*(.+)",
    ]
]
RULE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(?:不要|别|务必|必须|记得|需要)(.+)",
        r"(?:always|never|must|should|do not|don't)\s+(.+)",
    ]
]
TASK_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(?:任务|todo|待办|需要做|帮我)(.+)",
        r"(?:need to|todo|task:)\s+(.+)",
        r"(?:要|需要|得|需)(?:准备|提交|整理|完成|处理)(.+)",
        r"(?:准备|提交|整理|完成|处理)(.+)",
    ]
]
FACT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(?:用户|对方|ta|他|她).{0,12}(?:是|在|用|来自|叫)(.+)",
        r"(?:user|they)\s+(?:is|are|uses?|works? on|comes? from)\s+(.+)",
    ]
]
ASSISTANT_COMMIT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(?:我会|我将|稍后|接下来|下一步|我先|我准备)(.+)",
        r"(?:i will|i'll|next i(?:'ll)?|going to|let me|i(?:'m| am) going to)\s+(.+)",
    ]
]
ASSISTANT_RESULT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(?:已|已经|完成|修复|更新|处理|搞定|确认|验证|排查)(.+)",
        r"(?:done|fixed|updated|completed|implemented|verified|confirmed|checked)\s+(.+)",
    ]
]
ASSISTANT_DECISION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(?:结论是|结论：|决定|决定先|现在判断|判断是|原因是|核心问题是|主因是|根因是)(.+)",
        r"(?:问题不在|不是)(.+)",
        r"(?:the conclusion is|we decided|decision:|root cause is|the problem is not|the issue is not)\s+(.+)",
    ]
]
ASSISTANT_STATE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(?:现在状态是|目前状态是|当前状态是)(.+)",
        r"(?:now the state is|current state is)\s+(.+)",
    ]
]
TIME_MEETING_RE = re.compile(
    r"(?:今天|明天|后天|今晚|明早|明晚|周[一二三四五六日天]|星期[一二三四五六日天])?.{0,8}"
    r"(?:上午|下午|晚上|中午|早上)?\s*(?:\d{1,2}[:：点时]\d{0,2}|\d{1,2}点半?|\d{1,2}:\d{2}).{0,12}(?:会|会议|开会)",
    re.IGNORECASE,
)
NOISE_PREFIX_RE = re.compile(r"^(?:请)?记住[:：]?\s*", re.IGNORECASE)
LEADING_FILLER_RE = re.compile(r"^(?:另外|还有|然后|以及|并且|顺便说下|顺便)\s*", re.IGNORECASE)
CLAUSE_SPLIT_RE = re.compile(r"[\n。！？!?；;]+|(?<!\d),(?!\d)|，")
STATE_SUMMARY_KEY = "assistant_state_summary"


def load_payload() -> Dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def _workspace_root_from_project(project_root: Path) -> Optional[Path]:
    parts = list(project_root.parts)
    if "projects" in parts:
        idx = parts.index("projects")
        if idx > 0:
            return Path(*parts[:idx])
    return None


def default_store_root(payload: Optional[Dict[str, Any]] = None) -> Path:
    payload = payload or {}
    explicit_workspace = payload.get("workspace_root") or os.environ.get("OPENCLAW_WORKSPACE_DIR")
    if explicit_workspace:
        return Path(explicit_workspace) / "data" / "openclaw-brain"

    workspace_root = _workspace_root_from_project(PROJECT_ROOT)
    if workspace_root:
        return workspace_root / "data" / "openclaw-brain"

    return PROJECT_ROOT / "data" / "openclaw-brain"


def resolve_store(payload: Dict[str, Any]) -> Path:
    root = payload.get("store_root") or default_store_root(payload)
    return Path(root)


def load_brain(payload: Dict[str, Any]) -> OpenClawBrain:
    store = resolve_store(payload)
    kwargs = {
        "attention_threshold": payload.get("attention_threshold", 0.5),
        "working_memory_capacity": payload.get("working_memory_capacity", 20),
        "hippocampus_capacity": payload.get("hippocampus_capacity", 1000),
        "consolidation_interval_hours": payload.get("consolidation_interval_hours", 4.0),
    }
    backend = payload.get("backend", "jsonl")
    has_existing = any(store.glob("*.jsonl")) if backend == "jsonl" else store.exists() and any(store.iterdir())
    if has_existing:
        return OpenClawBrain.load(store, backend=backend, **kwargs)
    return OpenClawBrain(**kwargs)


def save_brain(brain: OpenClawBrain, payload: Dict[str, Any]) -> Dict[str, str]:
    backend = payload.get("backend", "jsonl")
    written = brain.save(resolve_store(payload), backend=backend)
    return {name: str(path) for name, path in written.items()}


def _latest_created_at(records: List[Any]) -> Optional[datetime]:
    timestamps = [getattr(record, "created_at", None) for record in records if getattr(record, "created_at", None) is not None]
    return max(timestamps) if timestamps else None


def should_auto_consolidate(brain: OpenClawBrain, payload: Dict[str, Any]) -> bool:
    if payload.get("trigger_consolidation") is True:
        return True
    if payload.get("trigger_consolidation") is False:
        return False
    if not payload.get("auto_consolidate", True):
        return False

    pending_batch_size = int(payload.get("auto_consolidate_batch_size", 12))
    stale_after_minutes = int(payload.get("auto_consolidate_stale_minutes", 30))

    hippocampus_items = list(brain.hippocampus.encoding_buffer)
    if not hippocampus_items:
        return False

    latest_episodic = _latest_created_at(list(brain.episodic.memories))
    if latest_episodic is None:
        pending = hippocampus_items
    else:
        pending = [item for item in hippocampus_items if getattr(item, "created_at", datetime.min) > latest_episodic]

    if not pending:
        return False
    if len(pending) >= pending_batch_size:
        return True

    oldest_pending = min(getattr(item, "created_at", datetime.now()) for item in pending)
    return oldest_pending <= datetime.now() - timedelta(minutes=stale_after_minutes)


def _clean_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _strip_noise_prefix(text: str) -> str:
    text = _clean_text(text)
    text = NOISE_PREFIX_RE.sub("", text)
    text = LEADING_FILLER_RE.sub("", text)
    return text.strip(" ：:,-")


def _normalize_memory_text(text: str) -> str:
    text = _strip_noise_prefix(text)
    return text.rstrip("，。,.!！?？；;")


def _extract_first(patterns: List[re.Pattern[str]], text: str) -> Optional[str]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _normalize_memory_text(match.group(1))
    return None


def _message_role(message: Dict[str, Any]) -> str:
    role = str(message.get("role") or "").strip().lower()
    if role:
        return role
    author = str(message.get("author") or "").strip().lower()
    if author in {"assistant", "system", "openclaw", "bot"}:
        return "assistant"
    return "user"


def _split_clauses(content: str) -> List[str]:
    clauses = [_normalize_memory_text(part) for part in CLAUSE_SPLIT_RE.split(content)]
    return [clause for clause in clauses if clause]


def _append_memory(memories: List[Dict[str, Any]], seen: set[tuple[str, str]], text: str, context: Dict[str, Any], importance: float, mode: str) -> None:
    normalized = _normalize_memory_text(text)
    if not normalized:
        return
    key = (mode, normalized.lower())
    if key in seen:
        return
    seen.add(key)
    memories.append(
        {
            "text": normalized,
            "context": {**context, "definition": normalized},
            "importance": importance,
            "mode": mode,
        }
    )


def _extract_user_clause_memories(clause: str, base_context: Dict[str, Any], memories: List[Dict[str, Any]], seen: set[tuple[str, str]]) -> None:
    preference = _extract_first(PREFERENCE_PATTERNS, clause)
    if preference:
        if not preference.startswith("被叫") and ("叫" in clause or "call me" in clause.lower() or "nickname" in clause.lower()):
            preference = f"被叫{preference.lstrip('做成叫作是为') }".strip()
        _append_memory(memories, seen, preference, {**base_context, "kind": "preference", "category": "preference"}, 0.92, "semantic")

    if TIME_MEETING_RE.search(clause):
        _append_memory(memories, seen, clause, {**base_context, "kind": "task", "category": "schedule"}, 0.9, "semantic")

    if any(token in clause for token in ["准备", "提交", "整理", "完成", "处理"]) and not TIME_MEETING_RE.search(clause):
        task = _extract_first(TASK_PATTERNS, clause) or clause
        _append_memory(memories, seen, task, {**base_context, "kind": "task", "category": "task"}, 0.84, "semantic")

    rule = _extract_first(RULE_PATTERNS, clause)
    if rule and len(rule) >= 2:
        _append_memory(memories, seen, rule, {**base_context, "kind": "rule", "category": "rule"}, 0.9, "semantic")

    fact = _extract_first(FACT_PATTERNS, clause)
    if fact and len(fact) >= 2:
        _append_memory(memories, seen, fact, {**base_context, "kind": "fact", "category": "fact"}, 0.78, "semantic")


def _build_state_summary_fields(brain: OpenClawBrain, extracted: List[Dict[str, Any]]) -> Dict[str, str]:
    existing = brain.semantic.find_by_name(STATE_SUMMARY_KEY)
    fields: Dict[str, str] = {}
    if existing:
        for key in ("current_state", "latest_decision", "latest_result", "next_step"):
            value = existing.properties.get(key)
            if value:
                fields[key] = _clean_text(value)

    priority = {
        "assistant_state": "current_state",
        "assistant_decision": "latest_decision",
        "assistant_result": "latest_result",
        "assistant_commit": "next_step",
    }
    for item in extracted:
        subtype = str(item.get("context", {}).get("source_subtype") or "").strip().lower()
        target = priority.get(subtype)
        if target and item.get("text"):
            fields[target] = _normalize_memory_text(item["text"])
    return fields


def _render_state_summary(fields: Dict[str, str]) -> str:
    order = [
        ("current_state", "当前进展"),
        ("latest_decision", "当前判断"),
        ("latest_result", "已确认"),
        ("next_step", "下一步"),
    ]
    lines = [f"{label}：{fields[key]}" for key, label in order if fields.get(key)]
    return "；".join(lines)


def update_state_summary(brain: OpenClawBrain, message: Dict[str, Any], extracted: List[Dict[str, Any]]) -> Optional[Any]:
    if _message_role(message) != "assistant":
        return None
    if not any((item.get("context") or {}).get("source_subtype") in {"assistant_state", "assistant_decision", "assistant_result", "assistant_commit"} for item in extracted):
        return None

    fields = _build_state_summary_fields(brain, extracted)
    summary_text = _render_state_summary(fields)
    if not summary_text:
        return None

    return brain.remember(
        STATE_SUMMARY_KEY,
        context={
            "name": STATE_SUMMARY_KEY,
            "kind": "summary",
            "category": "state_summary",
            "source": "message",
            "role": "assistant",
            "source_subtype": "assistant_state_summary",
            "definition": summary_text,
            **fields,
        },
        importance=0.98,
        mode="semantic",
    )


def extract_message_memories(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    content = _clean_text(message.get("content") or message.get("text") or "")
    if not content:
        return []

    role = _message_role(message)
    base_context = {
        "source": "message",
        "channel": message.get("channel"),
        "author": message.get("author"),
        "message_id": message.get("message_id"),
        "role": role,
    }

    memories: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    if role == "assistant":
        commit = _extract_first(ASSISTANT_COMMIT_PATTERNS, content)
        result = _extract_first(ASSISTANT_RESULT_PATTERNS, content)
        decision = _extract_first(ASSISTANT_DECISION_PATTERNS, content)
        state = _extract_first(ASSISTANT_STATE_PATTERNS, content)

        if commit:
            _append_memory(
                memories,
                seen,
                commit,
                {**base_context, "kind": "task", "source_subtype": "assistant_commit"},
                0.88,
                "working",
            )
            _append_memory(
                memories,
                seen,
                commit,
                {**base_context, "kind": "task", "source_subtype": "assistant_commit"},
                0.74,
                "episodic",
            )

        if result:
            _append_memory(
                memories,
                seen,
                result,
                {**base_context, "kind": "fact", "source_subtype": "assistant_result"},
                0.82,
                "episodic",
            )
            _append_memory(
                memories,
                seen,
                result,
                {**base_context, "kind": "fact", "source_subtype": "assistant_result"},
                0.76,
                "semantic",
            )

        if decision:
            _append_memory(
                memories,
                seen,
                decision,
                {**base_context, "kind": "rule", "category": "decision", "source_subtype": "assistant_decision"},
                0.86,
                "semantic",
            )
            _append_memory(
                memories,
                seen,
                decision,
                {**base_context, "kind": "rule", "category": "decision", "source_subtype": "assistant_decision"},
                0.72,
                "episodic",
            )

        if state:
            _append_memory(
                memories,
                seen,
                state,
                {**base_context, "kind": "fact", "category": "state", "source_subtype": "assistant_state"},
                0.8,
                "semantic",
            )
        return memories

    for clause in _split_clauses(content):
        _extract_user_clause_memories(clause, base_context, memories, seen)

    if not memories and len(content) <= 280 and any(token in content.lower() for token in ["记住", "remember", "important", "偏好", "规则", "任务"]):
        _append_memory(
            memories,
            seen,
            content,
            {**base_context, "kind": "fact", "category": "fact"},
            0.68,
            "episodic",
        )
    return memories


def remember_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    brain = load_brain(payload)
    message = payload.get("message", {})
    extracted = extract_message_memories(message)

    remembered = []
    content = _clean_text(message.get("content") or message.get("text") or "")
    role = _message_role(message)
    if payload.get("persist_raw_message", True) and content:
        raw_importance = float(payload.get("importance") or 0.55)
        raw_memory = brain.remember(
            content,
            context={
                "source": "message",
                "channel": message.get("channel"),
                "author": message.get("author"),
                "message_id": message.get("message_id"),
                "role": role,
                "kind": "message",
                "definition": content,
            },
            importance=max(0.35, min(raw_importance, 1.0)),
            mode="episodic",
        )
        if raw_memory is not None:
            remembered.append(raw_memory)

    for item in extracted:
        memory = brain.remember(item["text"], context=item["context"], importance=item["importance"], mode=item["mode"])
        if memory is not None:
            remembered.append(memory)

    state_summary = update_state_summary(brain, message, extracted)
    if state_summary is not None:
        remembered.append(state_summary)

    consolidation = None
    if should_auto_consolidate(brain, payload):
        consolidation = brain.consolidate()
    written = save_brain(brain, payload)
    return {
        "remembered": bool(remembered),
        "memory_id": remembered[0].id if remembered else None,
        "memory_count": len(remembered),
        "memory_kinds": [getattr(memory.kind, "value", str(memory.kind)) for memory in remembered],
        "resolved_store_root": str(resolve_store(payload)),
        "consolidation": consolidation,
        "written": written,
    }


def build_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    brain = load_brain(payload)
    build_context_kwargs = {
        "query": payload.get("query", ""),
        "recent_messages": payload.get("recent_messages") or [],
        "recent_message_ids": payload.get("recent_message_ids") or [],
        "limit": int(payload.get("limit", 5)),
        "context": payload.get("context") or {},
        "emotion": payload.get("emotion"),
        "max_chars": payload.get("max_chars"),
        "max_estimated_tokens": payload.get("max_estimated_tokens"),
    }
    supported = set(inspect.signature(brain.build_context).parameters.keys())
    result = brain.build_context(**{key: value for key, value in build_context_kwargs.items() if key in supported})
    result["recall_mode"] = result.get("recall_mode", "full_snapshot")
    result["candidate_count"] = int(result.get("candidate_count") or 0)
    result["resolved_store_root"] = str(resolve_store(payload))
    result["debug"] = _build_context_debug(payload, result)
    return result


def _tool_preview(value: Any, limit: int = 240) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _clean_text(value)[:limit]
    try:
        return json.dumps(value, ensure_ascii=False)[:limit]
    except TypeError:
        return _clean_text(value)[:limit]


def _preview_text(value: Any, limit: int = 72) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 3)]}..."


def _summarize_context_items(items: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    previews: List[str] = []
    for item in items[:limit]:
        kind = str(item.get("kind") or "").strip()
        text = _preview_text(item.get("text") or "")
        if not text:
            continue
        previews.append(f"{kind}:{text}" if kind else text)
    return previews


def _build_context_debug(payload: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    items = result.get("items") or []
    return {
        "query": _preview_text(payload.get("query") or "", 120),
        "backend": payload.get("backend", "jsonl"),
        "recall_mode": result.get("recall_mode", "unknown"),
        "candidate_count": int(result.get("candidate_count") or 0),
        "selected_count": int(result.get("count") or 0),
        "context_chars": int(result.get("context_chars") or 0),
        "estimated_tokens": int(result.get("estimated_tokens") or 0),
        "recent_message_count": len(payload.get("recent_messages") or []),
        "recent_message_id_count": len(payload.get("recent_message_ids") or []),
        "item_previews": _summarize_context_items(items, 3),
    }


def extract_knowledge(tool_name: str, result: Any) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if result is None:
        return items
    if isinstance(result, dict):
        ignore = {"status", "success", "error", "message", "code"}
        for key, value in result.items():
            if key.lower() in ignore or value in (None, ""):
                continue
            preview = _tool_preview(value, limit=220)
            if not preview:
                continue
            items.append(
                {
                    "content": f"{tool_name}.{key}",
                    "definition": preview,
                    "kind": "fact",
                    "importance": 0.68,
                }
            )
    elif isinstance(result, list):
        for index, item in enumerate(result[:5]):
            preview = _tool_preview(item, limit=180)
            if preview:
                items.append(
                    {
                        "content": f"{tool_name}[{index}]",
                        "definition": preview,
                        "kind": "fact",
                        "importance": 0.58,
                    }
                )
    else:
        preview = _tool_preview(result, limit=240)
        if len(preview) >= 20:
            items.append(
                {
                    "content": f"Result from {tool_name}",
                    "definition": preview,
                    "kind": "fact",
                    "importance": 0.6,
                }
            )
    return items


def remember_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    brain = load_brain(payload)
    tool = payload.get("tool", {})
    tool_name = tool.get("name") or tool.get("tool") or "unknown"
    arguments_ = tool.get("arguments") or tool.get("args") or {}
    result = tool.get("result")
    success = tool.get("success", True)

    summary_bits = [f"tool={tool_name}"]
    if arguments_:
        summary_bits.append(f"args={_tool_preview(arguments_, 120)}")
    preview = _tool_preview(result, 220)
    if preview:
        summary_bits.append(f"result={preview}")
    summary_bits.append(f"success={bool(success)}")
    episodic = brain.remember(
        "; ".join(summary_bits),
        context={
            "source": "tool",
            "tool_name": tool_name,
            "kind": "tool",
            "definition": preview or f"Tool {tool_name} executed",
        },
        importance=0.66 if success else 0.78,
        mode="episodic",
    )

    knowledge_count = 0
    if payload.get("extract_knowledge", True):
        extracted = extract_knowledge(tool_name, result)
        for item in extracted:
            brain.remember(
                item["content"],
                context={"kind": item["kind"], "definition": item["definition"], "source": f"tool:{tool_name}"},
                importance=item["importance"],
                mode="semantic",
            )
        knowledge_count = len(extracted)

    consolidation = None
    if should_auto_consolidate(brain, payload):
        consolidation = brain.consolidate()
    written = save_brain(brain, payload)
    return {
        "episodic_recorded": episodic is not None,
        "knowledge_count": knowledge_count,
        "resolved_store_root": str(resolve_store(payload)),
        "consolidation": consolidation,
        "written": written,
    }


def explain_store(payload: Dict[str, Any]) -> Dict[str, Any]:
    store_root = resolve_store(payload)
    workspace_root = payload.get("workspace_root") or os.environ.get("OPENCLAW_WORKSPACE_DIR")
    if not workspace_root:
        detected = _workspace_root_from_project(PROJECT_ROOT)
        workspace_root = str(detected) if detected else None
    return {
        "project_root": str(PROJECT_ROOT),
        "workspace_root": workspace_root,
        "resolved_store_root": str(store_root),
        "cli_path": str(Path(__file__).resolve()),
    }


def main() -> int:
    payload = load_payload()
    action = payload.get("action")
    if action == "remember-message":
        result = remember_message(payload)
    elif action == "remember-tool":
        result = remember_tool(payload)
    elif action == "build-context":
        result = build_context(payload)
    elif action == "explain-store":
        result = explain_store(payload)
    else:
        raise SystemExit(f"unknown action: {action}")
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
