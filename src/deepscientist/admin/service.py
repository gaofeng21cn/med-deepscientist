from __future__ import annotations

from collections import Counter
import json
import os
import platform
import shutil
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..runtime_tools import RuntimeToolService
from ..shared import count_jsonl, iter_jsonl, read_jsonl_tail, utc_now, which

if TYPE_CHECKING:
    from ..daemon.app import DaemonApp


_INTERESTING_RUNTIME_STATUSES = {"running", "waiting_for_user", "paused", "error"}

_CHART_CATALOG: dict[str, dict[str, str]] = {
    "quest_status_counts": {
        "chart_id": "quest_status_counts",
        "title": "Quest status counts",
        "description": "Current runtime status distribution across visible quests.",
        "kind": "bar",
    },
    "connector_status_counts": {
        "chart_id": "connector_status_counts",
        "title": "Connector status counts",
        "description": "Connector availability grouped by runtime connection state.",
        "kind": "bar",
    },
    "bash_session_status_counts": {
        "chart_id": "bash_session_status_counts",
        "title": "Bash session status counts",
        "description": "Current bash_exec terminal and exec session status distribution.",
        "kind": "bar",
    },
    "failure_counts": {
        "chart_id": "failure_counts",
        "title": "Failure counts",
        "description": "Recent failures grouped by severity.",
        "kind": "bar",
    },
}


def _normalized_text(value: object) -> str:
    return str(value or "").strip()


def _matches_query(query: str | None, *parts: object) -> bool:
    normalized_query = _normalized_text(query).lower()
    if not normalized_query:
        return True
    haystack = " ".join(_normalized_text(part) for part in parts if _normalized_text(part)).lower()
    return normalized_query in haystack


def _path_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "filename": str(path),
            "exists": False,
            "size_bytes": 0,
            "updated_at": None,
        }
    stat = path.stat()
    return {
        "filename": str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "updated_at": _isoformat_mtime(stat.st_mtime),
        "mtime": stat.st_mtime,
    }


def _path_updated_at(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return _isoformat_mtime(path.stat().st_mtime)
    except OSError:
        return None


def _isoformat_mtime(timestamp: float) -> str | None:
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, UTC).replace(microsecond=0).isoformat()


def _coerce_limit(value: object, default: int, *, maximum: int = 500) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(resolved, maximum))


