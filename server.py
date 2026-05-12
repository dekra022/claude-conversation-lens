from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse
from zoneinfo import ZoneInfo


APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
DEFAULT_DATA_DIR = Path(os.environ.get("CLAUDE_LOG_DIR", APP_ROOT / "data"))
LOCAL_TZ = ZoneInfo(os.environ.get("CLAUDE_LENS_TZ", "Asia/Shanghai"))
MAX_LIMIT = 500

SUMMARY_CACHE: dict[tuple[str, int, int], dict[str, Any]] = {}


TAG_REPLACEMENTS = [
    (re.compile(r"<local-command-caveat>.*?</local-command-caveat>", re.S), ""),
    (re.compile(r"<command-name>(.*?)</command-name>", re.S), r"Command: \1"),
    (re.compile(r"<command-message>(.*?)</command-message>", re.S), r"Message: \1"),
    (re.compile(r"<command-args>(.*?)</command-args>", re.S), r"Args: \1"),
    (re.compile(r"<local-command-stdout>(.*?)</local-command-stdout>", re.S), r"\1"),
    (re.compile(r"<local-command-stderr>(.*?)</local-command-stderr>", re.S), r"\1"),
]

WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s\"'<>|]+")
UNIX_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:[\w.\-]+/)+[\w.\-]+")
UUID_STEM_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def parse_iso_timestamp(value: str | None) -> dict[str, Any]:
    if not value:
        return {"utc": None, "local": None, "epoch_ms": None}
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        utc_dt = dt.astimezone(timezone.utc)
        local_dt = utc_dt.astimezone(LOCAL_TZ)
        return {
            "utc": utc_dt.isoformat(),
            "local": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "epoch_ms": int(utc_dt.timestamp() * 1000),
            "local_dt": local_dt,
        }
    except ValueError:
        return {"utc": value, "local": value, "epoch_ms": None, "local_dt": None}


def parse_local_filter(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=LOCAL_TZ)
        except ValueError:
            continue
    return None


def clean_markup(text: Any) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False, indent=2)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in TAG_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def short_text(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def title_from_snippet(text: str) -> str:
    text = clean_markup(text)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"^#+\s*", "", text.strip())
    candidates = []
    for line in text.splitlines():
        line = line.strip(" -#\t")
        if not line:
            continue
        if line.startswith(("Command:", "Args:", "Message:")):
            continue
        candidates.append(line)
    title = candidates[0] if candidates else text
    title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)
    title = re.sub(r"`([^`]+)`", r"\1", title)
    title = re.sub(r"\s+", " ", title).strip(" .。")
    return short_text(title, 72) or "Untitled session"


