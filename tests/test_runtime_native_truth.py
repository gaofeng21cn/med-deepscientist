from __future__ import annotations

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
