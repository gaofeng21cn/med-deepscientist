from __future__ import annotations

import os
from pathlib import Path
import threading

from deepscientist.config import ConfigManager
from deepscientist.daemon.app import DaemonApp
from deepscientist.home import ensure_home_layout
from deepscientist.shared import append_jsonl, ensure_dir, utc_now, write_json


def _bootstrap_app(temp_home: Path) -> DaemonApp:
    ensure_home_layout(temp_home)
    ConfigManager(temp_home).ensure_files()
    return DaemonApp(temp_home)


def _seed_bash_session(app: DaemonApp, quest_id: str, *, bash_id: str = "bash-visibility-001") -> str:
    quest_root = app.quest_service._quest_root(quest_id)
    service = app.bash_exec_service
    session_dir = service.session_dir(quest_root, bash_id)
    ensure_dir(session_dir)
    timestamp = utc_now()
    write_json(
        service.meta_path(quest_root, bash_id),
        {
            "id": bash_id,
            "bash_id": bash_id,
            "quest_id": quest_id,
            "project_id": quest_id,
            "session_id": f"quest:{quest_id}:bash-exec",
            "chat_session_id": f"quest:{quest_id}:bash-exec",
            "task_id": bash_id,
            "cli_server_id": "deepscientist-local",
            "agent_id": "user",
            "agent_instance_id": None,
            "started_by_user_id": "user:pytest",
            "stopped_by_user_id": None,
            "label": "visibility terminal",
            "command": "uv run pytest -q",
            "launch_argv": ["bash", "-lc", "uv run pytest -q"],
            "workdir": "",
            "cwd": str(quest_root),
            "kind": "exec",
            "source": {"surface": "pytest", "conversation_id": None},
            "log_path": service._session_log_relative_path(quest_root, bash_id),
            "mode": "detach",
            "status": "running",
            "exit_code": None,
            "stop_reason": None,
            "last_progress": None,
            "last_output_at": timestamp,
            "last_output_seq": 2,
            "started_at": timestamp,
            "finished_at": None,
            "updated_at": timestamp,
            "latest_seq": 2,
            "timeout_seconds": None,
            "env_keys": [],
            "quest_root": str(quest_root),
            "monitor_pid": os.getpid(),
            "process_pid": os.getpid(),
            "process_group_id": None,
            "last_input_at": timestamp,
            "last_prompt_at": timestamp,
            "last_command": "uv run pytest -q",
            "history_count": 1,
        },
    )
    append_jsonl(
        service.log_path(quest_root, bash_id),
        {
            "seq": 1,
            "stream": "stdout",
            "line": "running focused visibility checks",
            "timestamp": timestamp,
        },
    )
    append_jsonl(
        service.log_path(quest_root, bash_id),
        {
            "seq": 2,
            "stream": "stdout",
            "line": "visibility session still active",
            "timestamp": timestamp,
        },
    )
    service.terminal_log_path(quest_root, bash_id).write_text(
        "running focused visibility checks\nvisibility session still active\n",
        encoding="utf-8",
    )
    write_json(
        service.summary_path(quest_root),
        {
            "session_count": 1,
            "running_count": 1,
            "latest_session": {
                "bash_id": bash_id,
                "command": "uv run pytest -q",
                "kind": "exec",
                "status": "running",
                "updated_at": timestamp,
            },
            "updated_at": timestamp,
        },
    )
    return bash_id


def _seed_live_turn_worker(app: DaemonApp, quest_id: str) -> tuple[threading.Event, threading.Thread]:
    release = threading.Event()
    worker = threading.Thread(target=lambda: release.wait(timeout=5.0), daemon=True)
    worker.start()
    with app._turn_lock:
        app._turn_state[quest_id] = {
            "running": True,
            "pending": False,
            "worker": worker,
            "stop_requested": False,
        }
    return release, worker


def test_system_overview_quests_and_stats_expose_read_only_visibility(temp_home: Path) -> None:
    app = _bootstrap_app(temp_home)

    running = app.quest_service.create("observe running runtime", title="System visibility running quest")
    failed = app.quest_service.create("observe failed runtime", title="System visibility failed quest")
    running_id = running["quest_id"]
    failed_id = failed["quest_id"]

    app.quest_service.update_runtime_state(
        quest_root=app.quest_service._quest_root(running_id),
        status="running",
        display_status="running",
        active_run_id="run-main-001",
        worker_running=True,
        last_tool_activity_at=utc_now(),
        last_tool_activity_name="search_query",
    )
    app.quest_service.update_runtime_state(
        quest_root=app.quest_service._quest_root(failed_id),
        status="error",
        display_status="error",
        stop_reason="runner_error",
        event_source="pytest",
        event_kind="runtime_turn_error",
        event_summary="Runner failed while loading the model.",
    )

    app.sessions.bind(running_id, "web-react")
    _seed_bash_session(app, running_id)
    release, worker = _seed_live_turn_worker(app, running_id)
    app.logger.log(
        "error",
        "runner.turn_error",
        quest_id=failed_id,
        run_id="run-main-002",
        summary="Model unavailable for visibility slice.",
        diagnosis_code="runner_model_unavailable",
    )
    try:
        overview = app.handlers.system_overview()

        assert overview["ok"] is True
        assert overview["counts"]["quests_total"] == 2
        assert overview["counts"]["quests_running"] == 1
        assert overview["counts"]["quests_error"] == 1
        assert overview["counts"]["connector_sessions"] == 1
        assert overview["counts"]["bash_sessions_running"] == 1

        quests = app.handlers.system_quests("/api/system/quests")

        assert quests["total"] == 2
        assert quests["status_counts"]["running"] == 1
        assert quests["status_counts"]["error"] == 1
        assert {item["quest_id"] for item in quests["items"]} == {running_id, failed_id}

        detail = app.handlers.system_quest_summary(running_id)

        assert detail["ok"] is True
        assert detail["quest"]["quest_id"] == running_id
        assert detail["runtime_audit"]["active_run_id"] == "run-main-001"
        assert detail["runtime_audit"]["worker_running"] is True

        stats = app.handlers.system_stats_summary()

        assert stats["quest_status_counts"]["running"] == 1
        assert stats["quest_status_counts"]["error"] == 1
        assert stats["runtime_session_counts"]["connector_sessions"] == 1
        assert stats["runtime_session_counts"]["bash_sessions_running"] == 1
    finally:
        release.set()
        worker.join(timeout=1.0)


