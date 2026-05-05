from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any


def _require_text(field_name: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"quest runtime event {field_name} must be non-empty")
    return text


def _payload_text(payload: dict[str, Any], field_name: str) -> str:
    value = str(payload.get(field_name) or "").strip()
    if not value:
        raise ValueError(f"quest runtime event payload missing {field_name}")
    return value


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise TypeError("quest runtime event optional boolean field must be bool or None")


def _normalize_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("quest runtime event optional integer field must be int or None")
    return int(value)


_STATUS_SNAPSHOT_REQUIRED_KEYS = (
    "quest_status",
    "display_status",
    "active_run_id",
    "runtime_liveness_status",
    "worker_running",
    "stop_reason",
    "continuation_policy",
    "continuation_anchor",
    "continuation_reason",
    "pending_user_message_count",
    "interaction_action",
    "interaction_requires_user_input",
    "active_interaction_id",
    "last_transition_at",
)

_OUTER_LOOP_INPUT_REQUIRED_KEYS = _STATUS_SNAPSHOT_REQUIRED_KEYS

_SAFE_ARTIFACT_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _normalize_snapshot(
    payload: Any,
    *,
    field_name: str,
    required_keys: tuple[str, ...],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError(f"quest runtime event {field_name} must be a mapping")
    normalized = dict(payload)
    missing = [key for key in required_keys if key not in normalized]
    if missing:
        raise ValueError(f"quest runtime event {field_name} missing {', '.join(missing)}")
    normalized["quest_status"] = _normalize_optional_text(normalized.get("quest_status"))
    normalized["display_status"] = _normalize_optional_text(normalized.get("display_status"))
    normalized["active_run_id"] = _normalize_optional_text(normalized.get("active_run_id"))
    normalized["runtime_liveness_status"] = _normalize_optional_text(normalized.get("runtime_liveness_status"))
    normalized["worker_running"] = _normalize_optional_bool(normalized.get("worker_running"))
    normalized["stop_reason"] = _normalize_optional_text(normalized.get("stop_reason"))
    normalized["continuation_policy"] = _normalize_optional_text(normalized.get("continuation_policy"))
    normalized["continuation_anchor"] = _normalize_optional_text(normalized.get("continuation_anchor"))
    normalized["continuation_reason"] = _normalize_optional_text(normalized.get("continuation_reason"))
    normalized["pending_user_message_count"] = _normalize_optional_int(normalized.get("pending_user_message_count"))
    normalized["interaction_action"] = _normalize_optional_text(normalized.get("interaction_action"))
    normalized["interaction_requires_user_input"] = bool(normalized.get("interaction_requires_user_input"))
    normalized["active_interaction_id"] = _normalize_optional_text(normalized.get("active_interaction_id"))
    normalized["last_transition_at"] = _normalize_optional_text(normalized.get("last_transition_at"))
    return normalized


def _normalize_transition(payload: Any) -> dict[str, Any] | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise TypeError("quest runtime event transition must be a mapping or None")
    normalized = dict(payload)
    changed_fields = normalized.get("changed_fields")
    if changed_fields is None:
        normalized["changed_fields"] = []
    elif isinstance(changed_fields, list):
        normalized["changed_fields"] = [str(item) for item in changed_fields]
    else:
        raise TypeError("quest runtime event transition.changed_fields must be a list")
    for side in ("previous", "current"):
        if side in normalized and normalized[side] is not None:
            normalized[side] = _normalize_snapshot(
                normalized[side],
                field_name=f"transition.{side}",
                required_keys=_STATUS_SNAPSHOT_REQUIRED_KEYS,
            )
    return normalized


def _artifact_timestamp_slug(recorded_at: str) -> str:
    normalized = recorded_at.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    return datetime.fromisoformat(normalized).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _safe_artifact_id(value: str) -> str:
    normalized = _SAFE_ARTIFACT_RE.sub("-", value.strip()).strip("-")
    if not normalized:
        raise ValueError("quest runtime event event_kind must produce a non-empty artifact filename")
    return normalized


def runtime_event_report_root(quest_root: Path) -> Path:
    return Path(quest_root).expanduser().resolve() / "artifacts" / "reports" / "runtime_events"


def runtime_event_latest_path(quest_root: Path) -> Path:
    return runtime_event_report_root(quest_root) / "latest.json"


def runtime_event_record_path(*, quest_root: Path, record: "QuestRuntimeEvent") -> Path:
    return runtime_event_report_root(quest_root) / f"{_artifact_timestamp_slug(record.emitted_at)}_{_safe_artifact_id(record.event_kind)}.json"


@dataclass(frozen=True)
class QuestRuntimeEventRef:
    event_id: str
    artifact_path: str
    summary_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _require_text("event_id", self.event_id))
        object.__setattr__(self, "artifact_path", _require_text("artifact_path", self.artifact_path))
        object.__setattr__(self, "summary_ref", _require_text("summary_ref", self.summary_ref))

    def to_dict(self) -> dict[str, str]:
        return {
            "event_id": self.event_id,
            "artifact_path": self.artifact_path,
            "summary_ref": self.summary_ref,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "QuestRuntimeEventRef":
        if not isinstance(payload, dict):
            raise TypeError("quest runtime event ref payload must be a mapping")
        return cls(
            event_id=_payload_text(payload, "event_id"),
            artifact_path=_payload_text(payload, "artifact_path"),
            summary_ref=_payload_text(payload, "summary_ref"),
        )


@dataclass(frozen=True)
class QuestRuntimeEvent:
    schema_version: int
    event_id: str
    quest_id: str
    emitted_at: str
    event_source: str
    event_kind: str
    summary_ref: str
    status_snapshot: dict[str, Any]
    outer_loop_input: dict[str, Any]
    transition: dict[str, Any] | None = None
    artifact_path: str | None = None
    summary: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, int) or isinstance(self.schema_version, bool):
            raise TypeError("quest runtime event schema_version must be int")
        object.__setattr__(self, "event_id", _require_text("event_id", self.event_id))
        object.__setattr__(self, "quest_id", _require_text("quest_id", self.quest_id))
        object.__setattr__(self, "emitted_at", _require_text("emitted_at", self.emitted_at))
        object.__setattr__(self, "event_source", _require_text("event_source", self.event_source))
        object.__setattr__(self, "event_kind", _require_text("event_kind", self.event_kind))
        object.__setattr__(self, "summary_ref", _require_text("summary_ref", self.summary_ref))
        object.__setattr__(
            self,
            "status_snapshot",
            _normalize_snapshot(
                self.status_snapshot,
                field_name="status_snapshot",
                required_keys=_STATUS_SNAPSHOT_REQUIRED_KEYS,
            ),
        )
        object.__setattr__(
            self,
            "outer_loop_input",
            _normalize_snapshot(
                self.outer_loop_input,
                field_name="outer_loop_input",
                required_keys=_OUTER_LOOP_INPUT_REQUIRED_KEYS,
            ),
        )
        object.__setattr__(self, "transition", _normalize_transition(self.transition))
        if self.artifact_path is not None:
            object.__setattr__(self, "artifact_path", _require_text("artifact_path", self.artifact_path))
        if self.summary is not None:
            object.__setattr__(self, "summary", _require_text("summary", self.summary))

    def with_artifact_path(self, artifact_path: str) -> "QuestRuntimeEvent":
        return QuestRuntimeEvent(
            schema_version=self.schema_version,
            event_id=self.event_id,
            quest_id=self.quest_id,
            emitted_at=self.emitted_at,
            event_source=self.event_source,
            event_kind=self.event_kind,
            summary_ref=self.summary_ref,
            status_snapshot=self.status_snapshot,
            outer_loop_input=self.outer_loop_input,
            transition=self.transition,
            artifact_path=artifact_path,
            summary=self.summary,
        )

    def ref(self) -> QuestRuntimeEventRef:
        if self.artifact_path is None:
            raise ValueError("quest runtime event artifact_path must be set before building ref")
        return QuestRuntimeEventRef(
            event_id=self.event_id,
            artifact_path=self.artifact_path,
            summary_ref=self.summary_ref,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "quest_id": self.quest_id,
            "emitted_at": self.emitted_at,
            "event_source": self.event_source,
            "event_kind": self.event_kind,
            "summary_ref": self.summary_ref,
            "status_snapshot": dict(self.status_snapshot),
            "outer_loop_input": dict(self.outer_loop_input),
        }
        if self.transition is not None:
            payload["transition"] = dict(self.transition)
        if self.artifact_path is not None:
            payload["artifact_path"] = self.artifact_path
        if self.summary is not None:
            payload["summary"] = self.summary
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "QuestRuntimeEvent":
        if not isinstance(payload, dict):
            raise TypeError("quest runtime event payload must be a mapping")
        if "schema_version" not in payload:
            raise ValueError("quest runtime event payload missing schema_version")
        schema_version = payload.get("schema_version")
        if not isinstance(schema_version, int) or isinstance(schema_version, bool):
            raise TypeError("quest runtime event schema_version must be int")
        return cls(
            schema_version=schema_version,
            event_id=_payload_text(payload, "event_id"),
            quest_id=_payload_text(payload, "quest_id"),
            emitted_at=_payload_text(payload, "emitted_at"),
            event_source=_payload_text(payload, "event_source"),
            event_kind=_payload_text(payload, "event_kind"),
            summary_ref=_payload_text(payload, "summary_ref"),
            status_snapshot=payload.get("status_snapshot"),
            outer_loop_input=payload.get("outer_loop_input"),
            transition=payload.get("transition"),
            artifact_path=_normalize_optional_text(payload.get("artifact_path")),
            summary=_normalize_optional_text(payload.get("summary")),
        )
