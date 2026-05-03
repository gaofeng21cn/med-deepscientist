from __future__ import annotations

import json
import threading
from pathlib import Path

from deepscientist.evidence_packets import compact_runner_tool_event
from deepscientist.runners import CodexRunner, RunRequest
from deepscientist.runners.codex import (
    _compact_tool_event_payload,
    _delta_aware_stdout_record,
    _delta_aware_tool_result_event,
    _latest_run_no_progress_classification,
    _new_tool_budget_telemetry,
    _record_tool_budget_event,
    _record_turn_progress_heartbeat,
    _tool_event,
)
from deepscientist.shared import read_json


def test_codex_tool_event_preserves_parseable_bash_exec_payload_and_metadata() -> None:
    long_log = "\n".join(f"line {index}" for index in range(600))
    result_payload = {
        "bash_id": "bash-123",
        "status": "completed",
        "command": "sed -n '1,220p' /tmp/example.txt",
        "workdir": "",
        "cwd": "/tmp/quest",
        "log": long_log,
        "exit_code": 0,
    }
    event = {
        "type": "item.completed",
        "item_type": "mcp_tool_call",
        "item": {
            "type": "mcp_tool_call",
            "id": "tool-123",
            "server": "bash_exec",
            "tool": "bash_exec",
            "status": "completed",
            "arguments": {
                "mode": "read",
                "id": "bash-123",
                "workdir": "/tmp/quest",
            },
            "result": {
                "structured_content": result_payload,
                "content": [{"type": "text", "text": json.dumps(result_payload, ensure_ascii=False)}],
            },
        },
    }

    rendered = _tool_event(
        event,
        quest_id="q-001",
        run_id="run-001",
        skill_id="baseline",
        known_tool_names={},
        created_at="2026-03-21T00:00:00Z",
    )

    assert rendered is not None
    assert rendered["type"] == "runner.tool_result"
    assert len(rendered["output"]) > 1200
    parsed_output = json.loads(rendered["output"])
    assert parsed_output["structured_content"]["bash_id"] == "bash-123"
    assert parsed_output["structured_content"]["log"] == long_log
    assert rendered["metadata"]["bash_id"] == "bash-123"
    assert rendered["metadata"]["command"] == "sed -n '1,220p' /tmp/example.txt"
    assert rendered["metadata"]["cwd"] == "/tmp/quest"


def test_codex_runner_turn_progress_heartbeat_preserves_idempotency_key(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    run_root = quest_root / ".ds" / "runs" / "run-heartbeat-001"
    quest_events = quest_root / ".ds" / "events.jsonl"
    run_root.mkdir(parents=True)
    telemetry = {
        "version": 1,
        "quest_id": "quest-heartbeat-001",
        "run_id": "run-heartbeat-001",
        "turn_id": "turn-heartbeat-001",
        "idempotency_key": "turn-heartbeat-001",
        "turn_reason": "auto_continue",
        "turn_mode": "stage_execution",
        "created_at": "2026-05-02T00:00:00+00:00",
    }

    _record_turn_progress_heartbeat(
        telemetry=telemetry,
        quest_events=quest_events,
        run_root=run_root,
        quest_id="quest-heartbeat-001",
        run_id="run-heartbeat-001",
        source="codex",
        skill_id="write",
        model="inherit",
        summary="Long-running turn is still active.",
    )

    updated = read_json(run_root / "telemetry.json", {})
    events = [json.loads(line) for line in quest_events.read_text(encoding="utf-8").splitlines()]
    assert updated["turn_progress_kind"] == "heartbeat"
    assert updated["turn_progress_heartbeat_count"] == 1
    assert updated["idempotency_key"] == "turn-heartbeat-001"
    assert events[-1]["type"] == "runner.turn_progress"
    assert events[-1]["turn_progress_kind"] == "heartbeat"
    assert events[-1]["idempotency_key"] == "turn-heartbeat-001"


def test_codex_runner_turn_progress_heartbeat_writes_serializable_tool_budget_telemetry(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    run_root = quest_root / ".ds" / "runs" / "run-heartbeat-telemetry-001"
    quest_events = quest_root / ".ds" / "events.jsonl"
    run_root.mkdir(parents=True)
    telemetry = _new_tool_budget_telemetry(tool_call_budget=3)
    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_call",
            "tool_name": "bash_exec.bash_exec",
            "args": json.dumps({"mode": "read", "id": "bash-001"}),
            "command_fingerprint": "bash-read-001",
        },
    )

    _record_turn_progress_heartbeat(
        telemetry=telemetry,
        quest_events=quest_events,
        run_root=run_root,
        quest_id="quest-heartbeat-telemetry-001",
        run_id="run-heartbeat-telemetry-001",
        source="codex",
        skill_id="write",
        model="inherit",
        summary="Long-running turn is still active.",
    )

    updated = read_json(run_root / "telemetry.json", {})
    assert "_unique_command_fingerprints" not in updated
    assert updated["unique_command_count"] == 1
    assert updated["tool_call_count"] == 1
    assert telemetry["_unique_command_fingerprints"] == {"bash-read-001"}


