from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from deepscientist.config import ConfigManager
from deepscientist.daemon.app import DaemonApp
from deepscientist.home import ensure_home_layout
from deepscientist.shared import read_json


def _latest_runtime_event(quest_root: Path) -> dict:
    payload = read_json(quest_root / "artifacts" / "reports" / "runtime_events" / "latest.json", {})
    assert isinstance(payload, dict) and payload
    return payload


def test_pause_control_writes_native_runtime_event_and_session_exposes_ref(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create("native truth pause quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])

    app.quest_service.mark_turn_started(quest_id, run_id="run-native-pause-001")
    payload = app.handlers.quest_control(quest_id, {"action": "pause", "source": "tui-ink"})

    event = _latest_runtime_event(quest_root)
    session = app.handlers.quest_session(quest_id)
    events = app.quest_service.events(quest_id)["events"]

    assert payload["snapshot"]["status"] == "paused"
    assert event["event_source"] == "quest_control"
    assert event["event_kind"] == "runtime_control_applied"
    assert event["status_snapshot"]["quest_status"] == "paused"
    assert event["status_snapshot"]["runtime_liveness_status"] == "none"
    assert event["transition"]["previous"]["quest_status"] == "running"
    assert event["transition"]["current"]["quest_status"] == "paused"
    assert session["runtime_event_ref"]["event_id"] == event["event_id"]
    assert session["runtime_event"]["event_id"] == event["event_id"]
    assert any(
        item.get("type") == "quest.runtime_event"
        and item.get("runtime_event_kind") == "runtime_control_applied"
        and (item.get("runtime_event_ref") or {}).get("event_id") == event["event_id"]
        for item in events
    )


def test_resume_control_mode_reconciliation_writes_native_runtime_event(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create(
        "native truth resume control-mode quest",
        startup_contract={"control_mode": "copilot"},
    )
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])

    app.quest_service.set_status(quest_id, "paused")
    app.quest_service.update_runtime_state(
        quest_root=quest_root,
        continuation_policy="auto",
        continuation_reason="external_progress:run-004",
    )

    payload = app.resume_quest(quest_id, source="auto:daemon-recovery")

    event = _latest_runtime_event(quest_root)
    session = app.handlers.quest_session(quest_id)

    assert payload["snapshot"]["continuation_policy"] == "wait_for_user_or_resume"
    assert event["event_source"] == "quest_resume"
    assert event["event_kind"] == "runtime_continuation_changed"
    assert event["status_snapshot"]["quest_status"] == "active"
    assert event["status_snapshot"]["continuation_policy"] == "wait_for_user_or_resume"
    assert "continuation_anchor" in event["status_snapshot"]
    assert event["status_snapshot"]["continuation_anchor"] is None
    assert event["status_snapshot"]["continuation_reason"] == "control_mode_copilot"
    assert session["runtime_event_ref"]["event_id"] == event["event_id"]
    assert session["runtime_event"]["event_id"] == event["event_id"]


def test_runtime_execution_gate_event_includes_continuation_anchor(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create("native truth execution gate anchor quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])

    app.quest_service.set_continuation_state(
        quest_root,
        policy="auto",
        anchor="decision",
        reason="gate_needs_specificity",
    )

    event = _latest_runtime_event(quest_root)

    assert event["event_kind"] == "runtime_continuation_changed"
    assert event["status_snapshot"]["continuation_anchor"] == "decision"
    assert event["outer_loop_input"]["continuation_anchor"] == "decision"


def test_waiting_for_user_transition_writes_native_runtime_event(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create("native truth waiting quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])

    app.quest_service.mark_turn_started(quest_id, run_id="run-native-wait-001")
    app.artifact_service.interact(
        quest_root,
        kind="decision_request",
        message="Choose the next path.",
        deliver_to_bound_conversations=False,
        include_recent_inbound_messages=False,
        options=[{"id": "go", "label": "Go"}],
    )

    event = _latest_runtime_event(quest_root)
    snapshot = app.quest_service.snapshot(quest_id)

    assert snapshot["status"] == "waiting_for_user"
    assert event["event_kind"] == "runtime_waiting_for_user"
    assert event["status_snapshot"]["quest_status"] == "waiting_for_user"
    assert event["status_snapshot"]["worker_running"] is True
    assert event["status_snapshot"]["runtime_liveness_status"] == "live"
    assert event["outer_loop_input"]["interaction_requires_user_input"] is True
    assert event["outer_loop_input"]["interaction_action"] == "reply_required"
    assert event["outer_loop_input"]["active_interaction_id"]


def test_mark_turn_started_resets_interaction_watchdog_state_for_new_run(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create("native truth watchdog reset quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])

    stale_at = "2026-03-15T10:51:08+00:00"
    app.quest_service.update_runtime_state(
        quest_root=quest_root,
        status="stopped",
        active_run_id=None,
        last_artifact_interact_at=stale_at,
        last_tool_activity_at=stale_at,
        last_tool_activity_name="artifact.interact",
        tool_calls_since_last_artifact_interact=37,
    )

    app.quest_service.mark_turn_started(quest_id, run_id="run-native-reset-001")

    runtime_state = read_json(quest_root / ".ds" / "runtime_state.json", {})
    watchdog = app.quest_service.artifact_interaction_watchdog_status(quest_root)

    assert runtime_state["last_artifact_interact_at"] is None
    assert runtime_state["last_tool_activity_at"] is None
    assert runtime_state["last_tool_activity_name"] is None
    assert runtime_state["tool_calls_since_last_artifact_interact"] == 0
    assert watchdog["stale_visibility_gap"] is False
    assert watchdog["inspection_due"] is False


def test_watchdog_uses_turn_start_age_when_first_activity_never_arrives(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create("native truth zero activity watchdog quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])

    app.quest_service.mark_turn_started(quest_id, run_id="run-native-zero-activity-001")
    stale_started_at = (datetime.now(UTC) - timedelta(minutes=31)).replace(microsecond=0).isoformat()
    app.quest_service.update_runtime_state(
        quest_root=quest_root,
        last_transition_at=stale_started_at,
    )

    watchdog = app.quest_service.artifact_interaction_watchdog_status(quest_root)

    assert watchdog["last_artifact_interact_at"] is None
    assert watchdog["last_tool_activity_at"] is None
    assert watchdog["active_execution_window"] is True
    assert watchdog["seconds_since_last_transition"] >= 30 * 60
    assert watchdog["no_progress_since_turn_start"] is True
    assert watchdog["stale_visibility_gap"] is True
    assert watchdog["inspection_due"] is True


def test_reconcile_runtime_state_writes_native_runtime_event(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create("native truth reconcile quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])

    app.quest_service.update_runtime_state(
        quest_root=quest_root,
        status="running",
        active_run_id="run-native-stale-001",
        worker_running=False,
    )

    reconciled = app.quest_service.reconcile_runtime_state()
    event = _latest_runtime_event(quest_root)

    assert any(item["quest_id"] == quest_id for item in reconciled)
    assert event["event_source"] == "quest_runtime_recovery"
    assert event["event_kind"] == "runtime_reconciled"
    assert event["status_snapshot"]["quest_status"] == "stopped"
    assert event["status_snapshot"]["runtime_liveness_status"] == "none"
    assert event["transition"]["previous"]["runtime_liveness_status"] == "stale"
    assert event["transition"]["current"]["runtime_liveness_status"] == "none"


def test_snapshot_marks_worker_running_without_active_run_id_as_invalid_liveness(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create("native truth invalid liveness quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])

    app.quest_service.update_runtime_state(
        quest_root=quest_root,
        status="running",
        active_run_id=None,
        worker_running=True,
    )

    snapshot = app.quest_service.snapshot(quest_id)
    event = _latest_runtime_event(quest_root)

    assert snapshot["active_run_id"] is None
    assert snapshot["worker_running"] is True
    assert snapshot["runtime_liveness_status"] == "invalid"
    assert event["status_snapshot"]["runtime_liveness_status"] == "invalid"


def test_turn_error_writes_native_runtime_event_with_error_display_status(temp_home: Path) -> None:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    app = DaemonApp(temp_home)
    quest = app.quest_service.create("native truth error quest")
    quest_id = quest["quest_id"]
    quest_root = Path(quest["quest_root"])

    app.quest_service.mark_turn_started(quest_id, run_id="run-native-error-001")
    app._record_turn_error(
        quest_id=quest_id,
        runner_name="codex",
        run_id="run-native-error-001",
        skill_id="decision",
        model="gpt-5.4",
        summary="Forced runner failure for native runtime truth coverage.",
    )

    event = _latest_runtime_event(quest_root)
    snapshot = app.quest_service.snapshot(quest_id)

    assert snapshot["status"] == "error"
    assert snapshot["runtime_status"] == "active"
    assert event["event_source"] == "runner_postprocess"
    assert event["event_kind"] == "runtime_turn_error"
    assert event["status_snapshot"]["quest_status"] == "active"
    assert event["status_snapshot"]["display_status"] == "error"
    assert event["status_snapshot"]["runtime_liveness_status"] == "none"