def _extract_summary(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("summary", "message", "failure_summary", "reason", "status_line"):
        text = _normalized_text(payload.get(key))
        if text:
            return text
    return ""


class ReadOnlySystemService:
    def __init__(self, app: "DaemonApp") -> None:
        self.app = app

    def _quest_items(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.app.quest_service.list_quests()]

    def _quest_status_counts(self, quests: list[dict[str, Any]]) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for item in quests:
            status = _normalized_text(item.get("display_status") or item.get("status") or item.get("runtime_status")) or "unknown"
            counts[status] += 1
        return dict(sorted(counts.items()))

    def _all_bash_sessions(self, *, limit_per_quest: int = 50) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        for quest in self._quest_items():
            quest_id = _normalized_text(quest.get("quest_id"))
            if not quest_id:
                continue
            quest_root = self.app.quest_service._quest_root(quest_id)
            quest_title = _normalized_text(quest.get("title")) or quest_id
            for session in self.app.bash_exec_service.list_sessions(quest_root, limit=limit_per_quest):
                enriched = dict(session)
                enriched["quest_id"] = quest_id
                enriched["quest_title"] = quest_title
                sessions.append(enriched)
        sessions.sort(
            key=lambda item: (
                _normalized_text(item.get("updated_at")),
                _normalized_text(item.get("started_at")),
                _normalized_text(item.get("bash_id")),
            ),
            reverse=True,
        )
        return sessions

    def _runtime_session_items(self, quests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for quest in quests:
            quest_id = _normalized_text(quest.get("quest_id"))
            if not quest_id:
                continue
            audit = self.app.quest_runtime_audit(quest_id, snapshot=quest)
            item = {
                "quest_id": quest_id,
                "title": quest.get("title"),
                "status": quest.get("display_status") or quest.get("status") or quest.get("runtime_status"),
                "runtime_status": quest.get("runtime_status"),
                "active_run_id": audit.get("active_run_id"),
                "worker_running": audit.get("worker_running"),
                "worker_pending": audit.get("worker_pending"),
                "stop_requested": audit.get("stop_requested"),
                "updated_at": quest.get("updated_at"),
                "last_tool_activity_at": quest.get("last_tool_activity_at"),
                "last_tool_activity_name": quest.get("last_tool_activity_name"),
                "pending_user_message_count": int(quest.get("pending_user_message_count") or 0),
            }
            is_interesting = bool(
                item["active_run_id"]
                or item["worker_running"]
                or item["worker_pending"]
                or int(item["pending_user_message_count"]) > 0
                or _normalized_text(item.get("status")).lower() in _INTERESTING_RUNTIME_STATUSES
            )
            if is_interesting:
                items.append(item)
        items.sort(key=lambda item: _normalized_text(item.get("updated_at")), reverse=True)
        return items

    def _connector_session_items(self, quests_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for session in self.app.sessions.snapshot():
            quest_id = _normalized_text(session.get("quest_id"))
            quest = quests_by_id.get(quest_id, {})
            items.append(
                {
                    "quest_id": quest_id,
                    "title": quest.get("title"),
                    "status": quest.get("display_status") or quest.get("status") or quest.get("runtime_status"),
                    "bound_sources": list(session.get("bound_sources") or []),
                    "updated_at": session.get("updated_at"),
                }
            )
        items.sort(key=lambda item: _normalized_text(item.get("updated_at")), reverse=True)
        return items

    def _log_source_items(self) -> list[dict[str, Any]]:
        quests = self._quest_items()
        items: list[dict[str, Any]] = []

        daemon_path = self.app.home / "logs" / "daemon.jsonl"
        daemon_meta = _path_metadata(daemon_path)
        items.append(
            {
                "source_id": "daemon",
                "source_type": "daemon",
                "label": "Daemon log",
                **daemon_meta,
            }
        )

        for quest in quests:
            quest_id = _normalized_text(quest.get("quest_id"))
            if not quest_id:
                continue
            quest_root = self.app.quest_service._quest_root(quest_id)
            event_path = quest_root / ".ds" / "events.jsonl"
            event_meta = _path_metadata(event_path)
            items.append(
                {
                    "source_id": f"quest-events:{quest_id}",
                    "source_type": "quest_events",
                    "label": f"Quest {quest_id} events",
                    "quest_id": quest_id,
                    **event_meta,
                }
            )
            for session in self.app.bash_exec_service.list_sessions(quest_root, limit=50):
                bash_id = _normalized_text(session.get("bash_id"))
                if not bash_id:
                    continue
                log_path = self.app.bash_exec_service.log_path(quest_root, bash_id)
                session_meta = _path_metadata(log_path)
                items.append(
                    {
                        "source_id": f"bash:{quest_id}:{bash_id}",
                        "source_type": "bash",
                        "label": f"Quest {quest_id} bash {bash_id}",
                        "quest_id": quest_id,
                        "bash_id": bash_id,
                        **session_meta,
                    }
                )
        items.sort(
            key=lambda item: (
                bool(item.get("exists")),
                int(item.get("size_bytes") or 0),
                _normalized_text(item.get("source_id")),
            ),
            reverse=True,
        )
        return items

    def _resolve_log_source(self, source_id: str) -> tuple[str, Path]:
        normalized = _normalized_text(source_id)
        if normalized == "daemon":
            return "daemon", self.app.home / "logs" / "daemon.jsonl"
        if normalized.startswith("quest-events:"):
            quest_id = normalized.split(":", 1)[1]
            return "quest_events", self.app.quest_service._quest_root(quest_id) / ".ds" / "events.jsonl"
        if normalized.startswith("bash:"):
            _prefix, quest_id, bash_id = normalized.split(":", 2)
            quest_root = self.app.quest_service._quest_root(quest_id)
            return "bash", self.app.bash_exec_service.log_path(quest_root, bash_id)
        raise KeyError(f"Unknown log source `{normalized}`.")

    @staticmethod
    def _format_jsonl_lines(kind: str, entries: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        for item in entries:
            if kind == "bash":
                timestamp = _normalized_text(item.get("timestamp"))
                stream = _normalized_text(item.get("stream")) or "stdout"
                line = _normalized_text(item.get("line"))
                lines.append(" | ".join(part for part in (timestamp, stream, line) if part))
                continue
            timestamp = _normalized_text(item.get("timestamp") or item.get("created_at"))
            if kind == "daemon":
                payload = dict(item.get("payload") or {}) if isinstance(item.get("payload"), dict) else {}
                level = _normalized_text(item.get("level")).upper() or "INFO"
                event = _normalized_text(item.get("event")) or "event"
                summary = _extract_summary(payload)
                quest_id = _normalized_text(payload.get("quest_id"))
                line = " | ".join(part for part in (timestamp, level, event, f"quest={quest_id}" if quest_id else "", summary) if part)
                lines.append(line or json.dumps(item, ensure_ascii=False))
                continue
            event_type = _normalized_text(item.get("type")) or "event"
            summary = _extract_summary(item)
            tool_name = _normalized_text(item.get("tool_name"))
            line = " | ".join(part for part in (timestamp, event_type, tool_name, summary) if part)
            lines.append(line or json.dumps(item, ensure_ascii=False))
        return lines

    def _daemon_failure_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for index, entry in enumerate(iter_jsonl(self.app.home / "logs" / "daemon.jsonl")):
            level = _normalized_text(entry.get("level")).lower()
            event = _normalized_text(entry.get("event")).lower()
            payload = dict(entry.get("payload") or {}) if isinstance(entry.get("payload"), dict) else {}
            if level not in {"error", "warning"} and "error" not in event and "fail" not in event:
                continue
            summary = _extract_summary(payload) or event
            items.append(
                {
                    "id": f"daemon:{index}",
                    "severity": level or "error",
                    "source": "daemon",
                    "event_type": entry.get("event"),
                    "quest_id": payload.get("quest_id"),
                    "run_id": payload.get("run_id"),
                    "summary": summary,
                    "details": payload,
                    "created_at": entry.get("timestamp"),
                }
            )
        return items

    def _quest_failure_items(self, quests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for quest in quests:
            status = _normalized_text(quest.get("display_status") or quest.get("status") or quest.get("runtime_status")).lower()
            if status != "error":
                continue
            quest_id = _normalized_text(quest.get("quest_id"))
            summary = (
                _normalized_text(quest.get("last_recovery_summary"))
                or _normalized_text((quest.get("summary") or {}).get("status_line") if isinstance(quest.get("summary"), dict) else "")
                or _normalized_text(quest.get("stop_reason"))
                or "Quest runtime is in error state."
            )
            items.append(
                {
                    "id": f"quest:{quest_id}",
                    "severity": "error",
                    "source": "quest_runtime",
                    "event_type": "quest_error_state",
                    "quest_id": quest_id,
                    "run_id": quest.get("active_run_id"),
                    "summary": summary,
                    "details": {
                        "status": quest.get("status"),
                        "runtime_status": quest.get("runtime_status"),
                        "stop_reason": quest.get("stop_reason"),
                    },
                    "created_at": quest.get("updated_at"),
                }
            )
        return items

    def _bash_failure_items(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for session in sessions:
            status = _normalized_text(session.get("status")).lower()
            exit_code = session.get("exit_code")
            if status not in {"failed", "terminated"} and not (isinstance(exit_code, int) and exit_code != 0):
                continue
            bash_id = _normalized_text(session.get("bash_id"))
            quest_id = _normalized_text(session.get("quest_id"))
            items.append(
                {
                    "id": f"bash:{quest_id}:{bash_id}",
                    "severity": "warning" if status == "terminated" else "error",
                    "source": "bash_exec",
                    "event_type": "bash_session_failure",
                    "quest_id": quest_id,
                    "run_id": None,
                    "summary": f"{bash_id} `{_normalized_text(session.get('command'))}` ended with status `{status}`.",
                    "details": {
                        "status": status,
                        "exit_code": exit_code,
                        "command": session.get("command"),
                    },
                    "created_at": session.get("updated_at") or session.get("finished_at") or session.get("started_at"),
                }
            )
        return items

    def quests(self, *, status: str | None = None, query: str | None = None, limit: int = 200) -> dict[str, Any]:
        items = self._quest_items()
        if status:
            normalized_status = _normalized_text(status).lower()
            items = [
                item
                for item in items
                if _normalized_text(item.get("display_status") or item.get("status") or item.get("runtime_status")).lower()
                == normalized_status
            ]
        if query:
            items = [
                item
                for item in items
                if _matches_query(
                    query,
                    item.get("quest_id"),
                    item.get("title"),
                    item.get("status"),
                    (item.get("summary") or {}).get("status_line") if isinstance(item.get("summary"), dict) else "",
                )
            ]
        total = len(items)
        limited_items = items[: _coerce_limit(limit, 200)]
        return {
            "ok": True,
            "items": limited_items,
            "total": total,
            "status_counts": self._quest_status_counts(items),
            "updated_at": utc_now(),
        }

    def quest_summary(self, quest_id: str) -> dict[str, Any]:
        snapshot = self.app._compact_snapshot_with_reconciled_turn_state(quest_id)
        return {
            "ok": True,
            "quest": snapshot,
            "runtime_audit": self.app.quest_runtime_audit(quest_id, snapshot=snapshot),
            "bash_sessions": self.app.bash_exec_service.list_sessions(self.app.quest_service._quest_root(quest_id), limit=10),
            "updated_at": utc_now(),
        }

    def runtime_sessions(self, *, limit: int = 200) -> dict[str, Any]:
        quests = self._quest_items()
        quest_sessions = self._runtime_session_items(quests)
        quests_by_id = {str(item.get("quest_id")): item for item in quests if str(item.get("quest_id") or "").strip()}
        connector_sessions = self._connector_session_items(quests_by_id)
        bash_sessions = [
            item
            for item in self._all_bash_sessions(limit_per_quest=50)
            if _normalized_text(item.get("status")).lower() in {"running", "terminating"}
        ]
        limited_quest_sessions = quest_sessions[: _coerce_limit(limit, 200)]
        limited_connector_sessions = connector_sessions[: _coerce_limit(limit, 200)]
        limited_bash_sessions = bash_sessions[: _coerce_limit(limit, 200)]
        return {
            "ok": True,
            "quest_sessions": limited_quest_sessions,
            "connector_sessions": limited_connector_sessions,
            "bash_sessions": limited_bash_sessions,
            "totals": {
                "quest_sessions": len(quest_sessions),
                "connector_sessions": len(connector_sessions),
                "bash_sessions": len(bash_sessions),
                "bash_sessions_running": sum(
                    1 for item in bash_sessions if _normalized_text(item.get("status")).lower() == "running"
                ),
            },
            "updated_at": utc_now(),
        }

    def log_sources(self) -> dict[str, Any]:
        items = self._log_source_items()
        return {
            "ok": True,
            "items": items,
            "total": len(items),
            "updated_at": utc_now(),
        }

    def log_tail(self, source_id: str, *, limit: int = 200) -> dict[str, Any]:
        kind, path = self._resolve_log_source(source_id)
        normalized_limit = _coerce_limit(limit, 200)
        if kind == "bash":
            total = count_jsonl(path)
            entries = read_jsonl_tail(path, normalized_limit)
            lines = self._format_jsonl_lines("bash", entries)
        else:
            total = count_jsonl(path)
            entries = read_jsonl_tail(path, normalized_limit)
            lines = self._format_jsonl_lines("daemon" if kind == "daemon" else "quest_events", entries)
        return {
            "ok": True,
            "source_id": source_id,
            "filename": str(path),
            "lines": lines,
            "truncated": total > normalized_limit,
            "updated_at": _path_updated_at(path),
        }

    def failures(self, *, limit: int = 100, severity: str | None = None, query: str | None = None) -> dict[str, Any]:
        quests = self._quest_items()
        items = [
            *self._quest_failure_items(quests),
            *self._daemon_failure_items(),
            *self._bash_failure_items(self._all_bash_sessions(limit_per_quest=50)),
        ]
        if severity:
            normalized_severity = _normalized_text(severity).lower()
            items = [item for item in items if _normalized_text(item.get("severity")).lower() == normalized_severity]
        if query:
            items = [
                item
                for item in items
                if _matches_query(query, item.get("summary"), item.get("source"), item.get("quest_id"), item.get("event_type"))
            ]
        items.sort(key=lambda item: _normalized_text(item.get("created_at")), reverse=True)
        total = len(items)
        return {
            "ok": True,
            "items": items[: _coerce_limit(limit, 100)],
            "total": total,
            "updated_at": utc_now(),
        }

    def runtime_tools(self) -> dict[str, Any]:
        runtime_service = RuntimeToolService(self.app.home)
        items: list[dict[str, Any]] = []

        for name, payload in runtime_service.all_statuses().items():
            summary = _extract_summary(payload)
            items.append(
                {
                    "tool_name": name,
                    "kind": "managed",
                    "available": bool(payload.get("ok") or payload.get("installed")),
                    "path": (
                        ((payload.get("binaries") or {}).get("pdflatex") or {}).get("path")
                        if isinstance(payload.get("binaries"), dict)
                        else None
                    ),
                    "source": (
                        ((payload.get("binaries") or {}).get("pdflatex") or {}).get("source")
                        if isinstance(payload.get("binaries"), dict)
                        else None
                    ),
                    "summary": summary,
                    "details": payload,
                }
            )

        binary_entries = [
            ("codex", which("codex")),
            ("uv", which("uv")),
            ("git", which("git")),
            ("node", which("node")),
            ("npm", which("npm")),
            ("bash", which("bash")),
            ("python", sys.executable),
        ]
        for tool_name, path in binary_entries:
            items.append(
                {
                    "tool_name": tool_name,
                    "kind": "binary",
                    "available": bool(path),
                    "path": path,
                    "source": "path" if path else None,
                    "summary": f"`{tool_name}` is {'available' if path else 'missing'} in the local runtime.",
                    "details": None,
                }
            )

        items.sort(key=lambda item: (item.get("available") is True, _normalized_text(item.get("tool_name"))), reverse=True)
        return {
            "ok": True,
            "items": items,
            "total": len(items),
            "available_count": sum(1 for item in items if item.get("available")),
            "updated_at": utc_now(),
        }

    def hardware(self) -> dict[str, Any]:
        memory_total_bytes: int | None = None
        if hasattr(os, "sysconf"):
            try:
                memory_total_bytes = int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))
            except (ValueError, OSError, TypeError):
                memory_total_bytes = None

        load_average = None
        if hasattr(os, "getloadavg"):
            try:
                one_minute, five_minutes, fifteen_minutes = os.getloadavg()
                load_average = {
                    "1m": round(one_minute, 3),
                    "5m": round(five_minutes, 3),
                    "15m": round(fifteen_minutes, 3),
                }
            except OSError:
                load_average = None

        home_disk = shutil.disk_usage(self.app.home)
        repo_disk = shutil.disk_usage(self.app.repo_root)
        return {
            "ok": True,
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": socket.gethostname(),
            "cpu_count": int(os.cpu_count() or 0),
            "memory_total_bytes": memory_total_bytes,
            "load_average": load_average,
            "disk": {
                "home": {
                    "path": str(self.app.home.resolve()),
                    "total_bytes": home_disk.total,
                    "used_bytes": home_disk.used,
                    "free_bytes": home_disk.free,
                },
                "repo": {
                    "path": str(self.app.repo_root.resolve()),
                    "total_bytes": repo_disk.total,
                    "used_bytes": repo_disk.used,
                    "free_bytes": repo_disk.free,
                },
            },
            "home_path": str(self.app.home.resolve()),
            "repo_root": str(self.app.repo_root.resolve()),
            "runtime_tools_root": str((self.app.home / "runtime" / "tools").resolve()),
            "daemon_pid": os.getpid(),
            "updated_at": utc_now(),
        }

    def chart_catalog(self) -> dict[str, Any]:
        items = [dict(item) for item in _CHART_CATALOG.values()]
        return {
            "ok": True,
            "items": items,
            "total": len(items),
        }

    def chart_query(self, chart_id: str) -> dict[str, Any]:
        normalized_chart_id = _normalized_text(chart_id)
        chart = _CHART_CATALOG.get(normalized_chart_id)
        if chart is None:
            raise KeyError(f"Unknown chart `{normalized_chart_id}`.")

        if normalized_chart_id == "quest_status_counts":
            counts = self._quest_status_counts(self._quest_items())
        elif normalized_chart_id == "connector_status_counts":
            counts: Counter[str] = Counter()
            for item in self.app.list_connector_statuses():
                label = _normalized_text(item.get("connection_state")) or ("enabled" if item.get("enabled") else "disabled")
                counts[label] += 1
            counts = Counter(dict(sorted(counts.items())))
        elif normalized_chart_id == "bash_session_status_counts":
            counts = Counter(_normalized_text(item.get("status")) or "unknown" for item in self._all_bash_sessions(limit_per_quest=50))
            counts = Counter(dict(sorted(counts.items())))
        else:
            failures = self.failures(limit=500)
            counts = Counter(_normalized_text(item.get("severity")) or "error" for item in failures["items"])
            counts = Counter(dict(sorted(counts.items())))

        series = [{"label": label, "value": value} for label, value in counts.items()]
        return {
            "ok": True,
            "chart_id": normalized_chart_id,
            "title": chart["title"],
            "description": chart["description"],
            "kind": chart["kind"],
            "series": series,
            "updated_at": utc_now(),
        }

    def stats_summary(self) -> dict[str, Any]:
        quests = self._quest_items()
        quest_status_counts = self._quest_status_counts(quests)
        connector_counts: Counter[str] = Counter()
        for item in self.app.list_connector_statuses():
            label = _normalized_text(item.get("connection_state")) or ("enabled" if item.get("enabled") else "disabled")
            connector_counts[label] += 1
        runtime_sessions = self.runtime_sessions(limit=500)
        failures = self.failures(limit=500)
        runtime_tools = self.runtime_tools()
        return {
            "ok": True,
            "quest_status_counts": quest_status_counts,
            "connector_status_counts": dict(sorted(connector_counts.items())),
            "runtime_session_counts": runtime_sessions["totals"],
            "failure_counts": dict(sorted(Counter(_normalized_text(item.get("severity")) or "error" for item in failures["items"]).items())),
            "runtime_tools_available": runtime_tools["available_count"],
            "updated_at": utc_now(),
        }

    def overview(self) -> dict[str, Any]:
        quests = self._quest_items()
        quest_status_counts = self._quest_status_counts(quests)
        runtime_sessions = self.runtime_sessions(limit=500)
        log_sources = self.log_sources()
        failures = self.failures(limit=500)
        runtime_tools = self.runtime_tools()
        return {
            "ok": True,
            "daemon": {
                "daemon_id": self.app.daemon_id,
                "managed_by": self.app.daemon_managed_by,
                "home": str(self.app.home.resolve()),
                "repo_root": str(self.app.repo_root.resolve()),
                "pid": os.getpid(),
                "serve_host": self.app._serve_host,
                "serve_port": self.app._serve_port,
            },
            "counts": {
                "quests_total": len(quests),
                "quests_running": int(quest_status_counts.get("running") or 0),
                "quests_waiting": int(quest_status_counts.get("waiting_for_user") or 0),
                "quests_error": int(quest_status_counts.get("error") or 0),
                "connector_sessions": runtime_sessions["totals"]["connector_sessions"],
                "bash_sessions_running": runtime_sessions["totals"]["bash_sessions_running"],
                "failures_total": failures["total"],
                "log_sources": log_sources["total"],
                "runtime_tools_available": runtime_tools["available_count"],
            },
            "quest_status_counts": quest_status_counts,
            "connectors": self.app.connector_availability_summary(),
            "updated_at": utc_now(),
        }

    def search(self, query: str, *, scope: str | None = None, limit: int = 50) -> dict[str, Any]:
        normalized_scope = _normalized_text(scope).lower() or "all"
        normalized_query = _normalized_text(query)
        if not normalized_query:
            return {"ok": True, "items": [], "total": 0, "query": normalized_query, "scope": normalized_scope}

        items: list[dict[str, Any]] = []
        if normalized_scope in {"all", "quests"}:
            for quest in self._quest_items():
                if not _matches_query(
                    normalized_query,
                    quest.get("quest_id"),
                    quest.get("title"),
                    quest.get("status"),
                    (quest.get("summary") or {}).get("status_line") if isinstance(quest.get("summary"), dict) else "",
                ):
                    continue
                items.append(
                    {
                        "result_type": "quest",
                        "result_id": quest.get("quest_id"),
                        "label": quest.get("title") or quest.get("quest_id"),
                        "description": (quest.get("summary") or {}).get("status_line") if isinstance(quest.get("summary"), dict) else None,
                        "metadata": {
                            "quest_id": quest.get("quest_id"),
                            "status": quest.get("status"),
                        },
                    }
                )
        if normalized_scope in {"all", "failures"}:
            for item in self.failures(limit=200)["items"]:
                if not _matches_query(normalized_query, item.get("summary"), item.get("source"), item.get("quest_id")):
                    continue
                items.append(
                    {
                        "result_type": "failure",
                        "result_id": item.get("id"),
                        "label": item.get("summary"),
                        "description": item.get("source"),
                        "metadata": {
                            "quest_id": item.get("quest_id"),
                            "severity": item.get("severity"),
                        },
                    }
                )
        if normalized_scope in {"all", "logs"}:
            for source in self.log_sources()["items"]:
                matched_lines: list[str] = []
                metadata_match = _matches_query(normalized_query, source.get("source_id"), source.get("label"), source.get("filename"))
                if not metadata_match:
                    try:
                        tail_payload = self.log_tail(str(source.get("source_id") or ""), limit=25)
                    except KeyError:
                        tail_payload = {"lines": []}
                    matched_lines = [
                        line
                        for line in tail_payload.get("lines", [])
                        if _matches_query(normalized_query, line)
                    ][:3]
                    if not matched_lines:
                        continue
                items.append(
                    {
                        "result_type": "log_source",
                        "result_id": source.get("source_id"),
                        "label": source.get("label"),
                        "description": matched_lines[0] if matched_lines else source.get("filename"),
                        "metadata": {
                            "source_type": source.get("source_type"),
                            "exists": source.get("exists"),
                            "filename": source.get("filename"),
                            "matched_lines": matched_lines,
                        },
                    }
                )
        if normalized_scope in {"all", "runtime_tools"}:
            for tool in self.runtime_tools()["items"]:
                if not _matches_query(normalized_query, tool.get("tool_name"), tool.get("summary"), tool.get("path")):
                    continue
                items.append(
                    {
                        "result_type": "runtime_tool",
                        "result_id": tool.get("tool_name"),
                        "label": tool.get("tool_name"),
                        "description": tool.get("summary"),
                        "metadata": {
                            "available": tool.get("available"),
                            "kind": tool.get("kind"),
                        },
                    }
                )
        if normalized_scope in {"all", "charts"}:
            for chart in _CHART_CATALOG.values():
                if not _matches_query(normalized_query, chart.get("chart_id"), chart.get("title"), chart.get("description")):
                    continue
                items.append(
                    {
                        "result_type": "chart",
                        "result_id": chart.get("chart_id"),
                        "label": chart.get("title"),
                        "description": chart.get("description"),
                        "metadata": {
                            "kind": chart.get("kind"),
                        },
                    }
                )

        priority = {"quest": 0, "failure": 1, "log_source": 2, "runtime_tool": 3, "chart": 4}
        items.sort(key=lambda item: (priority.get(str(item.get("result_type")), 99), _normalized_text(item.get("label"))))
        total = len(items)
        return {
            "ok": True,
            "items": items[: _coerce_limit(limit, 50)],
            "total": total,
            "query": normalized_query,
            "scope": normalized_scope,
        }