def is_title_noise(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", clean_markup(text)).strip().lower()
    if not normalized:
        return True
    noise_prefixes = (
        "command:",
        "message: clear",
        "args:",
        "file created successfully",
        "file has been updated",
        "local-command",
        "[private reasoning omitted]",
    )
    if normalized in {"/clear", "clear", "command: /clear message: clear args:"}:
        return True
    return any(normalized.startswith(prefix) for prefix in noise_prefixes)


def title_score(text: str) -> int:
    normalized = re.sub(r"\s+", " ", clean_markup(text)).strip()
    if is_title_noise(normalized):
        return -100
    score = 0
    if re.search(r"[\u4e00-\u9fff]", normalized):
        score += 30
    if re.search(r"\b(why|how|what|analyze|build|implement|fix|design|search|train|evaluate)\b", normalized, re.I):
        score += 14
    if re.search(r"(分析|实现|搜索|训练|评估|方案|问题|架构|实验|结果)", normalized):
        score += 18
    if normalized.startswith(("#", "I need to", "Looking at", "基于", "现在", "请", "你")):
        score += 12
    if 24 <= len(normalized) <= 180:
        score += 10
    if re.search(r"(^|\s)(python|torchrun|cuda_visible_devices|cd |ls |find |git |npm |pip )", normalized, re.I):
        score -= 35
    if re.search(r"^[{\[]", normalized) or "file_path" in normalized:
        score -= 30
    if re.search(r"[A-Za-z]:\\|/Users/|~/", normalized):
        score -= 20
    return score


def build_display_title(path: Path, candidates: list[dict[str, Any]], first_ts: str | None) -> str:
    if not UUID_STEM_RE.match(path.stem):
        return path.stem
    if candidates:
        best = max(candidates, key=lambda item: title_score(item.get("title", "")))
        title = title_from_snippet(best.get("title", ""))
    else:
        title = "Claude Code session"
    date = first_ts[:10] if first_ts else path.stem[:8]
    return f"{title} · {date}"


def detect_language(tool_name: str, text: str) -> str:
    lowered = tool_name.lower()
    stripped = text.lstrip()
    if "patch" in lowered or stripped.startswith("*** Begin Patch"):
        return "diff"
    if "bash" in lowered or "shell" in lowered or "command" in lowered:
        return "bash"
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    if "def " in text or "import " in text or "class " in text:
        return "python"
    return "text"


def format_tool_input(tool_name: str, payload: Any) -> tuple[str, str]:
    if payload is None:
        return "", "text"
    if isinstance(payload, dict):
        for key in ("command", "cmd", "script"):
            if key in payload and isinstance(payload[key], str):
                return clean_markup(payload[key]), "bash"
        for key in ("content", "code", "patch"):
            if key in payload and isinstance(payload[key], str):
                text = clean_markup(payload[key])
                return text, detect_language(tool_name, text)
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        return text, "json"
    text = clean_markup(payload)
    return text, detect_language(tool_name, text)


def normalize_block(item: Any, include_thinking: bool = False) -> dict[str, Any] | None:
    if isinstance(item, str):
        text = clean_markup(item)
        if not text:
            return None
        return {"kind": "text", "title": None, "text": text, "language": "text"}

    if not isinstance(item, dict):
        text = clean_markup(item)
        if not text:
            return None
        return {"kind": "text", "title": None, "text": text, "language": "text"}

    item_type = item.get("type") or "object"

    if item_type == "text":
        text = clean_markup(item.get("text", ""))
        if not text:
            return None
        return {"kind": "text", "title": None, "text": text, "language": "text"}

    if item_type == "thinking":
        if not include_thinking:
            return {
                "kind": "thinking",
                "title": "Private reasoning",
                "text": "[private reasoning omitted]",
                "language": "text",
                "hidden": True,
            }
        text = clean_markup(item.get("thinking", ""))
        return {"kind": "thinking", "title": "Private reasoning", "text": text, "language": "text"}

    if item_type == "tool_use":
        tool_name = item.get("name") or "unknown_tool"
        text, language = format_tool_input(tool_name, item.get("input"))
        return {
            "kind": "tool_use",
            "title": tool_name,
            "text": text,
            "language": language,
            "tool": tool_name,
            "tool_use_id": item.get("id"),
        }

    if item_type == "tool_result":
        content = item.get("content", "")
        if isinstance(content, list):
            parts = []
            for child in content:
                block = normalize_block(child, include_thinking=include_thinking)
                if block and block.get("text"):
                    parts.append(block["text"])
            text = "\n\n".join(parts)
        else:
            text = clean_markup(content)
        return {
            "kind": "tool_result",
            "title": "Tool result",
            "text": text,
            "language": "text",
            "tool_use_id": item.get("tool_use_id"),
            "is_error": bool(item.get("is_error")),
        }

    text = clean_markup(item)
    if not text:
        return None
    return {"kind": item_type, "title": item_type, "text": text, "language": "json"}


def extract_blocks(record: dict[str, Any], include_thinking: bool = False) -> list[dict[str, Any]]:
    raw_content: Any = None
    message = record.get("message")
    if isinstance(message, dict):
        raw_content = message.get("content")
    if raw_content is None:
        raw_content = record.get("content")

    if raw_content is None and record.get("type") == "file-history-snapshot":
        snap = record.get("snapshot") or {}
        stamp = snap.get("timestamp") or record.get("timestamp") or ""
        return [{"kind": "snapshot", "title": "File history snapshot", "text": stamp, "language": "text"}]

    items = raw_content if isinstance(raw_content, list) else [raw_content]
    blocks: list[dict[str, Any]] = []
    for item in items:
        block = normalize_block(item, include_thinking=include_thinking)
        if block:
            blocks.append(block)
    return blocks


def infer_role(record: dict[str, Any], blocks: list[dict[str, Any]]) -> str:
    if blocks and all(block.get("kind") == "tool_result" for block in blocks):
        return "tool"
    msg = record.get("message")
    if isinstance(msg, dict) and msg.get("role"):
        role = str(msg["role"])
    else:
        role = str(record.get("type") or "unknown")
    if role == "user" and blocks and all(block.get("kind") == "tool_result" for block in blocks):
        return "tool"
    if role in {"assistant", "user", "system", "tool"}:
        return role
    if record.get("type") == "file-history-snapshot":
        return "system"
    return role


def extract_paths(text: str) -> set[str]:
    paths = set(WINDOWS_PATH_RE.findall(text))
    paths.update(UNIX_PATH_RE.findall(text))
    return paths


def block_text(blocks: list[dict[str, Any]], include_tools: bool = True) -> str:
    parts = []
    for block in blocks:
        if block.get("hidden"):
            continue
        if not include_tools and block.get("kind") in {"tool_use", "tool_result"}:
            continue
        text = block.get("text") or ""
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()


def record_to_event(record: dict[str, Any], line_no: int, include_thinking: bool = False) -> dict[str, Any]:
    blocks = extract_blocks(record, include_thinking=include_thinking)
    role = infer_role(record, blocks)
    ts = parse_iso_timestamp(record.get("timestamp"))
    usage = {}
    message = record.get("message")
    if isinstance(message, dict) and isinstance(message.get("usage"), dict):
        usage = message["usage"]

    visible_text = block_text(blocks)
    tools = [block.get("tool") for block in blocks if block.get("kind") == "tool_use" and block.get("tool")]
    paths: set[str] = set()
    commands: list[str] = []
    for block in blocks:
        text = block.get("text") or ""
        paths.update(extract_paths(text))
        if block.get("kind") == "tool_use" and block.get("language") == "bash" and text:
            commands.append(text.splitlines()[0][:240])

    is_meta = bool(record.get("isMeta")) or record.get("type") in {"file-history-snapshot"}
    subtype = record.get("subtype")
    if subtype in {"local_command"} and not visible_text:
        is_meta = True

    return {
        "line": line_no,
        "uuid": record.get("uuid") or record.get("messageId") or f"line-{line_no}",
        "parentUuid": record.get("parentUuid"),
        "timestamp": {"utc": ts.get("utc"), "local": ts.get("local"), "epoch_ms": ts.get("epoch_ms")},
        "_local_dt": ts.get("local_dt"),
        "role": role,
        "raw_type": record.get("type"),
        "subtype": subtype,
        "model": message.get("model") if isinstance(message, dict) else None,
        "cwd": record.get("cwd"),
        "gitBranch": record.get("gitBranch"),
        "isMeta": is_meta,
        "blocks": blocks,
        "snippet": short_text(visible_text),
        "searchText": visible_text.lower(),
        "charCount": len(visible_text),
        "tools": tools,
        "paths": sorted(paths),
        "commands": commands,
        "usage": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        },
        "hiddenThinking": any(block.get("kind") == "thinking" and block.get("hidden") for block in blocks),
    }