def test_codex_tool_event_truncates_oversized_bash_exec_log_but_keeps_json_parseable() -> None:
    long_log = "\n".join(f"line {index}: {'x' * 200}" for index in range(5000))
    result_payload = {
        "bash_id": "bash-oversized",
        "status": "completed",
        "command": "cat huge.log",
        "cwd": "/tmp/quest",
        "log": long_log,
        "exit_code": 0,
    }
    event = {
        "type": "item.completed",
        "item_type": "mcp_tool_call",
        "item": {
            "type": "mcp_tool_call",
            "id": "tool-oversized",
            "server": "bash_exec",
            "tool": "bash_exec",
            "status": "completed",
            "arguments": {"mode": "read", "id": "bash-oversized"},
            "result": {
                "structured_content": result_payload,
                "content": [{"type": "text", "text": json.dumps(result_payload, ensure_ascii=False)}],
            },
        },
    }

    rendered = _tool_event(
        event,
        quest_id="q-001",
        run_id="run-001",
        skill_id="baseline",
        known_tool_names={},
        created_at="2026-03-21T00:00:00Z",
    )

    assert rendered is not None
    parsed_output = json.loads(rendered["output"])
    truncated_log = parsed_output["structured_content"]["log"]
    assert len(truncated_log) < len(long_log)
    assert "[truncated " in truncated_log


def test_codex_compacts_extreme_tool_result_payload_before_event_write() -> None:
    huge_output = "x" * (3 * 1024 * 1024)
    payload = {
        "event_id": "evt-1",
        "type": "runner.tool_result",
        "quest_id": "q-001",
        "run_id": "run-001",
        "tool_name": "bash_exec.bash_exec",
        "output": huge_output,
        "metadata": {"bash_id": "bash-extreme", "command": "cat extreme.log"},
    }

    rendered = _compact_tool_event_payload(payload)

    assert rendered["type"] == "runner.tool_result"
    assert rendered["output_truncated"] is True
    assert rendered["output_bytes"] > 2_000_000
    assert len(str(rendered["output"])) < 20_000
    assert rendered["metadata"]["bash_id"] == "bash-extreme"


def test_codex_runner_tool_result_sidecars_large_output(temp_home: Path) -> None:
    payload = {
        "event_id": "evt-large-tool",
        "type": "runner.tool_result",
        "quest_id": "q-001",
        "run_id": "run-001",
        "tool_name": "bash_exec.bash_exec",
        "status": "completed",
        "args": '{"mode":"read","id":"bash-large"}',
        "output": json.dumps(
            {
                "ok": True,
                "bash_id": "bash-large",
                "status": "completed",
                "log": "\n".join(f"line {index}: {'x' * 120}" for index in range(400)),
            },
            ensure_ascii=False,
        ),
    }
    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True, exist_ok=True)

    compacted, meta = compact_runner_tool_event(payload, quest_root=quest_root, run_id="run-001")

    assert meta["compacted"] is True
    rendered_output = json.loads(compacted["output"])
    packet = rendered_output["evidence_packet"]
    assert packet["tool_name"] == "bash_exec.bash_exec"
    assert packet["payload_bytes"] > 8_000
    assert Path(packet["sidecar_path"]).exists()
    sidecar = read_json(Path(packet["sidecar_path"]), {})
    assert sidecar["payload"]["bash_id"] == "bash-large"
    assert compacted["output_compaction"]["saved_output_bytes"] > 0
    assert meta["saved_output_bytes"] == compacted["output_compaction"]["saved_output_bytes"]


def test_codex_runner_compacts_hot_status_tool_below_default_threshold(temp_home: Path) -> None:
    payload = {
        "event_id": "evt-hot-status",
        "type": "runner.tool_result",
        "quest_id": "q-001",
        "run_id": "run-001",
        "tool_name": "artifact.get_quest_state",
        "status": "completed",
        "args": json.dumps({"detail": "summary"}),
        "output": json.dumps(
            {
                "ok": True,
                "quest_state": {
                    "runtime_status": "running",
                    "continuation_policy": "auto",
                },
                "recent_events": ["x" * 900 for _ in range(6)],
            },
            ensure_ascii=False,
        ),
    }
    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True, exist_ok=True)

    compacted, meta = compact_runner_tool_event(payload, quest_root=quest_root, run_id="run-001")

    assert 4_000 < meta["output_bytes"] < 8_000
    assert meta["threshold_bytes"] == 4_000
    assert meta["compacted"] is True
    rendered_output = json.loads(compacted["output"])
    assert rendered_output["evidence_packet"]["tool_name"] == "artifact.get_quest_state"


def test_codex_runner_writes_delta_marker_for_repeated_stdout_line(temp_home: Path) -> None:
    quest_root = temp_home / "quest"
    run_root = quest_root / ".ds" / "runs" / "run-001"
    run_root.mkdir(parents=True)
    line = json.dumps({"type": "report", "status": "blocked", "fingerprint": "gate-001"})

    first = _delta_aware_stdout_record(quest_root=quest_root, run_root=run_root, line=line, timestamp="t1")
    second = _delta_aware_stdout_record(quest_root=quest_root, run_root=run_root, line=line, timestamp="t2")

    assert first["line"] == line
    assert "line" not in second
    assert second["delta_marker"] is True
    assert second["fingerprint"] == first["fingerprint"]
    assert second["repeat_count"] == 2


