from __future__ import annotations

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
    archived_log = bash_root / "log.full.jsonl.gz"
    assert archived_log.exists()
    with gzip.open(archived_log, "rt", encoding="utf-8") as handle:
        archived_lines = handle.read().splitlines()
    assert len(archived_lines) == 10

    compacted_terminal = (bash_root / "terminal.log").read_text(encoding="utf-8").splitlines()
    assert len(compacted_terminal) == 5
    assert any("compacted completed runtime log" in line for line in compacted_terminal)
    assert (bash_root / "terminal.full.log.gz").exists()
    assert not stale_tmp.exists()
    assert not codex_tmp.parent.exists()
    runtime_logs = result["roots"][0]["runtime_logs"]["compacted_files"]
    assert len(runtime_logs) == 2
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
    assert (bash_root / "terminal.full.log.gz").exists()
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
    assert (bash_root / "log.full.jsonl.gz").exists()
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