def iter_events(path: Path, include_thinking: bool = False):
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                yield {"_invalid": True, "line": line_no}
                continue
            if not isinstance(record, dict):
                continue
            yield record_to_event(record, line_no, include_thinking=include_thinking)


def summarize_session(path: Path) -> dict[str, Any]:
    stat = path.stat()
    cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
    cached = SUMMARY_CACHE.get(cache_key)
    if cached:
        return cached

    roles: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    models: Counter[str] = Counter()
    cwd: Counter[str] = Counter()
    files: Counter[str] = Counter()
    chapters: list[dict[str, Any]] = []
    title_candidates: list[str] = []
    first_ts = None
    last_ts = None
    invalid_lines = 0
    total = 0
    hidden_thinking = 0
    tool_calls = 0
    code_blocks = 0
    total_chars = 0
    token_usage = Counter()
    start_time = time.perf_counter()

    for event in iter_events(path):
        if event.get("_invalid"):
            invalid_lines += 1
            continue
        total += 1
        roles[event["role"]] += 1
        total_chars += event["charCount"]
        if event["timestamp"]["local"]:
            first_ts = first_ts or event["timestamp"]["local"]
            last_ts = event["timestamp"]["local"]
        if event.get("model"):
            models[event["model"]] += 1
        if event.get("cwd"):
            cwd[event["cwd"]] += 1
        if event.get("hiddenThinking"):
            hidden_thinking += 1
        for tool in event.get("tools", []):
            tools[tool] += 1
            tool_calls += 1
        for block in event.get("blocks", []):
            if block.get("language") in {"python", "bash", "diff", "json"} or "```" in (block.get("text") or ""):
                code_blocks += 1
        for path_value in event.get("paths", []):
            files[path_value] += 1
        for key, value in event.get("usage", {}).items():
            if isinstance(value, int):
                token_usage[key] += value
        if event["role"] == "user" and not event.get("isMeta") and event.get("snippet") and len(chapters) < 18:
            chapters.append(
                {
                    "time": event["timestamp"]["local"],
                    "line": event["line"],
                    "title": short_text(event["snippet"], 120),
                }
            )
        if (
            event["role"] in {"user", "assistant"}
            and not event.get("isMeta")
            and event.get("snippet")
            and not is_title_noise(event["snippet"])
            and len(title_candidates) < 24
        ):
            title_candidates.append(event["snippet"])

    summary = {
        "id": path.name,
        "name": path.stem,
        "displayTitle": build_display_title(
            path,
            [{"title": item, "time": first_ts, "line": 0} for item in title_candidates] or chapters,
            first_ts,
        ),
        "path": str(path),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime, LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "firstTimestamp": first_ts,
        "lastTimestamp": last_ts,
        "lineCount": total + invalid_lines,
        "eventCount": total,
        "invalidLines": invalid_lines,
        "roles": dict(roles),
        "tools": dict(tools.most_common(20)),
        "models": dict(models.most_common(8)),
        "topCwd": cwd.most_common(1)[0][0] if cwd else None,
        "topFiles": [{"path": value, "count": count} for value, count in files.most_common(14)],
        "chapters": chapters,
        "hiddenThinking": hidden_thinking,
        "toolCalls": tool_calls,
        "codeBlocks": code_blocks,
        "totalChars": total_chars,
        "tokenUsage": dict(token_usage),
        "scanMs": round((time.perf_counter() - start_time) * 1000, 2),
    }
    SUMMARY_CACHE.clear()
    SUMMARY_CACHE[cache_key] = summary
    return summary


