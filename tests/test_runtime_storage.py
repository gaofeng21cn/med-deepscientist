from __future__ import annotations

from datetime import UTC, datetime, timedelta
import gzip
import json
import os
import time
from pathlib import Path

from deepscientist.runtime_storage import maintain_quest_runtime_storage


def test_runtime_storage_maintenance_compacts_completed_bash_logs_and_prunes_tempfiles(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    bash_root = quest_root / ".ds" / "bash_exec" / "bash-001"
    bash_root.mkdir(parents=True, exist_ok=True)
    (quest_root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    meta = {
        "bash_id": "bash-001",
        "status": "terminated",
        "finished_at": "2026-04-10T00:00:00+00:00",
        "updated_at": "2026-04-10T00:00:00+00:00",
    }
    (bash_root / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = "x" * 150_000
    log_lines = [
        json.dumps(
            {
                "seq": seq,
                "stream": "stdout",
                "line": f"line-{seq}:{payload}",
                "timestamp": "2026-04-10T00:00:00+00:00",
            }
        )
        for seq in range(1, 11)
    ]
    (bash_root / "log.jsonl").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    (bash_root / "terminal.log").write_text(
        "\n".join(f"terminal-{idx}:{payload}" for idx in range(1, 11)) + "\n",
        encoding="utf-8",
    )
    projection_root = quest_root / ".ds" / "projections"
    projection_root.mkdir(parents=True, exist_ok=True)
    (projection_root / "details.v1.json").write_text('{"ok":true}\n', encoding="utf-8")
    stale_tmp = projection_root / "details.v1.json.abc12345.tmp"
    stale_tmp.write_text("stale\n", encoding="utf-8")
    old = time.time() - 8 * 3600
    os.utime(stale_tmp, (old, old))
    codex_tmp = quest_root / ".ds" / "codex_homes" / "run-001" / ".tmp" / "plugins.sha"
    codex_tmp.parent.mkdir(parents=True, exist_ok=True)
    codex_tmp.write_text("abc\n", encoding="utf-8")
    os.utime(codex_tmp.parent, (old, old))
    os.utime(codex_tmp, (old, old))
    codex_execve_tmp = quest_root / ".ds" / "codex_homes" / "run-001" / "tmp" / "arg0" / "codex-arg0abc123" / "apply_patch"
    codex_execve_tmp.parent.mkdir(parents=True, exist_ok=True)
    codex_execve_tmp.write_text("binary-placeholder\n", encoding="utf-8")
    os.utime(codex_execve_tmp.parent.parent.parent, (old, old))
    os.utime(codex_execve_tmp.parent.parent, (old, old))
    os.utime(codex_execve_tmp.parent, (old, old))
    os.utime(codex_execve_tmp, (old, old))

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=3600,
        jsonl_max_mb=1,
        text_max_mb=1,
        head_lines=2,
        tail_lines=2,
    )

    compacted_log = (bash_root / "log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(compacted_log) == 5
    assert any("compacted completed runtime log" in line for line in compacted_log)
    archived_log = quest_root / ".ds" / "cold_archive" / "bash_exec" / ".ds" / "bash_exec" / "bash-001" / "log.full.jsonl.gz"
    assert archived_log.exists()
    assert not (bash_root / "log.full.jsonl.gz").exists()
    assert (bash_root / "log.full.jsonl.gz.index.json").exists()
    with gzip.open(archived_log, "rt", encoding="utf-8") as handle:
        archived_lines = handle.read().splitlines()
    assert len(archived_lines) == 10

    compacted_terminal = (bash_root / "terminal.log").read_text(encoding="utf-8").splitlines()
    assert len(compacted_terminal) == 5
    assert any("compacted completed runtime log" in line for line in compacted_terminal)
    assert (
        quest_root / ".ds" / "cold_archive" / "bash_exec" / ".ds" / "bash_exec" / "bash-001" / "terminal.full.log.gz"
    ).exists()
    assert not (bash_root / "terminal.full.log.gz").exists()
    assert not stale_tmp.exists()
    assert not codex_tmp.parent.exists()
    assert not codex_execve_tmp.parent.parent.parent.exists()
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert len(runtime_logs) == 2
    cold_archive = result["roots"][0]["cold_archive"]
    assert cold_archive["moved_file_count"] == 2
    gitignore_text = (quest_root / ".gitignore").read_text(encoding="utf-8")
    assert ".ds/**/*.tmp" in gitignore_text
    assert ".ds/bash_exec/" in gitignore_text
    assert ".ds/codex_history/" in gitignore_text
    assert ".ds/codex_homes/" in gitignore_text
    assert ".ds/runs/" in gitignore_text


def test_runtime_storage_maintenance_compacts_large_single_line_terminal_logs(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    bash_root = quest_root / ".ds" / "bash_exec" / "bash-002"
    bash_root.mkdir(parents=True, exist_ok=True)
    (quest_root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    meta = {
        "bash_id": "bash-002",
        "status": "terminated",
        "finished_at": "2026-04-10T00:00:00+00:00",
        "updated_at": "2026-04-10T00:00:00+00:00",
    }
    (bash_root / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    huge_line = "terminal:" + ("x" * 1_500_000)
    (bash_root / "terminal.log").write_text(huge_line + "\n", encoding="utf-8")

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=3600,
        jsonl_max_mb=1,
        text_max_mb=1,
        head_lines=2,
        tail_lines=2,
    )

    compacted_terminal = (bash_root / "terminal.log").read_text(encoding="utf-8")
    assert "compacted completed runtime log" in compacted_terminal
    assert (
        quest_root / ".ds" / "cold_archive" / "bash_exec" / ".ds" / "bash_exec" / "bash-002" / "terminal.full.log.gz"
    ).exists()
    assert not (bash_root / "terminal.full.log.gz").exists()
    assert (bash_root / "terminal.log").stat().st_size < 1_000_000
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert len(runtime_logs) == 1


def test_runtime_storage_maintenance_compacts_large_single_line_jsonl_logs(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    bash_root = quest_root / ".ds" / "bash_exec" / "bash-003"
    bash_root.mkdir(parents=True, exist_ok=True)
    (quest_root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    meta = {
        "bash_id": "bash-003",
        "status": "terminated",
        "finished_at": "2026-04-10T00:00:00+00:00",
        "updated_at": "2026-04-10T00:00:00+00:00",
    }
    (bash_root / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    huge_payload = "jsonl:" + ("x" * 1_500_000)
    huge_line = json.dumps(
        {
            "seq": 1,
            "stream": "stdout",
            "line": huge_payload,
            "timestamp": "2026-04-10T00:00:00+00:00",
        }
    )
    (bash_root / "log.jsonl").write_text(huge_line + "\n", encoding="utf-8")

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=3600,
        jsonl_max_mb=1,
        text_max_mb=1,
        head_lines=2,
        tail_lines=2,
    )

    compacted_log = (bash_root / "log.jsonl").read_text(encoding="utf-8")
    assert "compacted completed runtime log" in compacted_log
    assert (
        quest_root / ".ds" / "cold_archive" / "bash_exec" / ".ds" / "bash_exec" / "bash-003" / "log.full.jsonl.gz"
    ).exists()
    assert not (bash_root / "log.full.jsonl.gz").exists()
    assert (bash_root / "log.jsonl").stat().st_size < 1_000_000
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert len(runtime_logs) == 1


def test_runtime_storage_maintenance_compacts_stale_running_sessions_with_finished_at(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    bash_root = quest_root / ".ds" / "bash_exec" / "bash-004"
    bash_root.mkdir(parents=True, exist_ok=True)
    (quest_root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    meta = {
        "bash_id": "bash-004",
        "status": "running",
        "finished_at": "2026-04-10T00:00:00+00:00",
        "updated_at": "2026-04-10T00:00:00+00:00",
    }
    (bash_root / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    huge_line = "terminal:" + ("x" * 1_500_000)
    (bash_root / "terminal.log").write_text(huge_line + "\n", encoding="utf-8")

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=3600,
        jsonl_max_mb=1,
        text_max_mb=1,
        head_lines=2,
        tail_lines=2,
    )

    compacted_terminal = (bash_root / "terminal.log").read_text(encoding="utf-8")
    assert "compacted completed runtime log" in compacted_terminal
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert len(runtime_logs) == 1


def test_runtime_storage_maintenance_compacts_cold_run_stdout_logs(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    run_id = "run-compact-001"
    run_root = quest_root / ".ds" / "runs" / run_id
    history_root = quest_root / ".ds" / "codex_history" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    history_root.mkdir(parents=True, exist_ok=True)
    payload = "stdout:" + ("x" * 150_000)
    (run_root / "stdout.jsonl").write_text(
        "\n".join(
            json.dumps({"timestamp": "2026-04-10T00:00:00+00:00", "line": f"{index}:{payload}"}, ensure_ascii=False)
            for index in range(10)
        )
        + "\n",
        encoding="utf-8",
    )
    (history_root / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "completed_at": "2026-04-10T00:00:00+00:00",
                "updated_at": "2026-04-10T00:00:00+00:00",
                "exit_code": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=3600,
        jsonl_max_mb=1,
        text_max_mb=1,
        head_lines=2,
        tail_lines=2,
    )

    compacted_stdout = (run_root / "stdout.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(compacted_stdout) == 5
    assert any("compacted completed runtime log" in line for line in compacted_stdout)
    assert (run_root / "stdout.full.jsonl.gz").exists()
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert any(item["path"].endswith("stdout.jsonl") for item in runtime_logs)


def test_runtime_storage_maintenance_compacts_cold_codex_session_logs(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    run_id = "run-compact-002"
    history_root = quest_root / ".ds" / "codex_history" / run_id
    session_path = quest_root / ".ds" / "codex_homes" / run_id / "sessions" / "2026" / "04" / "15" / "rollout.jsonl"
    history_root.mkdir(parents=True, exist_ok=True)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "session:" + ("x" * 150_000)
    session_path.write_text(
        "\n".join(
            json.dumps({"seq": index + 1, "item": {"type": "message", "text": f"{index}:{payload}"}}, ensure_ascii=False)
            for index in range(10)
        )
        + "\n",
        encoding="utf-8",
    )
    (history_root / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "completed_at": "2026-04-10T00:00:00+00:00",
                "updated_at": "2026-04-10T00:00:00+00:00",
                "exit_code": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=3600,
        jsonl_max_mb=1,
        text_max_mb=1,
        head_lines=2,
        tail_lines=2,
    )

    compacted_session_path = session_path.with_name("rollout.compact.ndjson")
    compacted_session = compacted_session_path.read_text(encoding="utf-8").splitlines()
    assert len(compacted_session) == 5
    assert any("compacted completed runtime log" in line for line in compacted_session)
    cold_session = (
        quest_root
        / ".ds"
        / "cold_archive"
        / "codex_sessions"
        / ".ds"
        / "codex_homes"
        / run_id
        / "sessions"
        / "2026"
        / "04"
        / "15"
        / "rollout.jsonl.gz"
    )
    assert cold_session.exists()
    assert not session_path.exists()
    assert session_path.with_name("rollout.jsonl.index.json").exists()
    assert not session_path.with_name("rollout.full.jsonl.gz").exists()
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert any(item["path"].endswith("rollout.jsonl") for item in runtime_logs)
    cold_archive = result["roots"][0]["cold_archive"]
    assert any(item["kind"] == "codex_session_jsonl" for item in cold_archive["moved_files"])


def test_runtime_storage_maintenance_rotates_quest_events_into_segments(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    events_path = quest_root / ".ds" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "event:" + ("x" * 80_000)
    events_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "event_id": f"evt-{index}",
                    "type": "runner.tool_result",
                    "run_id": "run-001",
                    "created_at": "2026-04-10T00:00:00+00:00",
                    "output": payload,
                },
                ensure_ascii=False,
            )
            for index in range(20)
        )
        + "\n",
        encoding="utf-8",
    )

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=0,
        event_segment_max_mb=1,
    )

    events_manifest = result["roots"][0]["events"]
    assert events_manifest["rotated_segment_count"] == 1
    assert events_path.exists()
    assert events_path.read_text(encoding="utf-8") == ""
    manifest_path = quest_root / ".ds" / "events" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["segment_count"] == 1
    segment_ref = manifest["segments"][0]["path"]
    segment_path = quest_root / segment_ref
    assert segment_path.exists()
    with gzip.open(segment_path, "rt", encoding="utf-8") as handle:
        assert len(handle.read().splitlines()) == 20


def test_runtime_storage_maintenance_applies_report_history_retention_contract(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    reports_root = quest_root / "artifacts" / "reports" / "runtime_events"
    reports_root.mkdir(parents=True, exist_ok=True)
    (reports_root / "latest.json").write_text('{"keep":"latest"}\n', encoding="utf-8")
    (reports_root / "state.json").write_text('{"keep":"state"}\n', encoding="utf-8")
    now = datetime.now(UTC)

    def _write_report(name: str, age_hours: int) -> Path:
        path = reports_root / name
        path.write_text(json.dumps({"name": name}, ensure_ascii=False) + "\n", encoding="utf-8")
        timestamp = (now - timedelta(hours=age_hours)).timestamp()
        os.utime(path, (timestamp, timestamp))
        return path

    recent_kept = _write_report("20260419T010000Z_runtime_state_observed.json", 2)
    recent_archived = _write_report("20260419T013000Z_runtime_state_observed.json", 2)
    old_kept = _write_report("20260414T010000Z_runtime_state_observed.json", 120)
    old_archived = _write_report("20260414T020000Z_runtime_state_observed.json", 120)

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=0,
    )

    retention = result["roots"][0]["report_history_retention"]
    assert retention["retention_contract"]["recent_hourly_window_hours"] == 72
    assert retention["archived_file_count"] == 2
    assert (reports_root / "latest.json").exists()
    assert (reports_root / "state.json").exists()
    assert recent_kept.exists()
    assert old_kept.exists()
    assert not recent_archived.exists()
    assert not old_archived.exists()
    manifest_path = quest_root / "artifacts" / "reports" / "retention_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["retention_contract"]["older_sampling"] == "daily"
    assert manifest["archived_file_count"] == 2


def test_runtime_storage_maintenance_slims_oversized_run_and_history_jsonl_entries(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    run_id = "run-oversized-001"
    run_root = quest_root / ".ds" / "runs" / run_id
    history_root = quest_root / ".ds" / "codex_history" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    history_root.mkdir(parents=True, exist_ok=True)
    huge_text = "x" * 1_500_000
    (run_root / "stdout.jsonl").write_text(
        json.dumps({"timestamp": "2026-04-10T00:00:00+00:00", "line": huge_text}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (history_root / "events.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-04-10T00:00:00+00:00",
                "event": {
                    "type": "message",
                    "content": huge_text,
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (history_root / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "completed_at": "2026-04-10T00:00:00+00:00",
                "updated_at": "2026-04-10T00:00:00+00:00",
                "exit_code": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=3600,
        slim_jsonl_threshold_mb=1,
    )

    compacted_stdout = (run_root / "stdout.jsonl").read_text(encoding="utf-8")
    compacted_history = (history_root / "events.jsonl").read_text(encoding="utf-8")
    assert "compacted oversized stdout entry" in compacted_stdout
    assert "Oversized codex history entry" in compacted_history
    slim_manifest = result["roots"][0]["oversized_jsonl"]
    assert slim_manifest["compacted_line_count"] == 2
    assert slim_manifest["files"]
    backup_root = Path(slim_manifest["backup_root"])
    assert backup_root.exists()
    assert (backup_root / "manifest.json").exists()


def test_runtime_storage_maintenance_dedupes_large_worktree_cold_files(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    session_a = quest_root / ".ds" / "worktrees" / "wt-a" / ".codex" / "sessions" / "2026" / "04" / "a.jsonl"
    session_b = quest_root / ".ds" / "worktrees" / "wt-b" / ".codex" / "sessions" / "2026" / "04" / "b.jsonl"
    session_a.parent.mkdir(parents=True, exist_ok=True)
    session_b.parent.mkdir(parents=True, exist_ok=True)
    duplicated_payload = (json.dumps({"message": "x" * 1_500_000}, ensure_ascii=False) + "\n") * 2
    session_a.write_text(duplicated_payload, encoding="utf-8")
    session_b.write_text(duplicated_payload, encoding="utf-8")
    old = time.time() - 8 * 3600
    os.utime(session_a, (old, old))
    os.utime(session_b, (old, old))

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=True,
        older_than_seconds=3600,
        dedupe_worktree_min_mb=1,
    )

    dedupe_manifest = result["worktree_dedupe"]
    assert dedupe_manifest["files_relinked"] == 1
    assert os.stat(session_a).st_ino == os.stat(session_b).st_ino


def test_runtime_storage_maintenance_dedupes_large_worktree_runtime_files(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    stdout_a = quest_root / ".ds" / "worktrees" / "wt-a" / ".ds" / "runs" / "run-001" / "stdout.jsonl"
    stdout_b = quest_root / ".ds" / "worktrees" / "wt-b" / ".ds" / "runs" / "run-001" / "stdout.jsonl"
    stdout_a.parent.mkdir(parents=True, exist_ok=True)
    stdout_b.parent.mkdir(parents=True, exist_ok=True)
    duplicated_payload = (json.dumps({"line": "x" * 1_500_000}, ensure_ascii=False) + "\n") * 2
    stdout_a.write_text(duplicated_payload, encoding="utf-8")
    stdout_b.write_text(duplicated_payload, encoding="utf-8")
    old = time.time() - 8 * 3600
    os.utime(stdout_a, (old, old))
    os.utime(stdout_b, (old, old))

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=True,
        older_than_seconds=3600,
        dedupe_worktree_min_mb=1,
    )

    dedupe_manifest = result["worktree_dedupe"]
    assert dedupe_manifest["files_relinked"] == 1
    assert os.stat(stdout_a).st_ino == os.stat(stdout_b).st_ino


def test_runtime_storage_maintenance_prunes_cold_unpinned_worktree_runtime_payloads(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    worktree_root = quest_root / ".ds" / "worktrees" / "wt-cold"
    runtime_dirs = [
        worktree_root / ".ds" / "bash_exec" / "bash-001",
        worktree_root / ".ds" / "runs" / "run-001",
        worktree_root / ".ds" / "codex_history" / "run-001",
        worktree_root / ".ds" / "codex_homes" / "run-001" / "sessions" / "2026" / "04",
        worktree_root / ".ds" / "slim_backups" / "2026-04-18T00-00-00Z",
    ]
    for path in runtime_dirs:
        path.mkdir(parents=True, exist_ok=True)
    (runtime_dirs[0] / "terminal.log").write_text("terminal\n", encoding="utf-8")
    (runtime_dirs[1] / "stdout.jsonl").write_text('{"line":"stdout"}\n', encoding="utf-8")
    (runtime_dirs[2] / "events.jsonl").write_text('{"event":{"type":"message"}}\n', encoding="utf-8")
    (runtime_dirs[3] / "rollout.jsonl").write_text('{"item":{"type":"message"}}\n', encoding="utf-8")
    (runtime_dirs[4] / "manifest.json").write_text('{"ok":true}\n', encoding="utf-8")
    artifact_path = worktree_root / "artifacts" / "reports" / "kept.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text('{"kept":true}\n', encoding="utf-8")
    (worktree_root / "brief.md").write_text("# kept\n", encoding="utf-8")
    old = time.time() - 8 * 3600
    for path in [
        worktree_root / ".ds" / "bash_exec",
        worktree_root / ".ds" / "runs",
        worktree_root / ".ds" / "codex_history",
        worktree_root / ".ds" / "codex_homes",
        worktree_root / ".ds" / "slim_backups",
    ]:
        for item in sorted(path.rglob("*"), reverse=True):
            os.utime(item, (old, old))
        os.utime(path, (old, old))

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=True,
        older_than_seconds=3600,
        dedupe_worktree_min_mb=None,
    )

    assert not (worktree_root / ".ds" / "bash_exec").exists()
    assert not (worktree_root / ".ds" / "runs").exists()
    assert not (worktree_root / ".ds" / "codex_history").exists()
    assert not (worktree_root / ".ds" / "codex_homes").exists()
    assert not (worktree_root / ".ds" / "slim_backups").exists()
    assert artifact_path.exists()
    assert (worktree_root / "brief.md").exists()
    prune_manifest = result["worktree_runtime_prune"]
    assert prune_manifest["worktrees_pruned"] == 1
    assert prune_manifest["directories_removed"] == 5


def test_runtime_storage_maintenance_keeps_pinned_worktree_runtime_payloads(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    worktree_root = quest_root / ".ds" / "worktrees" / "wt-pinned"
    runtime_root = worktree_root / ".ds" / "runs" / "run-001"
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "stdout.jsonl").write_text('{"line":"stdout"}\n', encoding="utf-8")
    (quest_root / ".ds").mkdir(parents=True, exist_ok=True)
    (quest_root / ".ds" / "research_state.json").write_text(
        json.dumps(
            {
                "current_workspace_root": str(worktree_root),
                "research_head_worktree_root": str(worktree_root),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    old = time.time() - 8 * 3600
    os.utime(runtime_root / "stdout.jsonl", (old, old))
    os.utime(worktree_root / ".ds" / "runs", (old, old))

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=True,
        older_than_seconds=3600,
        dedupe_worktree_min_mb=None,
    )

    assert (worktree_root / ".ds" / "runs").exists()
    prune_manifest = result["worktree_runtime_prune"]
    assert prune_manifest["worktrees_pruned"] == 0
    assert any(item["reason"] == "pinned" for item in prune_manifest["skipped"])