def test_system_runtime_sessions_logs_failures_and_search_cover_operator_visibility(temp_home: Path) -> None:
    app = _bootstrap_app(temp_home)

    quest = app.quest_service.create("searchable operator visibility", title="Operator visibility quest")
    quest_id = quest["quest_id"]
    quest_root = app.quest_service._quest_root(quest_id)
    bash_id = _seed_bash_session(app, quest_id)

    app.quest_service.update_runtime_state(
        quest_root=quest_root,
        status="running",
        display_status="running",
        active_run_id="run-visibility-001",
        worker_running=True,
        last_tool_activity_at=utc_now(),
        last_tool_activity_name="search_query",
    )
    app.sessions.bind(quest_id, "web-react")
    release, worker = _seed_live_turn_worker(app, quest_id)
    append_jsonl(
        quest_root / ".ds" / "events.jsonl",
        {
            "event_id": "evt-visibility-001",
            "type": "runner.tool_call",
            "quest_id": quest_id,
            "run_id": "run-visibility-001",
            "tool_name": "search_query",
            "summary": "Searching operator visibility fixtures.",
            "created_at": utc_now(),
        },
    )
    app.logger.log(
        "error",
        "runner.turn_error",
        quest_id=quest_id,
        run_id="run-visibility-001",
        summary="Visibility search failed on the second attempt.",
        diagnosis_code="runner_argument_list_too_long",
    )
    try:
        sessions = app.handlers.system_runtime_sessions("/api/system/runtime/sessions")

        assert sessions["totals"]["connector_sessions"] == 1
        assert sessions["totals"]["bash_sessions_running"] == 1
        assert any(item["quest_id"] == quest_id for item in sessions["quest_sessions"])
        assert any(item["quest_id"] == quest_id and item["bash_id"] == bash_id for item in sessions["bash_sessions"])

        sources = app.handlers.system_log_sources()
        source_ids = {item["source_id"] for item in sources["items"]}

        assert "daemon" in source_ids
        assert f"quest-events:{quest_id}" in source_ids
        assert f"bash:{quest_id}:{bash_id}" in source_ids

        daemon_tail = app.handlers.system_log_tail("daemon", "/api/system/logs/daemon/tail?limit=10")
        assert any("Visibility search failed" in line for line in daemon_tail["lines"])

        quest_tail = app.handlers.system_log_tail(
            f"quest-events:{quest_id}",
            f"/api/system/logs/quest-events%3A{quest_id}/tail?limit=10",
        )
        assert any("search_query" in line for line in quest_tail["lines"])

        bash_tail = app.handlers.system_log_tail(
            f"bash:{quest_id}:{bash_id}",
            f"/api/system/logs/bash%3A{quest_id}%3A{bash_id}/tail?limit=10",
        )
        assert any("visibility session still active" in line for line in bash_tail["lines"])

        failures = app.handlers.system_failures("/api/system/failures?limit=10")

        assert failures["total"] >= 1
        assert any(item["quest_id"] == quest_id for item in failures["items"])

        search = app.handlers.system_search("/api/system/search?q=visibility")

        assert search["total"] >= 2
        assert any(item["result_type"] == "quest" and item["result_id"] == quest_id for item in search["items"])
        assert any(item["result_type"] == "log_source" and item["result_id"] == "daemon" for item in search["items"])
    finally:
        release.set()
        worker.join(timeout=1.0)


def test_system_hardware_runtime_tools_and_chart_catalog_are_queryable(temp_home: Path) -> None:
    app = _bootstrap_app(temp_home)
    quest = app.quest_service.create("chartable system slice", title="Chart visibility quest")
    quest_id = quest["quest_id"]

    app.quest_service.update_runtime_state(
        quest_root=app.quest_service._quest_root(quest_id),
        status="running",
        display_status="running",
        active_run_id="run-chart-001",
        worker_running=True,
        last_tool_activity_at=utc_now(),
        last_tool_activity_name="graph",
    )

    tools = app.handlers.system_runtime_tools()
    hardware = app.handlers.system_hardware()
    catalog = app.handlers.system_chart_catalog()
    chart = app.handlers.system_chart_query("quest_status_counts", "/api/system/charts/quest_status_counts")

    assert tools["total"] >= 1
    assert any(item["tool_name"] == "tinytex" for item in tools["items"])

    assert hardware["cpu_count"] >= 1
    assert hardware["home_path"] == str(temp_home.resolve())
    assert "disk" in hardware

    chart_ids = {item["chart_id"] for item in catalog["items"]}
    assert {
        "quest_status_counts",
        "connector_status_counts",
        "bash_session_status_counts",
        "failure_counts",
    } <= chart_ids

    assert chart["chart_id"] == "quest_status_counts"
    assert chart["kind"] == "bar"
    assert any(point["label"] == "running" and point["value"] == 1 for point in chart["series"])