def test_codex_runner_writes_delta_marker_for_repeated_report_tool_result(temp_home: Path) -> None:
    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True)
    payload = {
        "event_id": "evt-report",
        "type": "runner.tool_result",
        "quest_id": "q-001",
        "run_id": "run-001",
        "tool_name": "artifact.get_paper_contract_health",
        "status": "completed",
        "args": json.dumps({"detail": "summary"}),
        "output": json.dumps({"gate": "blocked", "fingerprint": "paper-gate-001"}),
    }

    first = _delta_aware_tool_result_event(payload, quest_root=quest_root, run_id="run-001")
    second = _delta_aware_tool_result_event(payload, quest_root=quest_root, run_id="run-002")

    assert first["output"] == payload["output"]
    assert "output" not in second
    assert second["delta_marker"] is True
    assert second["delta_kind"] == "unchanged_tool_result"
    assert second["fingerprint"] == first["fingerprint"]
    assert second["repeat_count"] == 2


def test_codex_runner_delta_key_normalizes_bash_exec_read_windows(temp_home: Path) -> None:
    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True)
    output = json.dumps({"bash_id": "bash-001", "status": "running", "tail": ["same"]})
    first_payload = {
        "event_id": "evt-bash-read-1",
        "type": "runner.tool_result",
        "quest_id": "q-001",
        "run_id": "run-001",
        "tool_name": "bash_exec.bash_exec",
        "status": "completed",
        "args": json.dumps({"mode": "read", "id": "bash-001", "tail_limit": 100, "after_seq": 10}),
        "output": output,
        "metadata": {"mcp_server": "bash_exec", "mcp_tool": "bash_exec", "command": "pytest -q"},
    }
    second_payload = {
        **first_payload,
        "event_id": "evt-bash-read-2",
        "run_id": "run-002",
        "args": json.dumps({"mode": "read", "id": "bash-001", "tail_limit": 200, "after_seq": 20}),
    }

    first = _delta_aware_tool_result_event(first_payload, quest_root=quest_root, run_id="run-001")
    second = _delta_aware_tool_result_event(second_payload, quest_root=quest_root, run_id="run-002")

    assert "output" in first
    assert "output" not in second
    assert second["delta_kind"] == "unchanged_tool_result"
    assert second["repeat_count"] == 2


def test_codex_runner_tool_budget_telemetry_counts_unique_commands_and_repeated_reads() -> None:
    telemetry = _new_tool_budget_telemetry(tool_call_budget=3)

    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_call",
            "tool_name": "bash_exec.bash_exec",
            "args": json.dumps({"mode": "read", "id": "bash-001", "tail_limit": 100}),
            "metadata": {"command_fingerprint": "cmd-1"},
        },
    )
    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_result",
            "tool_name": "bash_exec.bash_exec",
            "delta_marker": True,
            "delta_kind": "unchanged_tool_result",
            "metadata": {"command_fingerprint": "cmd-1"},
        },
    )
    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_call",
            "tool_name": "artifact.get_quest_state",
            "args": json.dumps({"detail": "full"}),
        },
    )
    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_call",
            "tool_name": "bash_exec.bash_exec",
            "args": json.dumps({"mode": "read", "id": "bash-001", "tail_limit": 200}),
            "metadata": {"command_fingerprint": "cmd-1"},
        },
    )
    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_call",
            "tool_name": "artifact.list_paper_outlines",
            "args": "{}",
        },
    )

    assert telemetry["tool_call_budget"] == 3
    assert telemetry["tool_call_count"] == 4
    assert telemetry["tool_count"] == 4
    assert telemetry["tool_call_budget_remaining"] == 0
    assert telemetry["tool_call_budget_exceeded"] is True
    assert telemetry["unique_command_count"] == 1
    assert telemetry["read_tool_call_count"] == 4
    assert telemetry["repeated_read_result_count"] == 1
    assert telemetry["repeated_read_ratio"] == 1 / 4
    assert telemetry["full_detail_count"] == 1
    assert telemetry["saved_bytes"] == 0


def test_codex_runner_tool_budget_telemetry_counts_embedded_read_cache_delta() -> None:
    telemetry = _new_tool_budget_telemetry(tool_call_budget=4)
    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_call",
            "tool_name": "artifact.get_global_status",
            "args": json.dumps({"detail": "full"}),
        },
    )
    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_result",
            "tool_name": "artifact.get_global_status",
            "output": json.dumps(
                {
                    "structured_content": {
                        "ok": True,
                        "delta_marker": True,
                        "delta_kind": "unchanged_read_cache",
                        "read_cache": {"saved_bytes": 1234},
                    }
                }
            ),
        },
    )

    assert telemetry["repeated_read_result_count"] == 1
    assert telemetry["repeated_read_ratio"] == 1.0
    assert telemetry["read_churn_ratio"] == 1.0
    assert telemetry["same_result_reinjection_count"] == 1
    assert telemetry["saved_bytes"] == 1234