def bool_param(params: dict[str, list[str]], name: str, default: bool = False) -> bool:
    raw = params.get(name, [str(default).lower()])[0].lower()
    return raw in {"1", "true", "yes", "on"}


def int_param(params: dict[str, list[str]], name: str, default: int) -> int:
    try:
        return int(params.get(name, [str(default)])[0])
    except ValueError:
        return default


def resolve_session(data_dir: Path, session_id: str | None) -> Path:
    if not session_id:
        raise FileNotFoundError("missing session id")
    decoded = unquote(session_id)
    candidate = (data_dir / Path(decoded).name).resolve()
    data_root = data_dir.resolve()
    if candidate.parent != data_root or candidate.suffix.lower() != ".jsonl" or not candidate.exists():
        raise FileNotFoundError(decoded)
    return candidate


def event_matches(
    event: dict[str, Any],
    query: str,
    role: str,
    start_dt: datetime | None,
    end_dt: datetime | None,
    include_meta: bool,
    include_system: bool,
    include_tools: bool,
) -> bool:
    if event.get("_invalid"):
        return False
    if event.get("isMeta") and not include_meta:
        return False
    if event.get("role") == "system" and not include_system:
        return False
    if event.get("role") == "tool" and not include_tools:
        return False
    if role != "all" and event.get("role") != role:
        return False
    local_dt = event.get("_local_dt")
    if start_dt and local_dt and local_dt < start_dt:
        return False
    if end_dt and local_dt and local_dt > end_dt:
        return False
    if query and query.lower() not in event.get("searchText", ""):
        return False
    return True


