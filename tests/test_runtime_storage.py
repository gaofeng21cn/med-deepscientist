from __future__ import annotations

from datetime import UTC, datetime, timedelta
import gzip
import json
import os
import sqlite3
import time
from pathlib import Path
import tarfile

from deepscientist.runtime_storage import maintain_quest_runtime_storage


def _mark_tree_old(path: Path, *, age_seconds: int = 8 * 3600) -> None:
    old = time.time() - age_seconds
    for item in sorted(path.rglob("*"), reverse=True):
        os.utime(item, (old, old))
    os.utime(path, (old, old))


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

    compacted_log = (bash_root / "log.compact.ndjson").read_text(encoding="utf-8").splitlines()
    assert len(compacted_log) == 5
    assert any("compacted completed runtime log" in line for line in compacted_log)
    archived_log = quest_root / ".ds" / "cold_archive" / "bash_exec" / ".ds" / "bash_exec" / "bash-001" / "log.jsonl.gz"
    assert archived_log.exists()
    assert not (bash_root / "log.jsonl").exists()
    assert not (bash_root / "log.full.jsonl.gz").exists()
    assert (bash_root / "log.jsonl.index.json").exists()
    with gzip.open(archived_log, "rt", encoding="utf-8") as handle:
        archived_lines = handle.read().splitlines()
    assert len(archived_lines) == 10

    compacted_terminal = (bash_root / "terminal.compact.log").read_text(encoding="utf-8").splitlines()
    assert len(compacted_terminal) == 5
    assert any("compacted completed runtime log" in line for line in compacted_terminal)
    assert (
        quest_root / ".ds" / "cold_archive" / "bash_exec" / ".ds" / "bash_exec" / "bash-001" / "terminal.log.gz"
    ).exists()
    assert not (bash_root / "terminal.log").exists()
    assert not (bash_root / "terminal.full.log.gz").exists()
    assert (bash_root / "terminal.log.index.json").exists()
    assert not stale_tmp.exists()
    assert not codex_tmp.parent.exists()
    assert not codex_execve_tmp.parent.parent.parent.exists()
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert len(runtime_logs) == 2
    cold_archive = result["roots"][0]["cold_archive"]
    assert cold_archive["moved_file_count"] == 2
    assert cold_archive["moved_by_kind"]["bash_exec_session_log"] == 2
    gitignore_text = (quest_root / ".gitignore").read_text(encoding="utf-8")
    assert ".ds/**/*.tmp" in gitignore_text
    assert ".ds/bash_exec/" in gitignore_text
    assert ".ds/codex_history/" in gitignore_text
    assert ".ds/codex_homes/" in gitignore_text
    assert ".ds/runs/" in gitignore_text