def test_codex_runner_tool_budget_telemetry_records_meaningful_artifact_delta() -> None:
    telemetry = _new_tool_budget_telemetry(tool_call_budget=4)

    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_call",
            "tool_name": "artifact.record",
            "args": json.dumps({"stage_intent": "publication_gate_repair"}),
        },
    )
    _record_tool_budget_event(
        telemetry,
        {
            "type": "runner.tool_result",
            "tool_name": "artifact.record",
            "created_at": "2026-04-30T12:00:00+00:00",
            "output": json.dumps(
                {
                    "structured_content": {
                        "ok": True,
                        "artifact_delta": {
                            "marker": "artifact-delta",
                            "artifact_kind": "paper-writeback",
                            "source_signature": "source-signature-001",
                            "created_at": "2026-04-30T12:00:01+00:00",
                        },
                    }
                }
            ),
        },
    )

    assert telemetry["stage_intent"] == "publication_gate_repair"
    assert telemetry["meaningful_artifact_delta_at"] == "2026-04-30T12:00:01+00:00"
    assert telemetry["meaningful_artifact_delta_kind"] == "paper-writeback"
    assert telemetry["meaningful_artifact_delta_source_signature"] == "source-signature-001"
    assert telemetry["turn_progress_kind"] == "meaningful_artifact_delta"


def test_latest_run_telemetry_classifies_budget_exhausted_no_delta_as_no_progress() -> None:
    classification = _latest_run_no_progress_classification(
        {
            "tool_call_budget_exceeded": True,
            "meaningful_artifact_delta_at": None,
            "turn_progress_kind": "read_churn_without_artifact_delta",
        },
        same_fingerprint_auto_turn_count=3,
        gate_needs_specificity=True,
    )

    assert classification["no_progress_failure"] is True
    assert classification["failure_kind"] == "publication_gate_no_progress"
    assert classification["gate_needs_specificity"] is True
    assert classification["terminal_lifecycle_state"] == "gate_needs_specificity"
    assert classification["reasons"] == [
        "tool_call_budget_exceeded",
        "no_meaningful_artifact_delta",
        "read_churn_without_artifact_delta",
        "same_fingerprint_auto_turn_count_exceeded",
        "gate_needs_specificity",
    ]


def test_latest_run_telemetry_does_not_classify_with_artifact_delta() -> None:
    classification = _latest_run_no_progress_classification(
        {
            "tool_call_budget_exceeded": True,
            "meaningful_artifact_delta_at": "2026-05-02T00:00:00+00:00",
            "turn_progress_kind": "read_churn_without_artifact_delta",
        },
        same_fingerprint_auto_turn_count=3,
        gate_needs_specificity=True,
    )

    assert classification["no_progress_failure"] is False


def test_codex_tool_event_carries_bash_id_from_id_only_monitor_call() -> None:
    event = {
        "type": "item.started",
        "item_type": "mcp_tool_call",
        "item": {
            "type": "mcp_tool_call",
            "id": "tool-456",
            "server": "bash_exec",
            "tool": "bash_exec",
            "status": "in_progress",
            "arguments": {
                "mode": "await",
                "id": "bash-456",
                "workdir": "/tmp/quest",
                "timeout_seconds": 75,
            },
        },
    }

    rendered = _tool_event(
        event,
        quest_id="q-001",
        run_id="run-001",
        skill_id="baseline",
        known_tool_names={},
        created_at="2026-03-21T00:00:00Z",
    )

    assert rendered is not None
    assert rendered["type"] == "runner.tool_call"
    assert json.loads(rendered["args"])["id"] == "bash-456"
    assert rendered["metadata"]["bash_id"] == "bash-456"
    assert rendered["metadata"]["mode"] == "await"
    assert rendered["metadata"]["timeout_seconds"] == 75


def test_codex_tool_event_surfaces_failed_mcp_error_message() -> None:
    event = {
        "type": "item.completed",
        "item_type": "mcp_tool_call",
        "item": {
            "type": "mcp_tool_call",
            "id": "tool-failed",
            "server": "artifact",
            "tool": "get_quest_state",
            "status": "failed",
            "arguments": {"detail": "summary"},
            "error": {"message": "user cancelled MCP tool call"},
        },
    }

    rendered = _tool_event(
        event,
        quest_id="q-001",
        run_id="run-001",
        skill_id="idea",
        known_tool_names={},
        created_at="2026-03-21T00:00:00Z",
    )

    assert rendered is not None
    assert rendered["type"] == "runner.tool_result"
    assert rendered["status"] == "failed"
    assert "user cancelled MCP tool call" in rendered["output"]


def test_codex_runner_injects_builtin_mcp_tool_approval_overrides(temp_home) -> None:  # type: ignore[no-untyped-def]
    source_codex_home = temp_home / "source-codex-home"
    source_codex_home.mkdir(parents=True, exist_ok=True)
    (source_codex_home / "config.toml").write_text('model_provider = "ananapi"\n', encoding="utf-8")
    (source_codex_home / "auth.json").write_text("{}\n", encoding="utf-8")

    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True, exist_ok=True)
    workspace_root = quest_root

    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )

    codex_home = runner._prepare_project_codex_home(
        workspace_root,
        quest_root=quest_root,
        quest_id="q-001",
        run_id="run-001",
        runner_config={"config_dir": str(source_codex_home)},
    )

    config_text = (codex_home / "config.toml").read_text(encoding="utf-8")
    assert 'transport = "stdio"' in config_text
    assert "[mcp_servers.artifact.tools.get_quest_state]" in config_text
    assert "[mcp_servers.memory.tools.list_recent]" in config_text
    assert "[mcp_servers.bash_exec.tools.bash_exec]" in config_text
    assert config_text.count('approval_mode = "approve"') >= 3