def public_event(event: dict[str, Any], include_tools: bool = True) -> dict[str, Any]:
    event = {key: value for key, value in event.items() if not key.startswith("_")}
    if not include_tools:
        event["blocks"] = [block for block in event["blocks"] if block.get("kind") not in {"tool_use", "tool_result"}]
    return event


def query_events(path: Path, params: dict[str, list[str]]) -> dict[str, Any]:
    query = params.get("q", [""])[0].strip()
    role = params.get("role", ["all"])[0]
    offset = max(0, int_param(params, "offset", 0))
    limit = min(MAX_LIMIT, max(1, int_param(params, "limit", 150)))
    include_meta = bool_param(params, "includeMeta", False)
    include_system = bool_param(params, "includeSystem", True)
    include_tools = bool_param(params, "includeTools", True)
    include_thinking = bool_param(params, "includeThinking", False)
    start_dt = parse_local_filter(params.get("start", [None])[0])
    end_dt = parse_local_filter(params.get("end", [None])[0])

    events: list[dict[str, Any]] = []
    matched = 0
    for event in iter_events(path, include_thinking=include_thinking):
        if not event_matches(event, query, role, start_dt, end_dt, include_meta, include_system, include_tools):
            continue
        if matched >= offset and len(events) < limit:
            events.append(public_event(event, include_tools=include_tools))
        matched += 1

    return {
        "summary": summarize_session(path),
        "filters": {
            "q": query,
            "role": role,
            "offset": offset,
            "limit": limit,
            "includeMeta": include_meta,
            "includeSystem": include_system,
            "includeTools": include_tools,
            "start": params.get("start", [""])[0],
            "end": params.get("end", [""])[0],
        },
        "matched": matched,
        "nextOffset": offset + len(events) if offset + len(events) < matched else None,
        "events": events,
    }


def render_block_markdown(block: dict[str, Any]) -> str:
    kind = block.get("kind")
    title = block.get("title") or kind
    text = block.get("text") or ""
    if not text:
        return ""
    if block.get("hidden"):
        return f"> {text}"
    if kind in {"tool_use", "tool_result"}:
        language = block.get("language") or "text"
        return f"<details>\n<summary>{title}</summary>\n\n```{language}\n{text}\n```\n\n</details>"
    if kind == "snapshot":
        return f"> File history snapshot: {text}"
    return text


def export_markdown(path: Path, params: dict[str, list[str]]) -> str:
    data = query_events(path, {**params, "offset": ["0"], "limit": [str(MAX_LIMIT)]})
    summary = data["summary"]
    lines = [
        f"# Claude Code Conversation Export: {summary['name']}",
        "",
        f"- Source: `{summary['path']}`",
        f"- Time zone: `{LOCAL_TZ.key}`",
        f"- Range: `{summary.get('firstTimestamp')}` to `{summary.get('lastTimestamp')}`",
        f"- Events: `{data['matched']}` matched of `{summary['eventCount']}` parsed",
        f"- Tool calls: `{summary['toolCalls']}`",
        "",
        "## Timeline",
        "",
    ]
    for event in data["events"]:
        lines.append(f"### {event['timestamp']['local'] or 'no timestamp'} - {event['role'].title()}")
        if event.get("model"):
            lines.append(f"_Model: {event['model']}_")
        rendered = [render_block_markdown(block) for block in event.get("blocks", [])]
        rendered = [item for item in rendered if item]
        lines.append("\n\n".join(rendered) if rendered else event.get("snippet", ""))
        lines.append("")
    if data.get("nextOffset") is not None:
        lines.append(f"> Export truncated at {MAX_LIMIT} events. Narrow the filters for a smaller export.")
    return "\n".join(lines)


