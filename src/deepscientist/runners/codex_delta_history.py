from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..shared import ensure_dir, read_json, utc_now, write_json

_DELTA_HISTORY_SCHEMA_VERSION = 1
_DELTA_PREVIEW_TEXT_LIMIT = 240


def _stable_payload_fingerprint(value: object) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    except TypeError:
        encoded = str(value).encode("utf-8", errors="replace")
    return hashlib.sha256(encoded).hexdigest()


def _delta_history_state_path(quest_root: Path) -> Path:
    return quest_root / ".ds" / "delta_history_state.json"


def _delta_history_state(quest_root: Path) -> dict[str, Any]:
    payload = read_json(_delta_history_state_path(quest_root), {})
    if not isinstance(payload, dict) or int(payload.get("schema_version") or 0) != _DELTA_HISTORY_SCHEMA_VERSION:
        return {"schema_version": _DELTA_HISTORY_SCHEMA_VERSION, "entries": {}}
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        payload["entries"] = {}
    return payload


def _write_delta_history_state(quest_root: Path, payload: dict[str, Any]) -> None:
    payload["schema_version"] = _DELTA_HISTORY_SCHEMA_VERSION
    payload["updated_at"] = utc_now()
    ensure_dir(_delta_history_state_path(quest_root).parent)
    write_json(_delta_history_state_path(quest_root), payload)


def _delta_preview(text: str) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= _DELTA_PREVIEW_TEXT_LIMIT:
        return normalized
    return normalized[: _DELTA_PREVIEW_TEXT_LIMIT - 1].rstrip() + "…"


def _stdout_delta_key(line: str) -> str:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return "stdout:raw"
    if not isinstance(payload, dict):
        return "stdout:raw"
    item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
    event_type = str(payload.get("type") or "").strip() or "event"
    item_type = str(item.get("type") or payload.get("item_type") or "").strip() or "item"
    tool_name = str(item.get("tool") or item.get("name") or "").strip()
    server = str(item.get("server") or "").strip()
    if server and tool_name:
        tool_name = f"{server}.{tool_name}"
    return f"stdout:{event_type}:{item_type}:{tool_name or 'none'}"


def _delta_aware_stdout_record(
    *,
    quest_root: Path,
    run_root: Path,
    line: str,
    timestamp: str,
) -> dict[str, Any]:
    fingerprint = _stable_payload_fingerprint({"line": line})
    key = _stdout_delta_key(line)
    state = _delta_history_state(quest_root)
    entries = state.setdefault("entries", {})
    previous = entries.get(key) if isinstance(entries.get(key), dict) else {}
    repeat_count = int(previous.get("repeat_count") or 1) + 1 if previous.get("fingerprint") == fingerprint else 1
    entries[key] = {
        "fingerprint": fingerprint,
        "repeat_count": repeat_count,
        "last_seen_at": timestamp,
        "last_run_root": str(run_root),
    }
    _write_delta_history_state(quest_root, state)
    if repeat_count <= 1:
        return {"timestamp": timestamp, "line": line, "fingerprint": fingerprint}
    return {
        "timestamp": timestamp,
        "delta_marker": True,
        "delta_kind": "unchanged_stdout_line",
        "fingerprint": fingerprint,
        "repeat_count": repeat_count,
        "line_preview": _delta_preview(line),
    }


def _tool_result_delta_key(event: dict[str, Any]) -> str:
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    identity = {
        "tool_name": str(event.get("tool_name") or "").strip(),
        "args": str(event.get("args") or "").strip(),
        "mcp_server": str(event.get("mcp_server") or metadata.get("mcp_server") or "").strip(),
        "mcp_tool": str(event.get("mcp_tool") or metadata.get("mcp_tool") or "").strip(),
        "command": str(metadata.get("command") or "").strip(),
    }
    return "tool_result:" + _stable_payload_fingerprint(identity)


def _tool_result_payload_fingerprint(event: dict[str, Any]) -> str:
    output = event.get("output")
    if isinstance(output, str):
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = output
        if isinstance(parsed, dict):
            packet = parsed.get("evidence_packet")
            if isinstance(packet, dict) and packet.get("payload_sha256"):
                return str(packet["payload_sha256"])
    return _stable_payload_fingerprint(
        {
            "status": event.get("status"),
            "output": output,
            "output_bytes": event.get("output_bytes"),
            "metadata": event.get("metadata"),
        }
    )


def _delta_aware_tool_result_event(
    event: dict[str, Any],
    *,
    quest_root: Path,
    run_id: str,
) -> dict[str, Any]:
    if str(event.get("type") or "") != "runner.tool_result":
        return event
    tool_name = str(event.get("tool_name") or "").lower()
    eligible = any(
        marker in tool_name
        for marker in (
            "bash_exec",
            "report",
            "gate",
            "paper_contract",
            "submission",
            "display",
            "medical",
            "figure",
            "artifact.",
        )
    )
    if not eligible:
        return event
    fingerprint = _tool_result_payload_fingerprint(event)
    key = _tool_result_delta_key(event)
    state = _delta_history_state(quest_root)
    entries = state.setdefault("entries", {})
    previous = entries.get(key) if isinstance(entries.get(key), dict) else {}
    repeat_count = int(previous.get("repeat_count") or 1) + 1 if previous.get("fingerprint") == fingerprint else 1
    entries[key] = {
        "fingerprint": fingerprint,
        "repeat_count": repeat_count,
        "last_seen_at": utc_now(),
        "last_run_id": run_id,
    }
    _write_delta_history_state(quest_root, state)
    if repeat_count <= 1:
        rendered = dict(event)
        rendered["fingerprint"] = fingerprint
        return rendered
    marker = {
        key_name: value
        for key_name, value in event.items()
        if key_name
        in {
            "event_id",
            "type",
            "quest_id",
            "run_id",
            "source",
            "skill_id",
            "tool_call_id",
            "tool_name",
            "status",
            "mcp_server",
            "mcp_tool",
            "metadata",
            "raw_event_type",
            "created_at",
        }
    }
    marker.update(
        {
            "delta_marker": True,
            "delta_kind": "unchanged_tool_result",
            "fingerprint": fingerprint,
            "repeat_count": repeat_count,
            "summary": "Repeated tool/report payload omitted because its fingerprint is unchanged.",
        }
    )
    return marker