def test_codex_runner_omits_model_flag_when_request_uses_inherit(temp_home) -> None:  # type: ignore[no-untyped-def]
    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )
    request = RunRequest(
        quest_id="q-001",
        quest_root=temp_home,
        worktree_root=None,
        run_id="run-001",
        skill_id="baseline",
        message="hello",
        model="inherit",
        approval_policy="on-request",
        sandbox_mode="workspace-write",
        reasoning_effort="xhigh",
    )

    command = runner._build_command(request, "prompt", runner_config={})

    assert "--model" not in command


def test_codex_runner_omits_model_flag_when_request_uses_inherit_local_codex_default(
    temp_home,
) -> None:  # type: ignore[no-untyped-def]
    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )
    request = RunRequest(
        quest_id="q-001",
        quest_root=temp_home,
        worktree_root=None,
        run_id="run-001",
        skill_id="baseline",
        message="hello",
        model="inherit_local_codex_default",
        approval_policy="on-request",
        sandbox_mode="workspace-write",
        reasoning_effort="",
    )

    command = runner._build_command(request, "prompt", runner_config={})

    assert "--model" not in command


def test_codex_runner_includes_profile_when_runner_config_requests_it(temp_home) -> None:  # type: ignore[no-untyped-def]
    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )
    request = RunRequest(
        quest_id="q-001",
        quest_root=temp_home,
        worktree_root=None,
        run_id="run-001",
        skill_id="baseline",
        message="hello",
        model="inherit",
        approval_policy="on-request",
        sandbox_mode="workspace-write",
        reasoning_effort="xhigh",
    )

    command = runner._build_command(request, "prompt", runner_config={"profile": "m27"})

    assert command[1:4] == ["--search", "--profile", "m27"]


def test_codex_runner_profile_forces_inherit_model_flag(temp_home) -> None:  # type: ignore[no-untyped-def]
    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )
    request = RunRequest(
        quest_id="q-001",
        quest_root=temp_home,
        worktree_root=None,
        run_id="run-001",
        skill_id="baseline",
        message="hello",
        model="gpt-5.4",
        approval_policy="on-request",
        sandbox_mode="workspace-write",
        reasoning_effort="",
    )

    command = runner._build_command(request, "prompt", runner_config={"profile": "m27"})

    assert command[1:4] == ["--search", "--profile", "m27"]
    assert "--model" not in command


def test_codex_runner_downgrades_xhigh_for_legacy_codex_cli(monkeypatch, temp_home) -> None:  # type: ignore[no-untyped-def]
    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )
    request = RunRequest(
        quest_id="q-001",
        quest_root=temp_home,
        worktree_root=None,
        run_id="run-001",
        skill_id="baseline",
        message="hello",
        model="inherit",
        approval_policy="on-request",
        sandbox_mode="workspace-write",
        reasoning_effort="xhigh",
    )

    monkeypatch.setattr("deepscientist.runners.codex.resolve_runner_binary", lambda binary, runner_name=None: "/tmp/fake-codex")
    monkeypatch.setattr(
        "deepscientist.runners.codex.normalize_codex_reasoning_effort",
        lambda reasoning_effort, *, resolved_binary: ("high", "downgraded"),
    )

    command = runner._build_command(request, "prompt", runner_config={"profile": "m27"})

    assert '-c' in command
    assert 'model_reasoning_effort="high"' in command
    assert 'model_reasoning_effort="xhigh"' not in command


def test_codex_runner_prepares_project_home_from_runner_config_dir(temp_home) -> None:  # type: ignore[no-untyped-def]
    source_home = temp_home / "provider-codex-home"
    source_home.mkdir(parents=True, exist_ok=True)
    (source_home / "config.toml").write_text("[profiles.m27]\n", encoding="utf-8")
    (source_home / "auth.json").write_text('{"provider":"custom"}', encoding="utf-8")

    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True, exist_ok=True)
    workspace_root = quest_root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )

    target = runner._prepare_project_codex_home(
        workspace_root,
        quest_root=quest_root,
        quest_id="q-001",
        run_id="run-001",
        runner_config={"config_dir": str(source_home)},
    )

    config_text = (Path(target) / "config.toml").read_text(encoding="utf-8")
    assert config_text.startswith("[profiles.m27]\n")
    assert "# BEGIN DEEPSCIENTIST BUILTINS" in config_text
    assert (Path(target) / "auth.json").read_text(encoding="utf-8") == '{"provider":"custom"}'