def export_html(path: Path, params: dict[str, list[str]]) -> str:
    data = query_events(path, {**params, "offset": ["0"], "limit": [str(MAX_LIMIT)]})
    summary = data["summary"]
    rows = []
    for event in data["events"]:
        blocks = []
        for block in event.get("blocks", []):
            text = html.escape(block.get("text") or "")
            title = html.escape(block.get("title") or block.get("kind") or "")
            if block.get("kind") in {"tool_use", "tool_result"}:
                blocks.append(f"<details><summary>{title}</summary><pre>{text}</pre></details>")
            else:
                blocks.append(f"<p>{text.replace(chr(10), '<br>')}</p>")
        rows.append(
            "<article>"
            f"<h2>{html.escape(event['role'].title())} <small>{html.escape(event['timestamp']['local'] or '')}</small></h2>"
            + "\n".join(blocks)
            + "</article>"
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{html.escape(summary['name'])}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; max-width: 960px; margin: 40px auto; line-height: 1.65; color: #1c2633; }}
    article {{ border-top: 1px solid #d7dde8; padding: 20px 0; }}
    h1 {{ font-size: 30px; }}
    h2 {{ font-size: 18px; }}
    small {{ color: #6a7280; font-weight: 500; }}
    pre {{ overflow:auto; background:#101725; color:#edf3ff; padding:14px; border-radius:8px; }}
    details {{ margin: 10px 0; }}
  </style>
</head>
<body>
  <h1>Claude Code Conversation Export</h1>
  <p><strong>Source:</strong> {html.escape(summary['path'])}</p>
  {''.join(rows)}
</body>
</html>"""


def list_sessions(data_dir: Path) -> list[dict[str, Any]]:
    if not data_dir.exists():
        return []
    sessions = []
    for path in sorted(data_dir.glob("*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True):
        sessions.append(summarize_session(path))
    return sessions


class LensHandler(SimpleHTTPRequestHandler):
    server_version = "ClaudeConversationLens/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    @property
    def data_dir(self) -> Path:
        return self.server.data_dir  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                self.serve_file(STATIC_ROOT / "index.html")
            elif parsed.path.startswith("/static/"):
                requested = (STATIC_ROOT / parsed.path.removeprefix("/static/")).resolve()
                if STATIC_ROOT.resolve() not in requested.parents and requested != STATIC_ROOT.resolve():
                    self.send_error(HTTPStatus.NOT_FOUND)
                else:
                    self.serve_file(requested)
            elif parsed.path == "/api/config":
                self.send_json({"dataDir": str(self.data_dir), "timezone": LOCAL_TZ.key, "maxLimit": MAX_LIMIT})
            elif parsed.path == "/api/sessions":
                self.send_json({"sessions": list_sessions(self.data_dir)})
            elif parsed.path == "/api/session":
                path = resolve_session(self.data_dir, params.get("id", [None])[0])
                self.send_json(query_events(path, params))
            elif parsed.path == "/api/export":
                path = resolve_session(self.data_dir, params.get("id", [None])[0])
                fmt = params.get("format", ["markdown"])[0]
                self.send_export(path, params, fmt)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except FileNotFoundError as exc:
            self.send_json({"error": f"Session not found: {exc}"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_export(self, path: Path, params: dict[str, list[str]], fmt: str) -> None:
        safe_name = quote(path.stem)
        if fmt == "html":
            content = export_html(path, params).encode("utf-8")
            content_type = "text/html; charset=utf-8"
            filename = f"{safe_name}.html"
        elif fmt == "json":
            content = json.dumps(query_events(path, {**params, "offset": ["0"], "limit": [str(MAX_LIMIT)]}), ensure_ascii=False, indent=2).encode("utf-8")
            content_type = "application/json; charset=utf-8"
            filename = f"{safe_name}.json"
        else:
            content = export_markdown(path, params).encode("utf-8")
            content_type = "text/markdown; charset=utf-8"
            filename = f"{safe_name}.md"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Claude Code JSONL conversation explorer")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing Claude Code .jsonl files")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    server = ThreadingHTTPServer((args.host, args.port), LensHandler)
    server.data_dir = data_dir  # type: ignore[attr-defined]
    print(f"Claude Conversation Lens")
    print(f"Data dir: {data_dir}")
    print(f"Open: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
