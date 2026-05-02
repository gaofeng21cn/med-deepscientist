from __future__ import annotations

from typing import Any


def _require_dict(payload: object, *, name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError(f"{name} must be a dict")
    return dict(payload)


def _require_non_empty_string(payload: dict[str, Any], key: str, *, name: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"{name}.{key} must be a non-empty string")
    return value


def build_quest_runtime_audit_contract(
    *,
    active_run_id: str | None,
    worker_running: bool,
    worker_pending: bool,
    stop_requested: bool,
) -> dict[str, Any]:
    normalized_active_run_id = str(active_run_id or "").strip() or None
    if worker_running and normalized_active_run_id is None:
        status = "invalid"
    elif worker_running:
        status = "live"
    else:
        status = "none"
    return {
        "ok": True,
        "status": status,
        "source": "daemon_turn_worker",
        "active_run_id": normalized_active_run_id,
        "worker_running": bool(worker_running),
        "worker_pending": bool(worker_pending),
        "stop_requested": bool(stop_requested),
    }


def build_quest_session_contract(
    *,
    quest_id: str,
    snapshot: dict[str, Any],
    runtime_audit: dict[str, Any],
    acp_session: dict[str, Any],
) -> dict[str, Any]:
    resolved_quest_id = str(quest_id or "").strip()
    if not resolved_quest_id:
        raise ValueError("quest_id must be a non-empty string")
    resolved_snapshot = _require_dict(snapshot, name="snapshot")
    resolved_runtime_audit = _require_dict(runtime_audit, name="runtime_audit")
    resolved_acp_session = _require_dict(acp_session, name="acp_session")
    if str(resolved_snapshot.get("quest_id") or "").strip() != resolved_quest_id:
        raise ValueError("snapshot.quest_id must match quest_id")
    return {
        "ok": True,
        "quest_id": resolved_quest_id,
        "snapshot": resolved_snapshot,
        "runtime_audit": resolved_runtime_audit,
        "acp_session": resolved_acp_session,
    }


def build_quest_startup_context_contract(snapshot: dict[str, Any]) -> dict[str, Any]:
    resolved_snapshot = _require_dict(snapshot, name="snapshot")
    quest_id = _require_non_empty_string(resolved_snapshot, "quest_id", name="snapshot")
    return {
        "ok": True,
        "quest_id": quest_id,
        "snapshot": resolved_snapshot,
    }


def build_quest_control_contract(payload: dict[str, Any]) -> dict[str, Any]:
    resolved_payload = _require_dict(payload, name="payload")
    quest_id = _require_non_empty_string(resolved_payload, "quest_id", name="payload")
    action = _require_non_empty_string(resolved_payload, "action", name="payload")
    snapshot = _require_dict(resolved_payload.get("snapshot"), name="payload.snapshot")
    status = str(resolved_payload.get("status") or snapshot.get("status") or "").strip()
    if not status:
        raise ValueError("payload.status or payload.snapshot.status must be a non-empty string")
    contract = dict(resolved_payload)
    contract["quest_id"] = quest_id
    contract["action"] = action
    contract["status"] = status
    contract["snapshot"] = snapshot
    return contract


def build_artifact_completion_contract(payload: dict[str, Any]) -> dict[str, Any]:
    resolved_payload = _require_dict(payload, name="payload")
    snapshot = _require_dict(resolved_payload.get("snapshot"), name="payload.snapshot")
    status = _require_non_empty_string(resolved_payload, "status", name="payload")
    summary_refresh = _require_dict(resolved_payload.get("summary_refresh"), name="payload.summary_refresh")
    contract = dict(resolved_payload)
    contract["snapshot"] = snapshot
    contract["status"] = status
    contract["summary_refresh"] = summary_refresh
    return contract