def test_codex_runner_prepares_project_home_overwrites_existing_provider_files(temp_home) -> None:  # type: ignore[no-untyped-def]
    source_home = temp_home / "provider-codex-home"
    source_home.mkdir(parents=True, exist_ok=True)
    (source_home / "config.toml").write_text("[profiles.m27]\nmodel = \"new-profile\"\n", encoding="utf-8")
    (source_home / "auth.json").write_text('{"provider":"new-auth"}', encoding="utf-8")

    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True, exist_ok=True)
    workspace_root = quest_root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    target_home = workspace_root / ".codex"
    target_home.mkdir(parents=True, exist_ok=True)
    (target_home / "config.toml").write_text("[profiles.old]\nmodel = \"old-profile\"\n", encoding="utf-8")
    (target_home / "auth.json").write_text('{"provider":"old-auth"}', encoding="utf-8")

    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )

    target = runner._prepare_project_codex_home(
        workspace_root,
        quest_root=quest_root,
        quest_id="q-001",
        run_id="run-001",
        runner_config={"config_dir": str(source_home)},
    )

    config_text = (Path(target) / "config.toml").read_text(encoding="utf-8")
    assert 'model = "new-profile"' in config_text
    assert 'old-profile' not in config_text
    assert (Path(target) / "auth.json").read_text(encoding="utf-8") == '{"provider":"new-auth"}'


def test_codex_runner_prepares_project_home_adapting_profile_only_provider_config(temp_home) -> None:  # type: ignore[no-untyped-def]
    source_home = temp_home / "provider-codex-home"
    source_home.mkdir(parents=True, exist_ok=True)
    (source_home / "config.toml").write_text(
        """[model_providers.minimax]
name = "MiniMax Chat Completions API"
base_url = "https://api.minimaxi.com/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "chat"
requires_openai_auth = false

[profiles.m27]
model = "MiniMax-M2.7"
model_provider = "minimax"
""",
        encoding="utf-8",
    )

    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True, exist_ok=True)
    workspace_root = quest_root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )

    target = runner._prepare_project_codex_home(
        workspace_root,
        quest_root=quest_root,
        quest_id="q-001",
        run_id="run-001",
        runner_config={"config_dir": str(source_home), "profile": "m27"},
    )

    config_text = (Path(target) / "config.toml").read_text(encoding="utf-8")
    assert 'model_provider = "minimax"' in config_text
    assert 'model = "MiniMax-M2.7"' in config_text


def test_codex_runner_sanitizes_openai_env_for_provider_without_openai_auth(temp_home) -> None:  # type: ignore[no-untyped-def]
    source_home = temp_home / "provider-codex-home"
    source_home.mkdir(parents=True, exist_ok=True)
    (source_home / "config.toml").write_text(
        """[model_providers.minimax]
name = "MiniMax Chat Completions API"
base_url = "https://api.minimaxi.com/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "chat"
requires_openai_auth = false

[profiles.m27]
model = "MiniMax-M2.7"
model_provider = "minimax"
""",
        encoding="utf-8",
    )

    env = CodexRunner._sanitize_provider_env(
        {
            "CODEX_HOME": str(source_home),
            "OPENAI_API_KEY": "openai-secret",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "MINIMAX_API_KEY": "minimax-secret",
        },
        runner_config={"config_dir": str(source_home), "profile": "m27"},
    )

    assert env["MINIMAX_API_KEY"] == "minimax-secret"
    assert "OPENAI_API_KEY" not in env
    assert "OPENAI_BASE_URL" not in env


def test_codex_runner_appends_single_tool_guard_for_chat_wire_profile(temp_home) -> None:  # type: ignore[no-untyped-def]
    source_home = temp_home / "provider-codex-home"
    source_home.mkdir(parents=True, exist_ok=True)
    (source_home / "config.toml").write_text(
        """[model_providers.minimax]
name = "MiniMax Chat Completions API"
base_url = "https://api.minimaxi.com/v1"
env_key = "MINIMAX_API_KEY"
wire_api = "chat"
requires_openai_auth = false

[profiles.m27]
model = "MiniMax-M2.7"
model_provider = "minimax"
""",
        encoding="utf-8",
    )

    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )

    prompt = runner._apply_chat_wire_tool_call_guard(
        "BASE PROMPT",
        runner_config={"config_dir": str(source_home), "profile": "m27"},
    )

    assert "BASE PROMPT" in prompt
    assert "## Codex Chat-Wire Tool Call Compatibility" in prompt
    assert "active_provider_profile: m27" in prompt
    assert "single_tool_call_per_turn_rule" in prompt
    assert "no_batched_mcp_rule" in prompt
    assert "no_immediate_repeat_rule" in prompt


def test_codex_runner_skips_single_tool_guard_for_non_chat_profile(temp_home) -> None:  # type: ignore[no-untyped-def]
    source_home = temp_home / "provider-codex-home"
    source_home.mkdir(parents=True, exist_ok=True)
    (source_home / "config.toml").write_text(
        """[model_providers.local]
name = "Local Responses"
base_url = "http://127.0.0.1:8004/v1"
env_key = "LOCAL_API_KEY"
wire_api = "responses"
requires_openai_auth = false

[profiles.local]
model = "gpt-oss"
model_provider = "local"
""",
        encoding="utf-8",
    )

    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )

    prompt = runner._apply_chat_wire_tool_call_guard(
        "BASE PROMPT",
        runner_config={"config_dir": str(source_home), "profile": "local"},
    )

    assert prompt == "BASE PROMPT"