def test_runtime_storage_maintenance_updates_sqlite_sidecar_index(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    bash_root = quest_root / ".ds" / "bash_exec" / "bash-indexed"
    bash_root.mkdir(parents=True, exist_ok=True)
    (bash_root / "meta.json").write_text(
        json.dumps(
            {
                "bash_id": "bash-indexed",
                "status": "terminated",
                "finished_at": "2026-04-10T00:00:00+00:00",
                "updated_at": "2026-04-10T00:00:00+00:00",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (bash_root / "terminal.log").write_text("terminal\n" * 10, encoding="utf-8")
    reports_root = quest_root / "artifacts" / "reports" / "runtime_events"
    reports_root.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    for name, age_hours in (
        ("20260419T010000Z_runtime_state_observed.json", 120),
        ("20260419T020000Z_runtime_state_observed.json", 120),
    ):
        path = reports_root / name
        path.write_text(json.dumps({"name": name}, ensure_ascii=False) + "\n", encoding="utf-8")
        timestamp = (now - timedelta(hours=age_hours)).timestamp()
        os.utime(path, (timestamp, timestamp))
    worktree_runtime = quest_root / ".ds" / "worktrees" / "wt-indexed" / ".ds" / "runs" / "run-001"
    worktree_runtime.mkdir(parents=True, exist_ok=True)
    (worktree_runtime / "stdout.jsonl").write_text('{"line":"stdout"}\n', encoding="utf-8")
    _mark_tree_old(quest_root / ".ds" / "worktrees" / "wt-indexed")

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=True,
        older_than_seconds=3600,
        text_max_mb=1,
        dedupe_worktree_min_mb=None,
    )

    runtime_index = result["runtime_index"]
    db_path = Path(runtime_index["db_path"])
    assert db_path == quest_root.resolve() / ".ds" / "runtime_index.sqlite"
    assert runtime_index["schema_version"] == 1
    assert runtime_index["status"] == "updated"
    assert ".ds/cold_archive" in runtime_index["indexed_buckets"]
    assert "artifacts/reports" in runtime_index["indexed_buckets"]

    with sqlite3.connect(db_path) as connection:
        schema_version = connection.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
        assert schema_version == ("1",)
        run = connection.execute(
            """
            SELECT include_worktrees, root_count, worktrees_pruned, files_archived
            FROM maintenance_runs
            WHERE run_id = ?
            """,
            (runtime_index["run_id"],),
        ).fetchone()
        assert run == (1, 2, 1, 1)
        cold_archive_bucket = connection.execute(
            """
            SELECT file_count, bytes_total, exists_on_disk
            FROM bucket_snapshots
            WHERE run_id = ? AND bucket = '.ds/cold_archive'
            """,
            (runtime_index["run_id"],),
        ).fetchone()
        assert cold_archive_bucket is not None
        assert cold_archive_bucket[0] > 0
        assert cold_archive_bucket[1] > 0
        assert cold_archive_bucket[2] == 1
        refs = connection.execute(
            """
            SELECT kind, source_path, archive_ref, restore_index_ref, ledger_ref
            FROM archive_refs
            WHERE run_id = ?
            ORDER BY kind, source_path
            """,
            (runtime_index["run_id"],),
        ).fetchall()
    kinds = {row[0] for row in refs}
    assert "bash_exec_session_log" in kinds
    assert "report_history_retention" in kinds
    assert "worktree_runtime_payload" in kinds
    assert any(row[3] == result["worktree_runtime_prune"]["restore_index_ref"] for row in refs)
    assert any(row[4] == result["roots"][0]["report_history_retention"]["ledger_ref"] for row in refs)


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

    compacted_terminal = (bash_root / "terminal.compact.log").read_text(encoding="utf-8")
    assert "compacted completed runtime log" in compacted_terminal
    assert (
        quest_root / ".ds" / "cold_archive" / "bash_exec" / ".ds" / "bash_exec" / "bash-002" / "terminal.log.gz"
    ).exists()
    assert not (bash_root / "terminal.log").exists()
    assert not (bash_root / "terminal.full.log.gz").exists()
    assert (bash_root / "terminal.compact.log").stat().st_size < 1_000_000
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert len(runtime_logs) == 1


def test_runtime_storage_maintenance_falls_back_to_byte_windows_for_multiline_huge_terminal_logs(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    bash_root = quest_root / ".ds" / "bash_exec" / "bash-002b"
    bash_root.mkdir(parents=True, exist_ok=True)
    (quest_root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    meta = {
        "bash_id": "bash-002b",
        "status": "terminated",
        "finished_at": "2026-04-10T00:00:00+00:00",
        "updated_at": "2026-04-10T00:00:00+00:00",
    }
    (bash_root / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    huge_line = "terminal:" + ("x" * 1_500_000)
    lines = [huge_line, "line-1", "line-2", "line-3", "tail-0", "tail-1", "tail-2", "tail-3"]
    (bash_root / "terminal.log").write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=False,
        older_than_seconds=3600,
        jsonl_max_mb=1,
        text_max_mb=1,
        head_lines=2,
        tail_lines=2,
    )

    compacted_terminal = (bash_root / "terminal.compact.log").read_text(encoding="utf-8")
    assert "compacted completed runtime log" in compacted_terminal
    assert (bash_root / "terminal.compact.log").stat().st_size < 1_000_000
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert len(runtime_logs) == 1
    assert runtime_logs[0]["mode"] == "text_head_tail_bytes"


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

    compacted_log = (bash_root / "log.compact.ndjson").read_text(encoding="utf-8")
    assert "compacted completed runtime log" in compacted_log
    assert (
        quest_root / ".ds" / "cold_archive" / "bash_exec" / ".ds" / "bash_exec" / "bash-003" / "log.jsonl.gz"
    ).exists()
    assert not (bash_root / "log.jsonl").exists()
    assert not (bash_root / "log.full.jsonl.gz").exists()
    assert (bash_root / "log.compact.ndjson").stat().st_size < 1_000_000
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

    compacted_terminal = (bash_root / "terminal.compact.log").read_text(encoding="utf-8")
    assert "compacted completed runtime log" in compacted_terminal
    assert not (bash_root / "terminal.log").exists()
    assert (bash_root / "terminal.log.index.json").exists()
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
    assert cold_archive["moved_by_kind"]["codex_session_jsonl"] == 1
    assert any(item["kind"] == "codex_session_jsonl" for item in cold_archive["moved_samples"])


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
    assert manifest["kept_file_count"] == 4
    assert "archived_files" not in manifest
    assert "kept_files" not in manifest
    assert manifest["ledger_ref"]
    ledger_path = quest_root / manifest["ledger_ref"]
    assert ledger_path.exists()
    with gzip.open(ledger_path, "rt", encoding="utf-8") as handle:
        ledger = json.load(handle)
    assert len(ledger["archived_files"]) == 2
    assert len(ledger["kept_files"]) == 4


def test_runtime_storage_maintenance_retains_inactive_codex_home_payloads(tmp_path: Path) -> None:
    quest_root = tmp_path / "quest"
    run_id = "run-cold-home-001"
    history_root = quest_root / ".ds" / "codex_history" / run_id
    run_home = quest_root / ".ds" / "codex_homes" / run_id
    session_path = run_home / "sessions" / "2026" / "04" / "15" / "rollout.jsonl"
    history_root.mkdir(parents=True, exist_ok=True)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    (run_home / "config.toml").write_text("model = 'gpt-5.4'\n", encoding="utf-8")
    (run_home / "auth.json").write_text('{"token":"abc"}\n', encoding="utf-8")
    (run_home / "logs_1.sqlite").write_text("sqlite-log\n", encoding="utf-8")
    (run_home / "state_1.sqlite").write_text("sqlite-state\n", encoding="utf-8")
    (run_home / "skills" / "demo" / "SKILL.md").parent.mkdir(parents=True, exist_ok=True)
    (run_home / "skills" / "demo" / "SKILL.md").write_text("# demo\n", encoding="utf-8")
    (run_home / "memories" / "note.txt").parent.mkdir(parents=True, exist_ok=True)
    (run_home / "memories" / "note.txt").write_text("memory\n", encoding="utf-8")
    session_path.write_text(
        "\n".join(
            json.dumps({"seq": index + 1, "item": {"type": "message", "text": f"line-{index}"}}, ensure_ascii=False)
            for index in range(4)
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
        jsonl_max_mb=8,
        text_max_mb=8,
        head_lines=2,
        tail_lines=2,
    )

    assert (run_home / "config.toml").exists()
    assert not (run_home / "auth.json").exists()
    assert not (run_home / "logs_1.sqlite").exists()
    assert not (run_home / "state_1.sqlite").exists()
    assert not (run_home / "skills").exists()
    assert not (run_home / "memories").exists()
    assert (run_home / "sessions" / "2026" / "04" / "15" / "rollout.compact.ndjson").exists()
    assert (run_home / "sessions" / "2026" / "04" / "15" / "rollout.jsonl.index.json").exists()
    run_manifest_path = run_home / "runtime_retention.index.json"
    assert run_manifest_path.exists()
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    assert run_manifest["run_id"] == run_id
    assert "config.toml" in run_manifest["retained_items"]
    cold_archive = result["roots"][0]["cold_archive"]
    assert cold_archive["moved_by_kind"]["codex_home_payload"] >= 5
    assert any(item["kind"] == "codex_home_payload" for item in cold_archive["moved_samples"])
    auth_archive = quest_root / ".ds" / "cold_archive" / "codex_home_runs" / ".ds" / "codex_homes" / run_id / "auth.json.gz"
    skills_archive = quest_root / ".ds" / "cold_archive" / "codex_home_runs" / ".ds" / "codex_homes" / run_id / "skills.tar.gz"
    assert auth_archive.exists()
    assert skills_archive.exists()
    with gzip.open(auth_archive, "rt", encoding="utf-8") as handle:
        assert "abc" in handle.read()
    with tarfile.open(skills_archive, "r:gz") as archive:
        assert any(member.name.endswith("SKILL.md") for member in archive.getmembers())


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
    assert prune_manifest["directories_archived"] == 5
    assert prune_manifest["directories_removed"] == 5
    assert prune_manifest["files_archived"] == 5
    assert prune_manifest["bytes_original"] > 0
    assert prune_manifest["bytes_archived"] > 0
    restore_index = quest_root / prune_manifest["restore_index_ref"]
    assert restore_index.exists()
    restore_payload = json.loads(restore_index.read_text(encoding="utf-8"))
    assert len(restore_payload["archives"]) == 5
    archived_by_source = {
        item["source_path"]: item
        for item in prune_manifest["removed"][0]["archived_directories"]
    }
    bash_archive = archived_by_source[".ds/worktrees/wt-cold/.ds/bash_exec"]
    assert bash_archive["archive_sha256"]
    assert bash_archive["restore_command"].startswith("tar -xzf .ds/cold_archive/worktree_runtime_payloads/")
    assert len(bash_archive["file_manifest"]) == 1
    bash_file = bash_archive["file_manifest"][0]
    assert bash_file["path"] == ".ds/worktrees/wt-cold/.ds/bash_exec/bash-001/terminal.log"
    assert bash_file["bytes"] == len("terminal\n".encode("utf-8"))
    assert bash_file["sha256"]
    archive_path = quest_root / bash_archive["archive_ref"]
    assert archive_path.exists()
    with tarfile.open(archive_path, "r:gz") as archive:
        names = archive.getnames()
        assert ".ds/worktrees/wt-cold/.ds/bash_exec/bash-001/terminal.log" in names
        member = archive.extractfile(".ds/worktrees/wt-cold/.ds/bash_exec/bash-001/terminal.log")
        assert member is not None
        assert member.read().decode("utf-8") == "terminal\n"


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


def test_runtime_storage_maintenance_archives_cold_unpinned_expanded_worktree_without_runtime_payloads(
    tmp_path: Path,
) -> None:
    quest_root = tmp_path / "quest"
    worktree_root = quest_root / ".ds" / "worktrees" / "analysis-old"
    source_path = worktree_root / "src" / "analysis.py"
    manuscript_path = worktree_root / "paper" / "paper" / "manuscript.md"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    manuscript_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("print('analysis')\n", encoding="utf-8")
    manuscript_path.write_text("# archived manuscript draft\n", encoding="utf-8")
    root_artifact = quest_root / "artifacts" / "reports" / "kept.json"
    root_dataset = quest_root / "datasets" / "manifest.json"
    root_manuscript = quest_root / "manuscript" / "paper.md"
    root_artifact.parent.mkdir(parents=True, exist_ok=True)
    root_dataset.parent.mkdir(parents=True, exist_ok=True)
    root_manuscript.parent.mkdir(parents=True, exist_ok=True)
    root_artifact.write_text('{"kept":true}\n', encoding="utf-8")
    root_dataset.write_text('{"dataset":"kept"}\n', encoding="utf-8")
    root_manuscript.write_text("# kept root manuscript\n", encoding="utf-8")
    _mark_tree_old(worktree_root)

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=True,
        older_than_seconds=3600,
        dedupe_worktree_min_mb=None,
    )

    assert not worktree_root.exists()
    assert root_artifact.exists()
    assert root_dataset.exists()
    assert root_manuscript.exists()
    prune_manifest = result["worktree_runtime_prune"]
    assert prune_manifest["worktrees_pruned"] == 1
    assert prune_manifest["expanded_worktrees_archived"] == 1
    assert prune_manifest["expanded_worktrees_removed"] == 1
    assert prune_manifest["files_archived"] == 2
    archived_worktree = prune_manifest["removed"][0]["archived_worktree"]
    assert archived_worktree["kind"] == "worktree_expanded_checkout"
    assert archived_worktree["source_path"] == ".ds/worktrees/analysis-old"
    assert archived_worktree["archive_sha256"]
    assert archived_worktree["restore_command"].startswith("tar -xzf .ds/cold_archive/worktree_runtime_payloads/")
    assert {item["path"] for item in archived_worktree["file_manifest"]} == {
        ".ds/worktrees/analysis-old/paper/paper/manuscript.md",
        ".ds/worktrees/analysis-old/src/analysis.py",
    }
    restore_index = quest_root / prune_manifest["restore_index_ref"]
    restore_payload = json.loads(restore_index.read_text(encoding="utf-8"))
    assert restore_payload["archives"][-1]["source_path"] == ".ds/worktrees/analysis-old"
    archive_path = quest_root / archived_worktree["archive_ref"]
    with tarfile.open(archive_path, "r:gz") as archive:
        names = archive.getnames()
        assert ".ds/worktrees/analysis-old/src/analysis.py" in names
        assert ".ds/worktrees/analysis-old/paper/paper/manuscript.md" in names


def test_runtime_storage_maintenance_keeps_pinned_and_recent_expanded_worktrees_without_runtime_payloads(
    tmp_path: Path,
) -> None:
    quest_root = tmp_path / "quest"
    pinned_root = quest_root / ".ds" / "worktrees" / "paper-active"
    recent_root = quest_root / ".ds" / "worktrees" / "analysis-recent"
    (pinned_root / "paper" / "draft.md").parent.mkdir(parents=True, exist_ok=True)
    (recent_root / "src").mkdir(parents=True, exist_ok=True)
    (pinned_root / "paper" / "draft.md").write_text("# active\n", encoding="utf-8")
    (recent_root / "src" / "analysis.py").write_text("print('recent')\n", encoding="utf-8")
    (quest_root / ".ds").mkdir(parents=True, exist_ok=True)
    (quest_root / ".ds" / "research_state.json").write_text(
        json.dumps(
            {
                "current_workspace_root": str(pinned_root),
                "research_head_worktree_root": str(pinned_root),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _mark_tree_old(pinned_root)

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=True,
        older_than_seconds=3600,
        dedupe_worktree_min_mb=None,
    )

    assert pinned_root.exists()
    assert recent_root.exists()
    prune_manifest = result["worktree_runtime_prune"]
    assert prune_manifest["worktrees_pruned"] == 0
    skip_reasons = {item["worktree_root"]: item["reason"] for item in prune_manifest["skipped"]}
    assert skip_reasons[".ds/worktrees/paper-active"] == "pinned"
    assert skip_reasons[".ds/worktrees/analysis-recent"] == "recent_worktree"


def test_runtime_storage_maintenance_ignores_generated_metadata_when_pruning_expanded_worktree(
    tmp_path: Path,
) -> None:
    quest_root = tmp_path / "quest"
    worktree_root = quest_root / ".ds" / "worktrees" / "analysis-generated-metadata"
    source_path = worktree_root / "src" / "analysis.py"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("print('old content')\n", encoding="utf-8")
    generated_paths = [
        worktree_root / ".ds" / "events" / "manifest.json",
        worktree_root / ".codex" / "skills" / "medical-research-scout" / "SKILL.md",
        worktree_root / "artifacts" / "reports" / "retention_manifest.json",
        worktree_root / "src" / "__pycache__" / "analysis.cpython-312.pyc",
    ]
    for path in generated_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated\n", encoding="utf-8")
    _mark_tree_old(worktree_root)
    now = time.time()
    for path in generated_paths:
        os.utime(path, (now, now))
        os.utime(path.parent, (now, now))

    result = maintain_quest_runtime_storage(
        quest_root,
        include_worktrees=True,
        older_than_seconds=3600,
        dedupe_worktree_min_mb=None,
    )

    assert not worktree_root.exists()
    prune_manifest = result["worktree_runtime_prune"]
    assert prune_manifest["expanded_worktrees_removed"] == 1
    archived_worktree = prune_manifest["removed"][0]["archived_worktree"]
    assert archived_worktree["kind"] == "worktree_expanded_checkout"