def test_codex_runner_subprocess_popen_kwargs_hide_windows_console(monkeypatch, temp_home) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_process_session_popen_kwargs(*, hide_window: bool = False, new_process_group: bool = True):  # noqa: ANN001
        captured["hide_window"] = hide_window
        captured["new_process_group"] = new_process_group
        return {"creationflags": 1536, "startupinfo": object()}

    monkeypatch.setattr("deepscientist.runners.codex.process_session_popen_kwargs", fake_process_session_popen_kwargs)

    kwargs = CodexRunner._subprocess_popen_kwargs(
        workspace_root=Path(temp_home),
        env={"TEST_ENV": "1"},
    )

    assert captured["hide_window"] is True
    assert captured["new_process_group"] is True
    assert kwargs["cwd"] == str(temp_home)
    assert kwargs["env"] == {"TEST_ENV": "1"}
    assert kwargs["text"] is True
    assert kwargs["creationflags"] == 1536
    assert "startupinfo" in kwargs


def test_codex_runner_prepares_run_scoped_codex_home(temp_home) -> None:  # type: ignore[no-untyped-def]
    source_home = temp_home / "provider-codex-home"
    source_home.mkdir(parents=True, exist_ok=True)
    (source_home / "config.toml").write_text("[profiles.m27]\n", encoding="utf-8")
    (source_home / "auth.json").write_text('{"provider":"custom"}', encoding="utf-8")

    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True, exist_ok=True)
    workspace_root = quest_root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=object(),  # type: ignore[arg-type]
        prompt_builder=object(),  # type: ignore[arg-type]
        artifact_service=object(),  # type: ignore[arg-type]
    )

    first_target = Path(
        runner._prepare_project_codex_home(
            workspace_root,
            quest_root=quest_root,
            quest_id="q-001",
            run_id="run-001",
            runner_config={"config_dir": str(source_home)},
        )
    )
    second_target = Path(
        runner._prepare_project_codex_home(
            workspace_root,
            quest_root=quest_root,
            quest_id="q-001",
            run_id="run-002",
            runner_config={"config_dir": str(source_home)},
        )
    )

    assert first_target == quest_root / ".ds" / "codex_homes" / "run-001"
    assert second_target == quest_root / ".ds" / "codex_homes" / "run-002"
    assert first_target != second_target
    assert not (workspace_root / ".codex").exists()


def test_codex_runner_drains_stderr_before_stdout_finishes(monkeypatch, temp_home) -> None:  # type: ignore[no-untyped-def]
    class _PromptBuilder:
        def build(self, **_: object) -> str:
            return "prompt from builder"

    class _Logger:
        def log(self, *_args: object, **_kwargs: object) -> None:
            return None

    class _QuestService:
        def schedule_projection_refresh(self, *_args: object, **_kwargs: object) -> None:
            return None

    class _ArtifactService:
        def __init__(self) -> None:
            self.quest_service = _QuestService()

        def record(self, *_args: object, **_kwargs: object) -> dict[str, object]:
            return {"artifact_id": "artifact-001"}

    class _FakeStdin:
        def __init__(self) -> None:
            self.buffer = ""

        def write(self, text: str) -> int:
            self.buffer += text
            return len(text)

        def close(self) -> None:
            return None

    class _FakeStdout:
        def __init__(self, release_event: threading.Event, stderr_read_started: threading.Event) -> None:
            self._release_event = release_event
            self._stderr_read_started = stderr_read_started
            self._prefix = [
                json.dumps({"type": "thread.started", "thread_id": "thr-001"}) + "\n",
                json.dumps({"type": "turn.started"}) + "\n",
            ]
            self._suffix = [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "id": "item-001",
                            "text": "done",
                        },
                    }
                )
                + "\n",
                json.dumps({"type": "turn.completed"}) + "\n",
            ]

        def __iter__(self) -> "_FakeStdout":
            return self

        def __next__(self) -> str:
            if self._prefix:
                return self._prefix.pop(0)
            if self._suffix:
                if not self._stderr_read_started.is_set():
                    self._release_event.wait()
                return self._suffix.pop(0)
            raise StopIteration

    class _FakeStderr:
        def __init__(self, stderr_read_started: threading.Event) -> None:
            self._stderr_read_started = stderr_read_started

        def read(self) -> str:
            self._stderr_read_started.set()
            return "warning\n" * 4096

    class _FakeProcess:
        def __init__(self) -> None:
            self.release_event = threading.Event()
            self.stderr_read_started = threading.Event()
            self.stdin = _FakeStdin()
            self.stdout = _FakeStdout(self.release_event, self.stderr_read_started)
            self.stderr = _FakeStderr(self.stderr_read_started)

        def wait(self) -> int:
            return 0

        def poll(self) -> None:
            return None

    fake_process = _FakeProcess()

    monkeypatch.setattr("deepscientist.runners.codex.subprocess.Popen", lambda *args, **kwargs: fake_process)
    monkeypatch.setattr("deepscientist.runners.codex.export_git_graph", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "deepscientist.runners.codex.normalize_codex_reasoning_effort",
        lambda reasoning_effort, *, resolved_binary: (str(reasoning_effort), None),
    )

    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=_Logger(),  # type: ignore[arg-type]
        prompt_builder=_PromptBuilder(),  # type: ignore[arg-type]
        artifact_service=_ArtifactService(),  # type: ignore[arg-type]
    )

    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True, exist_ok=True)
    (quest_root / "quest.yaml").write_text("active_anchor: write\n", encoding="utf-8")
    request = RunRequest(
        quest_id="q-001",
        quest_root=quest_root,
        worktree_root=quest_root / "workspace",
        run_id="run-001",
        skill_id="write",
        message="continue",
        model="gpt-5.4",
        approval_policy="never",
        sandbox_mode="danger-full-access",
        reasoning_effort="xhigh",
        turn_reason="auto_continue",
        turn_intent="continue_stage",
        turn_mode="stage_execution",
    )
    request.worktree_root.mkdir(parents=True, exist_ok=True)

    result_holder: dict[str, object] = {}
    error_holder: list[BaseException] = []
    finished = threading.Event()

    def _run() -> None:
        try:
            result_holder["result"] = runner.run(request)
        except BaseException as exc:  # pragma: no cover - surfaced below
            error_holder.append(exc)
        finally:
            finished.set()

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()

    try:
        assert finished.wait(timeout=1.0), "runner blocked waiting for stderr to drain"
    finally:
        fake_process.release_event.set()
        worker.join(timeout=1.0)

    if error_holder:
        raise error_holder[0]

    result = result_holder["result"]
    assert getattr(result, "output_text") == "done"
    telemetry = read_json(quest_root / ".ds" / "runs" / "run-001" / "telemetry.json", {})
    assert telemetry["prompt_bytes"] == len("prompt from builder".encode("utf-8"))
    assert telemetry["stdout_event_count"] == 4
    assert telemetry["model_inherited"] is False
    assert telemetry["reasoning_effort"] == "xhigh"


def test_codex_runner_preserves_success_when_artifact_record_postprocess_fails(
    monkeypatch,
    temp_home,
) -> None:  # type: ignore[no-untyped-def]
    class _PromptBuilder:
        def build(self, **_: object) -> str:
            return "prompt from builder"

    class _Logger:
        def __init__(self) -> None:
            self.events: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def log(self, *args: object, **kwargs: object) -> None:
            self.events.append((args, kwargs))

    class _QuestService:
        def schedule_projection_refresh(self, *_args: object, **_kwargs: object) -> None:
            return None

    class _ArtifactService:
        def __init__(self) -> None:
            self.quest_service = _QuestService()

        def record(self, *_args: object, **_kwargs: object) -> dict[str, object]:
            raise RuntimeError("unknown file extension: .png")

    class _FakeStdin:
        def write(self, text: str) -> int:
            return len(text)

        def close(self) -> None:
            return None

    class _FakeStdout:
        def __init__(self) -> None:
            self._lines = [
                json.dumps({"type": "thread.started", "thread_id": "thr-001"}) + "\n",
                json.dumps({"type": "turn.started"}) + "\n",
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "id": "item-001", "text": "done"},
                    }
                )
                + "\n",
                json.dumps({"type": "turn.completed"}) + "\n",
            ]

        def __iter__(self) -> "_FakeStdout":
            return self

        def __next__(self) -> str:
            if not self._lines:
                raise StopIteration
            return self._lines.pop(0)

    class _FakeStderr:
        def read(self) -> str:
            return ""

    class _FakeProcess:
        stdin = _FakeStdin()
        stdout = _FakeStdout()
        stderr = _FakeStderr()

        def wait(self) -> int:
            return 0

        def poll(self) -> None:
            return None

    monkeypatch.setattr("deepscientist.runners.codex.subprocess.Popen", lambda *args, **kwargs: _FakeProcess())
    monkeypatch.setattr(
        "deepscientist.runners.codex.normalize_codex_reasoning_effort",
        lambda reasoning_effort, *, resolved_binary: (str(reasoning_effort), None),
    )

    logger = _Logger()
    runner = CodexRunner(
        home=temp_home,
        repo_root=temp_home,
        binary="codex",
        logger=logger,  # type: ignore[arg-type]
        prompt_builder=_PromptBuilder(),  # type: ignore[arg-type]
        artifact_service=_ArtifactService(),  # type: ignore[arg-type]
    )

    quest_root = temp_home / "quest"
    quest_root.mkdir(parents=True, exist_ok=True)
    (quest_root / "quest.yaml").write_text("active_anchor: write\n", encoding="utf-8")
    worktree_root = quest_root / "workspace"
    worktree_root.mkdir(parents=True, exist_ok=True)
    result = runner.run(
        RunRequest(
            quest_id="q-001",
            quest_root=quest_root,
            worktree_root=worktree_root,
            run_id="run-001",
            skill_id="write",
            message="continue",
            model="gpt-5.4",
            approval_policy="never",
            sandbox_mode="danger-full-access",
            reasoning_effort="xhigh",
            turn_reason="auto_continue",
            turn_intent="continue_stage",
            turn_mode="stage_execution",
        )
    )

    assert result.ok is True
    assert result.exit_code == 0
    events = (quest_root / ".ds" / "events.jsonl").read_text(encoding="utf-8")
    assert "runner.turn_postprocess_warning" in events
    assert "runner.turn_error" not in events
    artifact = read_json(quest_root / ".ds" / "runs" / "run-001" / "artifact.json", {})
    assert artifact["status"] == "postprocess_failed"
    assert artifact["stage"] == "artifact_record"
