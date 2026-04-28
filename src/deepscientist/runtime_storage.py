from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import tarfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .quest.layout import RUNTIME_GITIGNORE_ENTRIES
from .shared import ensure_dir, read_json, utc_now, write_json

TERMINAL_STATUSES = {"completed", "failed", "terminated"}
_ATOMIC_TMP_RE = re.compile(r"^(?P<base>.+)\.[A-Za-z0-9_-]{8,}\.tmp$")
_SEQ_RE = re.compile(r'"seq"\s*:\s*(\d+)')
_EVENT_ID_BYTES_RE = re.compile(rb'"event_id"\s*:\s*"([^"]+)"')
_EVENT_TYPE_BYTES_RE = re.compile(rb'"(?:type|event_type)"\s*:\s*"([^"]+)"')
_RUN_ID_BYTES_RE = re.compile(rb'"run_id"\s*:\s*"([^"]+)"')
_TOOL_NAME_BYTES_RE = re.compile(rb'"tool_name"\s*:\s*"([^"]+)"')
_TIMESTAMP_BYTES_RE = re.compile(rb'"timestamp"\s*:\s*"([^"]+)"')
_SEQ_BYTES_RE = re.compile(rb'"seq"\s*:\s*(\d+)')
_STREAM_BYTES_RE = re.compile(rb'"stream"\s*:\s*"([^"]+)"')
_PINNED_WORKTREE_STATE_KEYS = (
    "current_workspace_root",
    "research_head_worktree_root",
    "analysis_parent_worktree_root",
    "paper_parent_worktree_root",
)
_WORKTREE_RUNTIME_DIR_NAMES = (
    "bash_exec",
    "runs",
    "codex_history",
    "codex_homes",
    "slim_backups",
)
_REPORT_RETENTION_KEEP_FILENAMES = {
    "latest.json",
    "state.json",
    "retention_manifest.json",
    "retention_manifest.ledger.json.gz",
}
_REPORT_RETENTION_RECENT_HOURLY_WINDOW_HOURS = 72
_REPORT_RETENTION_OLDER_SAMPLING = "daily"
_MANIFEST_SAMPLE_LIMIT = 20
_CODEX_HOME_RETENTION_KEEP_NAMES = {"config.toml", "runtime_retention.index.json", "sessions"}
_BASH_SESSION_LOG_SPECS = (
    ("log.jsonl", "jsonl"),
    ("terminal.log", "text"),
    ("monitor.log", "text"),
)
_COMPACT_TEXT_WINDOW_MAX_BYTES = 512 * 1024


def _parse_timestamp(value: object) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _age_seconds(path: Path, *, now: datetime) -> float | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
    return max(0.0, (now - modified).total_seconds())


def _session_is_cold_terminal(meta: dict[str, Any], *, now: datetime, older_than_seconds: int) -> bool:
    status = str((meta or {}).get("status") or "").strip().lower()
    finished_at = _parse_timestamp((meta or {}).get("finished_at") or (meta or {}).get("updated_at"))
    if finished_at is not None and (now - finished_at).total_seconds() < older_than_seconds:
        return False
    if status in TERMINAL_STATUSES:
        return True
    return finished_at is not None


def iter_managed_roots(quest_root: Path) -> list[Path]:
    resolved_quest_root = Path(quest_root).expanduser().resolve()
    roots = [resolved_quest_root]
    worktrees_root = resolved_quest_root / ".ds" / "worktrees"
    if worktrees_root.exists():
        roots.extend(sorted(path.resolve() for path in worktrees_root.iterdir() if path.is_dir()))
    return roots


def _pinned_worktree_roots(quest_root: Path) -> set[Path]:
    resolved_quest_root = Path(quest_root).expanduser().resolve()
    worktrees_root = resolved_quest_root / ".ds" / "worktrees"
    if not worktrees_root.exists():
        return set()
    payload = read_json(resolved_quest_root / ".ds" / "research_state.json", {})
    if not isinstance(payload, dict):
        return set()
    pinned: set[Path] = set()
    for key in _PINNED_WORKTREE_STATE_KEYS:
        raw = str(payload.get(key) or "").strip()
        if not raw:
            continue
        candidate = Path(raw).expanduser().resolve(strict=False)
        try:
            candidate.relative_to(worktrees_root)
        except ValueError:
            continue
        pinned.add(candidate)
    return pinned


def _path_tree_is_cold(path: Path, *, now: datetime, older_than_seconds: int) -> bool:
    cutoff = now.timestamp() - max(0, older_than_seconds)
    for current_root, _, filenames in os.walk(path):
        current = Path(current_root)
        try:
            current_stat = current.stat()
        except OSError:
            continue
        if current_stat.st_mtime > cutoff:
            return False
        for filename in filenames:
            candidate = current / filename
            try:
                if candidate.stat().st_mtime > cutoff:
                    return False
            except OSError:
                continue
    return True


def prune_cold_worktree_runtime_payloads(
    quest_root: Path,
    *,
    older_than_seconds: int = 6 * 3600,
) -> dict[str, Any]:
    resolved_root = Path(quest_root).expanduser().resolve()
    worktrees_root = resolved_root / ".ds" / "worktrees"
    pinned_roots = _pinned_worktree_roots(resolved_root)
    manifest: dict[str, Any] = {
        "quest_root": str(resolved_root),
        "worktrees_root": str(worktrees_root),
        "older_than_seconds": max(0, older_than_seconds),
        "pinned_worktrees": sorted(str(path) for path in pinned_roots),
        "worktrees_examined": 0,
        "worktrees_pruned": 0,
        "directories_archived": 0,
        "directories_removed": 0,
        "bytes_original": 0,
        "bytes_archived": 0,
        "files_archived": 0,
        "restore_index_ref": None,
        "archive_kind": "worktree_runtime_payloads",
        "removed": [],
        "skipped": [],
    }
    if not worktrees_root.exists():
        return manifest

    now = datetime.now(UTC)
    for worktree_root in sorted(path for path in worktrees_root.iterdir() if path.is_dir()):
        resolved_worktree = worktree_root.resolve(strict=False)
        manifest["worktrees_examined"] += 1
        if resolved_worktree in pinned_roots:
            manifest["skipped"].append(
                {
                    "worktree_root": str(worktree_root.relative_to(resolved_root)),
                    "reason": "pinned",
                }
            )
            continue
        runtime_dirs = [
            worktree_root / ".ds" / directory_name
            for directory_name in _WORKTREE_RUNTIME_DIR_NAMES
            if (worktree_root / ".ds" / directory_name).exists()
        ]
        if not runtime_dirs:
            manifest["skipped"].append(
                {
                    "worktree_root": str(worktree_root.relative_to(resolved_root)),
                    "reason": "no_runtime_payloads",
                }
            )
            continue
        if any(not _path_tree_is_cold(path, now=now, older_than_seconds=older_than_seconds) for path in runtime_dirs):
            manifest["skipped"].append(
                {
                    "worktree_root": str(worktree_root.relative_to(resolved_root)),
                    "reason": "recent_runtime_payloads",
                }
            )
            continue
        archived_directories: list[dict[str, Any]] = []
        for runtime_dir in runtime_dirs:
            relative_dir = _relative_ref(runtime_dir, root=resolved_root)
            archive_path = _cold_archive_path(
                resolved_root,
                kind="worktree_runtime_payloads",
                relative_path=f"{relative_dir}.tar.gz",
                compress=False,
            )
            content_manifest = _directory_file_manifest(runtime_dir, root=resolved_root)
            _archive_directory_tree_as_tar_gz(runtime_dir, archive_path, arcname=relative_dir)
            try:
                archive_bytes = archive_path.stat().st_size
            except OSError:
                archive_bytes = 0
            archive_ref = _relative_ref(archive_path, root=resolved_root)
            archive_entry = {
                "schema_version": 1,
                "kind": "worktree_runtime_payload",
                "worktree_root": _relative_ref(worktree_root, root=resolved_root),
                "source_path": relative_dir,
                "archive_ref": archive_ref,
                "archive_sha256": _sha256(archive_path),
                "archive_bytes": archive_bytes,
                "bytes_original": content_manifest["bytes_original"],
                "file_count": content_manifest["file_count"],
                "file_manifest": content_manifest["files"],
                "archived_at": utc_now(),
                "restore_command": f"tar -xzf {archive_ref} -C {resolved_root}",
            }
            archived_directories.append(archive_entry)
            shutil.rmtree(runtime_dir, ignore_errors=True)
        manifest["worktrees_pruned"] += 1
        manifest["directories_archived"] += len(archived_directories)
        manifest["directories_removed"] += len(archived_directories)
        manifest["bytes_original"] += sum(int(item.get("bytes_original") or 0) for item in archived_directories)
        manifest["bytes_archived"] += sum(int(item.get("archive_bytes") or 0) for item in archived_directories)
        manifest["files_archived"] += sum(int(item.get("file_count") or 0) for item in archived_directories)
        if archived_directories:
            manifest["restore_index_ref"] = _append_worktree_runtime_restore_index(
                resolved_root,
                entries=archived_directories,
            )
        manifest["removed"].append(
            {
                "worktree_root": str(worktree_root.relative_to(resolved_root)),
                "directories": [str(item["source_path"]) for item in archived_directories],
                "archived_directories": archived_directories,
            }
        )
    return manifest


def _archive_path(path: Path) -> Path:
    suffixes = "".join(path.suffixes)
    base = path.name[: -len(suffixes)] if suffixes else path.name
    return path.with_name(f"{base}.full{suffixes}.gz")


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 10_000):
        candidate = path.with_name(f"{stem}.{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"unable to allocate unique archive path for {path}")


def _manifest_ledger_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}.ledger.json.gz")


def _compact_view_path(path: Path) -> Path:
    if path.suffix == ".jsonl":
        return path.with_name(f"{path.stem}.compact.ndjson")
    return path.with_name(f"{path.stem}.compact{path.suffix}")


def _relative_ref(path: Path, *, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _cold_archive_path(
    root: Path,
    *,
    kind: str,
    relative_path: str,
    compress: bool = False,
) -> Path:
    normalized_relative = Path(*Path(relative_path).parts)
    target = root / ".ds" / "cold_archive" / kind / normalized_relative
    if compress and target.suffix != ".gz":
        suffixes = "".join(target.suffixes)
        base = target.name[: -len(suffixes)] if suffixes else target.name
        target = target.with_name(f"{base}{suffixes}.gz")
    ensure_dir(target.parent)
    return _unique_path(target)


def _write_json_index(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    write_json(path, payload)


def _write_gzip_copy(source: Path, archive_path: Path) -> None:
    ensure_dir(archive_path.parent)
    with source.open("rb") as input_handle, gzip.open(archive_path, "wb", compresslevel=6) as output_handle:
        shutil.copyfileobj(input_handle, output_handle)


def _write_gzip_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _archive_directory_as_tar_gz(source_dir: Path, archive_path: Path) -> None:
    ensure_dir(archive_path.parent)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(source_dir, arcname=source_dir.name)


def _archive_directory_tree_as_tar_gz(source_dir: Path, archive_path: Path, *, arcname: str) -> None:
    ensure_dir(archive_path.parent)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(source_dir, arcname=arcname)


def _directory_file_manifest(source_dir: Path, *, root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total_bytes = 0
    for path in sorted(item for item in source_dir.rglob("*") if item.is_file()):
        try:
            file_bytes = path.stat().st_size
            digest = _sha256(path)
        except OSError:
            continue
        total_bytes += file_bytes
        files.append(
            {
                "path": _relative_ref(path, root=root),
                "bytes": file_bytes,
                "sha256": digest,
            }
        )
    return {
        "file_count": len(files),
        "bytes_original": total_bytes,
        "files": files,
    }


def _append_worktree_runtime_restore_index(
    root: Path,
    *,
    entries: list[dict[str, Any]],
) -> str:
    index_path = root / ".ds" / "cold_archive" / "worktree_runtime_payloads" / "restore_index.json"
    payload = read_json(index_path, {})
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        payload = {
            "schema_version": 1,
            "quest_root": str(root),
            "index_path": _relative_ref(index_path, root=root),
            "archives": [],
        }
    archives = payload.get("archives")
    if not isinstance(archives, list):
        archives = []
    archives.extend(entries)
    payload["archives"] = archives
    payload["updated_at"] = utc_now()
    write_json(index_path, payload)
    return _relative_ref(index_path, root=root)


def _collect_line_windows(path: Path, *, head_lines: int, tail_lines: int) -> tuple[list[str], list[str], int]:
    head: list[str] = []
    tail: deque[str] = deque(maxlen=max(1, tail_lines))
    total = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            total += 1
            if total <= head_lines:
                head.append(line)
            tail.append(line)
    return head, list(tail), total


def _line_window_bytes(*segments: str) -> int:
    return sum(len(segment.encode("utf-8")) + 1 for segment in segments)


def _collect_byte_windows(path: Path, *, head_bytes: int, tail_bytes: int) -> tuple[str, str, int]:
    try:
        original_bytes = path.stat().st_size
    except OSError:
        return "", "", 0
    if original_bytes <= 0:
        return "", "", original_bytes

    normalized_head_bytes = max(1, head_bytes)
    normalized_tail_bytes = max(1, tail_bytes)
    with path.open("rb") as handle:
        head = handle.read(min(original_bytes, normalized_head_bytes))
        if original_bytes > len(head):
            tail_size = min(normalized_tail_bytes, max(original_bytes - len(head), 0))
            if tail_size > 0:
                handle.seek(-tail_size, 2)
                tail = handle.read(tail_size)
            else:
                tail = b""
        else:
            tail = b""
    return (
        head.decode("utf-8", errors="replace"),
        tail.decode("utf-8", errors="replace"),
        original_bytes,
    )


def _extract_seq(raw_line: str) -> int | None:
    match = _SEQ_RE.search(raw_line)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _extract_bytes(pattern: re.Pattern[bytes], raw: bytes) -> str | None:
    match = pattern.search(raw)
    if match is None:
        return None
    try:
        return match.group(1).decode("utf-8", errors="ignore").strip() or None
    except Exception:
        return None


def _truncate_leaf_text(text: str, *, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    head = max(limit // 2, 128)
    tail = max(limit - head - 32, 64)
    omitted = max(len(text) - head - tail, 0)
    return f"{text[:head]}...[truncated {omitted} chars]...{text[-tail:]}"


def _truncate_structured_value(value: object, *, string_limit: int) -> object:
    if isinstance(value, str):
        return _truncate_leaf_text(value, limit=string_limit)
    if isinstance(value, list):
        return [_truncate_structured_value(item, string_limit=string_limit) for item in value[:100]]
    if isinstance(value, dict):
        truncated: dict[object, object] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 100:
                truncated["__truncated__"] = f"truncated remaining {len(value) - 100} item(s)"
                break
            truncated[key] = _truncate_structured_value(item, string_limit=string_limit)
        return truncated
    return value


def _preview_jsonl_line(raw_line: str, *, string_limit: int = 32 * 1024) -> str:
    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError:
        return _truncate_leaf_text(raw_line, limit=string_limit)
    preview = _truncate_structured_value(payload, string_limit=string_limit)
    return json.dumps(preview, ensure_ascii=False)


def _compact_jsonl_file(
    path: Path,
    *,
    archive_path: Path,
    original_bytes: int,
    head_lines: int,
    tail_lines: int,
    root: Path,
    destination_path: Path | None = None,
) -> dict[str, Any] | None:
    output_path = destination_path or path
    head, tail, total_lines = _collect_line_windows(path, head_lines=head_lines, tail_lines=tail_lines)
    head_last_seq = _extract_seq(head[-1]) if head else None
    tail_first_seq = _extract_seq(tail[0]) if tail else None
    marker_seq = (head_last_seq + 1) if head_last_seq is not None else 1
    if tail_first_seq is not None and marker_seq >= tail_first_seq:
        marker_seq = max(1, tail_first_seq - 1)
    if total_lines > head_lines + tail_lines:
        omitted_lines = max(0, total_lines - len(head) - len(tail))
        marker = {
            "seq": marker_seq,
            "stream": "system",
            "line": (
                f"[compacted completed runtime log: omitted {omitted_lines} lines; "
                f"full log archived at {archive_path.relative_to(root).as_posix()}]"
            ),
            "timestamp": utc_now(),
            "compacted_log": True,
            "omitted_line_count": omitted_lines,
            "original_bytes": original_bytes,
            "archive_ref": archive_path.relative_to(root).as_posix(),
        }
        rewritten = [*head, json.dumps(marker, ensure_ascii=False), *tail]
        output_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
        return {
            "path": str(path.relative_to(root)),
            "compact_view_path": str(output_path.relative_to(root)),
            "archive_path": str(archive_path.relative_to(root)),
            "original_bytes": original_bytes,
            "omitted_line_count": omitted_lines,
            "mode": "jsonl_head_tail",
        }

    preview_head_count = max(total_lines - len(tail), 0)
    preview_lines = [*head[:preview_head_count], *tail]
    rewritten_preview = [_preview_jsonl_line(line) for line in preview_lines]
    omitted_bytes = max(
        0,
        original_bytes - sum(len(line.encode("utf-8")) + 1 for line in rewritten_preview),
    )
    if omitted_bytes <= 0:
        if destination_path is not None:
            ensure_dir(output_path.parent)
            shutil.copy2(path, output_path)
            return {
                "path": str(path.relative_to(root)),
                "compact_view_path": str(output_path.relative_to(root)),
                "archive_path": str(archive_path.relative_to(root)),
                "original_bytes": original_bytes,
                "mode": "jsonl_copy",
            }
        return None
    marker = {
        "seq": marker_seq,
        "stream": "system",
        "line": (
            f"[compacted completed runtime log: omitted {omitted_bytes} bytes; "
            f"full log archived at {archive_path.relative_to(root).as_posix()}]"
        ),
        "timestamp": utc_now(),
        "compacted_log": True,
        "omitted_byte_count": omitted_bytes,
        "original_bytes": original_bytes,
        "archive_ref": archive_path.relative_to(root).as_posix(),
    }
    midpoint = max(len(rewritten_preview) // 2, 0)
    rewritten = [
        *rewritten_preview[:midpoint],
        json.dumps(marker, ensure_ascii=False),
        *rewritten_preview[midpoint:],
    ]
    output_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
    return {
        "path": str(path.relative_to(root)),
        "compact_view_path": str(output_path.relative_to(root)),
        "archive_path": str(archive_path.relative_to(root)),
        "original_bytes": original_bytes,
        "omitted_byte_count": omitted_bytes,
        "mode": "jsonl_preview",
    }


def _compact_text_file(
    path: Path,
    *,
    archive_path: Path,
    original_bytes: int,
    head_lines: int,
    tail_lines: int,
    root: Path,
    destination_path: Path | None = None,
) -> dict[str, Any] | None:
    output_path = destination_path or path
    head, tail, total_lines = _collect_line_windows(path, head_lines=head_lines, tail_lines=tail_lines)
    if total_lines > head_lines + tail_lines and _line_window_bytes(*head, *tail) <= _COMPACT_TEXT_WINDOW_MAX_BYTES:
        omitted_lines = max(0, total_lines - len(head) - len(tail))
        marker = (
            f"[compacted completed runtime log: omitted {omitted_lines} lines; "
            f"full log archived at {archive_path.relative_to(root).as_posix()}]"
        )
        rewritten = [*head, marker, *tail]
        output_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
        return {
            "path": str(path.relative_to(root)),
            "compact_view_path": str(output_path.relative_to(root)),
            "archive_path": str(archive_path.relative_to(root)),
            "original_bytes": original_bytes,
            "omitted_line_count": omitted_lines,
            "mode": "text_head_tail",
        }

    head_text, tail_text, total_bytes = _collect_byte_windows(
        path,
        head_bytes=128 * 1024,
        tail_bytes=128 * 1024,
    )
    if total_bytes <= 0:
        return None
    omitted_bytes = max(0, total_bytes - len(head_text.encode("utf-8")) - len(tail_text.encode("utf-8")))
    if omitted_bytes <= 0:
        if destination_path is not None:
            ensure_dir(output_path.parent)
            shutil.copy2(path, output_path)
            return {
                "path": str(path.relative_to(root)),
                "compact_view_path": str(output_path.relative_to(root)),
                "archive_path": str(archive_path.relative_to(root)),
                "original_bytes": original_bytes,
                "mode": "text_copy",
            }
        return None
    marker = (
        f"[compacted completed runtime log: omitted {omitted_bytes} bytes; "
        f"full log archived at {archive_path.relative_to(root).as_posix()}]"
    )
    rewritten = [segment for segment in (head_text.rstrip("\n"), marker, tail_text.lstrip("\n")) if segment]
    output_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
    return {
        "path": str(path.relative_to(root)),
        "compact_view_path": str(output_path.relative_to(root)),
        "archive_path": str(archive_path.relative_to(root)),
        "original_bytes": original_bytes,
        "omitted_byte_count": omitted_bytes,
        "mode": "text_head_tail_bytes",
    }


def _maybe_update_session_meta(session_dir: Path, *, entries: list[dict[str, Any]]) -> None:
    meta_path = session_dir / "meta.json"
    meta = read_json(meta_path, {})
    if not isinstance(meta, dict) or not meta:
        return
    existing = meta.get("storage_maintenance") if isinstance(meta.get("storage_maintenance"), dict) else {}
    meta["storage_maintenance"] = {
        **existing,
        "last_compacted_at": utc_now(),
        "compacted_entries": entries,
    }
    write_json(meta_path, meta)


def _replace_file(path: Path, lines: list[bytes]) -> None:
    with NamedTemporaryFile("wb", delete=False, dir=path.parent, prefix=f"{path.name}.", suffix=".tmp") as handle:
        temp_path = Path(handle.name)
        for line in lines:
            handle.write(line)
    temp_path.replace(path)


def _backup_raw_line(backup_root: Path, *, file_rel: str, line_no: int, raw: bytes) -> Path:
    digest = hashlib.sha256(raw).hexdigest()[:16]
    safe_rel = file_rel.replace("/", "__")
    backup_name = f"{safe_rel}__line_{line_no:06d}__{digest}.jsonl.gz"
    backup_path = backup_root / backup_name
    ensure_dir(backup_path.parent)
    with gzip.open(backup_path, "wb") as handle:
        handle.write(raw)
    return backup_path


def _event_placeholder(raw: bytes, *, original_bytes: int, backup_ref: str, file_rel: str, line_no: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_id": _extract_bytes(_EVENT_ID_BYTES_RE, raw) or f"evt-slim-{line_no}",
        "type": _extract_bytes(_EVENT_TYPE_BYTES_RE, raw) or "runner.tool_result",
        "run_id": _extract_bytes(_RUN_ID_BYTES_RE, raw),
        "tool_name": _extract_bytes(_TOOL_NAME_BYTES_RE, raw),
        "status": "compacted",
        "summary": f"Oversized quest event payload ({original_bytes} bytes) was compacted into a quest-local backup.",
        "oversized_event": True,
        "original_bytes": original_bytes,
        "backup_ref": backup_ref,
        "created_at": utc_now(),
    }
    return {key: value for key, value in payload.items() if value is not None}


def _bash_log_placeholder(raw: bytes, *, original_bytes: int, backup_ref: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "seq": int(_extract_bytes(_SEQ_BYTES_RE, raw) or 0),
        "stream": _extract_bytes(_STREAM_BYTES_RE, raw) or "stdout",
        "timestamp": _extract_bytes(_TIMESTAMP_BYTES_RE, raw),
        "line": f"[compacted oversized bash log entry: {original_bytes} bytes -> {backup_ref}]",
        "oversized_payload": True,
        "original_bytes": original_bytes,
        "backup_ref": backup_ref,
    }
    return {key: value for key, value in payload.items() if value is not None}


def _stdout_placeholder(raw: bytes, *, original_bytes: int, backup_ref: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": _extract_bytes(_TIMESTAMP_BYTES_RE, raw),
        "line": f"[compacted oversized stdout entry: {original_bytes} bytes -> {backup_ref}]",
        "oversized_payload": True,
        "original_bytes": original_bytes,
        "backup_ref": backup_ref,
    }
    return {key: value for key, value in payload.items() if value is not None}


def _codex_history_placeholder(raw: bytes, *, original_bytes: int, backup_ref: str) -> dict[str, Any]:
    return {
        "timestamp": _extract_bytes(_TIMESTAMP_BYTES_RE, raw),
        "event": {
            "type": "oversized_payload",
            "summary": f"Oversized codex history entry ({original_bytes} bytes) was compacted into a quest-local backup.",
            "backup_ref": backup_ref,
            "original_bytes": original_bytes,
        },
    }


def _placeholder_for(path: Path, raw: bytes, *, original_bytes: int, backup_ref: str, file_rel: str, line_no: int) -> dict[str, Any]:
    normalized = file_rel.replace("\\", "/")
    if normalized == ".ds/events.jsonl":
        return _event_placeholder(raw, original_bytes=original_bytes, backup_ref=backup_ref, file_rel=file_rel, line_no=line_no)
    if normalized.startswith(".ds/bash_exec/") and normalized.endswith("/log.jsonl"):
        return _bash_log_placeholder(raw, original_bytes=original_bytes, backup_ref=backup_ref)
    if normalized.startswith(".ds/runs/") and normalized.endswith("/stdout.jsonl"):
        return _stdout_placeholder(raw, original_bytes=original_bytes, backup_ref=backup_ref)
    if normalized.startswith(".ds/codex_history/") and normalized.endswith("/events.jsonl"):
        return _codex_history_placeholder(raw, original_bytes=original_bytes, backup_ref=backup_ref)
    return {
        "oversized_payload": True,
        "original_bytes": original_bytes,
        "backup_ref": backup_ref,
    }


def _iter_jsonl_slim_targets(ds_root: Path) -> list[Path]:
    files: list[Path] = []
    direct_events = ds_root / "events.jsonl"
    if direct_events.exists():
        files.append(direct_events)
    files.extend(sorted((ds_root / "bash_exec").glob("**/log.jsonl")))
    files.extend(sorted((ds_root / "codex_history").glob("**/events.jsonl")))
    files.extend(sorted((ds_root / "runs").glob("**/stdout.jsonl")))
    return [path for path in files if path.is_file()]


def _path_is_cold(path: Path, *, root: Path, now: datetime, older_than_seconds: int) -> bool:
    relative = path.relative_to(root).as_posix()
    timestamp: datetime | None = None
    if relative.startswith(".ds/bash_exec/") and relative.endswith("/log.jsonl"):
        meta = read_json(path.parent / "meta.json", {})
        timestamp = _parse_timestamp((meta or {}).get("finished_at") or (meta or {}).get("updated_at"))
    elif relative.startswith(".ds/codex_history/") and relative.endswith("/events.jsonl"):
        meta = read_json(path.parent / "meta.json", {})
        timestamp = _parse_timestamp(
            (meta or {}).get("completed_at") or (meta or {}).get("finished_at") or (meta or {}).get("updated_at")
        )
    elif relative.startswith(".ds/runs/") and relative.endswith("/stdout.jsonl"):
        run_id = path.parent.name
        meta = read_json(root / ".ds" / "codex_history" / run_id / "meta.json", {})
        timestamp = _parse_timestamp(
            (meta or {}).get("completed_at") or (meta or {}).get("finished_at") or (meta or {}).get("updated_at")
        )
    elif relative.startswith(".ds/codex_homes/") and "/sessions/" in relative and relative.endswith(".jsonl"):
        parts = Path(relative).parts
        run_id = parts[2] if len(parts) > 2 else ""
        meta = read_json(root / ".ds" / "codex_history" / run_id / "meta.json", {})
        timestamp = _parse_timestamp(
            (meta or {}).get("completed_at") or (meta or {}).get("finished_at") or (meta or {}).get("updated_at")
        )
    if timestamp is not None:
        return (now - timestamp).total_seconds() >= older_than_seconds
    age = _age_seconds(path, now=now)
    return age is not None and age >= older_than_seconds


def _iter_cold_runtime_jsonl_targets(root: Path) -> list[Path]:
    resolved_root = Path(root).expanduser().resolve()
    ds_root = resolved_root / ".ds"
    files: list[Path] = []
    files.extend(sorted((ds_root / "runs").glob("*/stdout.jsonl")))
    codex_homes_root = ds_root / "codex_homes"
    if codex_homes_root.exists():
        for run_home in sorted(path for path in codex_homes_root.iterdir() if path.is_dir()):
            sessions_root = run_home / "sessions"
            if not sessions_root.exists():
                continue
            files.extend(sorted(sessions_root.glob("**/*.jsonl")))
    return [path for path in files if path.is_file()]


def slim_quest_jsonl(
    quest_root: Path,
    *,
    older_than_seconds: int = 6 * 3600,
    threshold_bytes: int,
) -> dict[str, Any]:
    resolved_root = Path(quest_root).expanduser().resolve()
    ds_root = resolved_root / ".ds"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_root = ds_root / "slim_backups" / timestamp
    manifest: dict[str, Any] = {
        "quest_root": str(resolved_root),
        "threshold_bytes": threshold_bytes,
        "backup_root": str(backup_root),
        "processed_at": utc_now(),
        "files": [],
        "compacted_line_count": 0,
        "compacted_bytes_total": 0,
    }
    if threshold_bytes <= 0 or not ds_root.exists():
        return manifest

    now = datetime.now(UTC)
    for path in _iter_jsonl_slim_targets(ds_root):
        if not _path_is_cold(path, root=resolved_root, now=now, older_than_seconds=older_than_seconds):
            continue
        rel = path.relative_to(resolved_root).as_posix()
        line_no = 0
        compacted_lines = 0
        compacted_bytes = 0
        rewritten: list[bytes] = []
        with path.open("rb") as handle:
            for raw in handle:
                line_no += 1
                line_bytes = len(raw)
                if line_bytes <= threshold_bytes:
                    rewritten.append(raw)
                    continue
                backup_path = _backup_raw_line(backup_root, file_rel=rel, line_no=line_no, raw=raw)
                backup_ref = backup_path.relative_to(resolved_root).as_posix()
                placeholder = _placeholder_for(
                    path,
                    raw,
                    original_bytes=line_bytes,
                    backup_ref=backup_ref,
                    file_rel=rel,
                    line_no=line_no,
                )
                rewritten.append((json.dumps(placeholder, ensure_ascii=False) + "\n").encode("utf-8"))
                compacted_lines += 1
                compacted_bytes += line_bytes
        if compacted_lines:
            _replace_file(path, rewritten)
            manifest["files"].append(
                {
                    "path": rel,
                    "compacted_lines": compacted_lines,
                    "compacted_bytes": compacted_bytes,
                }
            )
            manifest["compacted_line_count"] += compacted_lines
            manifest["compacted_bytes_total"] += compacted_bytes

    if manifest["compacted_line_count"]:
        ensure_dir(backup_root)
        manifest_path = backup_root / "manifest.json"
        manifest["manifest_path"] = str(manifest_path)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _iter_dedupe_targets(worktrees_root: Path, *, older_than_seconds: int, min_bytes: int) -> list[Path]:
    now = datetime.now(UTC)
    patterns = [
        "**/.codex/sessions/**/*.jsonl",
        "**/experiments/**/*.json",
        "**/.ds/runs/*/stdout.jsonl",
        "**/.ds/runs/*/stdout.full.jsonl.gz",
        "**/.ds/codex_history/*/events.jsonl",
        "**/.ds/bash_exec/**/*.full.jsonl.gz",
        "**/.ds/bash_exec/**/*.full.log.gz",
        "**/.ds/codex_homes/*/sessions/**/*.jsonl",
        "**/.ds/codex_homes/*/sessions/**/*.jsonl.gz",
    ]
    files: list[Path] = []
    for pattern in patterns:
        for path in worktrees_root.glob(pattern):
            if not path.is_file():
                continue
            try:
                if path.stat().st_size < min_bytes:
                    continue
            except OSError:
                continue
            age = _age_seconds(path, now=now)
            if age is None or age < older_than_seconds:
                continue
            files.append(path)
    return sorted(files)


def _sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _replace_with_hardlink(target: Path, source: Path) -> None:
    with NamedTemporaryFile("wb", delete=False, dir=target.parent, prefix=f"{target.name}.", suffix=".linktmp") as handle:
        temp_path = Path(handle.name)
    try:
        temp_path.unlink(missing_ok=True)
        os.link(source, temp_path)
        temp_path.replace(target)
    finally:
        temp_path.unlink(missing_ok=True)


def dedupe_worktree_files(
    quest_root: Path,
    *,
    older_than_seconds: int = 6 * 3600,
    min_bytes: int,
) -> dict[str, Any]:
    resolved_root = Path(quest_root).expanduser().resolve()
    worktrees_root = resolved_root / ".ds" / "worktrees"
    manifest: dict[str, Any] = {
        "quest_root": str(resolved_root),
        "worktrees_root": str(worktrees_root),
        "min_bytes": min_bytes,
        "older_than_seconds": older_than_seconds,
        "groups_examined": 0,
        "files_relinked": 0,
        "bytes_deduped": 0,
        "groups": [],
    }
    if min_bytes <= 0 or not worktrees_root.exists():
        return manifest

    size_buckets: dict[int, list[Path]] = {}
    for path in _iter_dedupe_targets(worktrees_root, older_than_seconds=older_than_seconds, min_bytes=min_bytes):
        try:
            size_buckets.setdefault(path.stat().st_size, []).append(path)
        except OSError:
            continue

    for size, paths in sorted(size_buckets.items(), key=lambda item: -item[0]):
        if len(paths) < 2:
            continue
        manifest["groups_examined"] += 1
        hash_buckets: dict[str, list[Path]] = {}
        for path in paths:
            try:
                digest = _sha256(path)
            except OSError:
                continue
            hash_buckets.setdefault(digest, []).append(path)
        for digest, dupes in hash_buckets.items():
            if len(dupes) < 2:
                continue
            canonical = dupes[0]
            relinked: list[str] = []
            for duplicate in dupes[1:]:
                try:
                    if canonical.stat().st_ino == duplicate.stat().st_ino:
                        continue
                except OSError:
                    continue
                _replace_with_hardlink(duplicate, canonical)
                manifest["files_relinked"] += 1
                manifest["bytes_deduped"] += size
                relinked.append(str(duplicate.relative_to(resolved_root)))
            if relinked:
                manifest["groups"].append(
                    {
                        "sha256": digest,
                        "size_bytes": size,
                        "canonical": str(canonical.relative_to(resolved_root)),
                        "relinked": relinked,
                    }
                )
    return manifest


def _count_lines(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def rotate_quest_events_segments(
    quest_root: Path,
    *,
    max_bytes: int = 64 * 1024 * 1024,
) -> dict[str, Any]:
    resolved_root = Path(quest_root).expanduser().resolve()
    events_path = resolved_root / ".ds" / "events.jsonl"
    manifest_path = resolved_root / ".ds" / "events" / "manifest.json"
    segments_root = resolved_root / ".ds" / "events" / "segments"
    existing_manifest = read_json(manifest_path, {})
    existing_segments = [
        dict(item)
        for item in (existing_manifest.get("segments") or [])
        if isinstance(item, dict)
    ]
    manifest: dict[str, Any] = {
        "quest_root": str(resolved_root),
        "events_path": str(events_path),
        "manifest_path": str(manifest_path),
        "segment_root": str(segments_root),
        "max_bytes": max_bytes,
        "rotated_segment_count": 0,
        "segments": existing_segments,
        "current_bytes": 0,
    }
    if max_bytes <= 0:
        return manifest
    if not events_path.exists():
        ensure_dir(segments_root)
        write_json(
            manifest_path,
            {
                "schema_version": 1,
                "quest_root": str(resolved_root),
                "active_path": _relative_ref(events_path, root=resolved_root),
                "segment_count": len(existing_segments),
                "segments": existing_segments,
                "updated_at": utc_now(),
            },
        )
        return manifest
    try:
        current_bytes = events_path.stat().st_size
    except OSError:
        current_bytes = 0
    manifest["current_bytes"] = current_bytes
    if current_bytes < max_bytes:
        write_json(
            manifest_path,
            {
                "schema_version": 1,
                "quest_root": str(resolved_root),
                "active_path": _relative_ref(events_path, root=resolved_root),
                "segment_count": len(existing_segments),
                "segments": existing_segments,
                "current_bytes": current_bytes,
                "updated_at": utc_now(),
            },
        )
        return manifest

    ensure_dir(segments_root)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    staging_path = events_path.with_name(f"events.rotate-{timestamp}.jsonl")
    events_path.replace(staging_path)
    events_path.write_text("", encoding="utf-8")
    segment_rel = Path(".ds") / "events" / "segments" / f"events-{timestamp}.jsonl.gz"
    segment_path = _unique_path(resolved_root / segment_rel)
    _write_gzip_copy(staging_path, segment_path)
    original_bytes = staging_path.stat().st_size if staging_path.exists() else current_bytes
    line_count = _count_lines(staging_path) if staging_path.exists() else 0
    staging_path.unlink(missing_ok=True)
    segment_entry = {
        "segment_id": f"events-segment-{timestamp}",
        "path": _relative_ref(segment_path, root=resolved_root),
        "original_bytes": original_bytes,
        "line_count": line_count,
        "created_at": utc_now(),
    }
    existing_segments.append(segment_entry)
    write_json(
        manifest_path,
        {
            "schema_version": 1,
            "quest_root": str(resolved_root),
            "active_path": _relative_ref(events_path, root=resolved_root),
            "segment_count": len(existing_segments),
            "segments": existing_segments,
            "current_bytes": 0,
            "updated_at": utc_now(),
        },
    )
    manifest["rotated_segment_count"] = 1
    manifest["segments"] = existing_segments
    return manifest


def _report_retention_bucket(path: Path, *, root: Path, now: datetime) -> tuple[str, str]:
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    age_hours = max(0.0, (now - modified).total_seconds()) / 3600.0
    relative_parent = _relative_ref(path.parent, root=root)
    if age_hours <= _REPORT_RETENTION_RECENT_HOURLY_WINDOW_HOURS:
        return (
            "hourly",
            f"{relative_parent}:{modified.strftime('%Y-%m-%dT%H')}",
        )
    return (
        "daily",
        f"{relative_parent}:{modified.strftime('%Y-%m-%d')}",
    )


def apply_report_history_retention(quest_root: Path) -> dict[str, Any]:
    resolved_root = Path(quest_root).expanduser().resolve()
    reports_root = resolved_root / "artifacts" / "reports"
    manifest_path = reports_root / "retention_manifest.json"
    manifest: dict[str, Any] = {
        "quest_root": str(resolved_root),
        "reports_root": str(reports_root),
        "retention_contract": {
            "keep_roles": ["latest", "state"],
            "recent_hourly_window_hours": _REPORT_RETENTION_RECENT_HOURLY_WINDOW_HOURS,
            "older_sampling": _REPORT_RETENTION_OLDER_SAMPLING,
        },
        "archived_file_count": 0,
        "kept_file_count": 0,
        "archived_samples": [],
        "kept_samples": [],
    }
    if not reports_root.exists():
        return manifest

    now = datetime.now(UTC)
    bucket_winners: dict[tuple[str, str], Path] = {}
    candidates: list[Path] = []
    kept_files: list[str] = []
    archived_files: list[dict[str, str]] = []
    for path in sorted(item for item in reports_root.rglob("*") if item.is_file()):
        if path.name in _REPORT_RETENTION_KEEP_FILENAMES or path.name.startswith("retention_manifest.ledger"):
            kept_files.append(_relative_ref(path, root=resolved_root))
            continue
        bucket = _report_retention_bucket(path, root=resolved_root, now=now)
        current = bucket_winners.get(bucket)
        if current is None or path.stat().st_mtime > current.stat().st_mtime:
            bucket_winners[bucket] = path
        candidates.append(path)

    kept_paths = set(bucket_winners.values())
    for path in candidates:
        if path in kept_paths:
            kept_files.append(_relative_ref(path, root=resolved_root))
            continue
        archive_target = _cold_archive_path(
            resolved_root,
            kind="report_history",
            relative_path=_relative_ref(path, root=resolved_root),
            compress=False,
        )
        shutil.move(str(path), archive_target)
        archived_files.append(
            {
                "source_path": _relative_ref(path, root=resolved_root),
                "archive_path": _relative_ref(archive_target, root=resolved_root),
            }
        )
    manifest["archived_file_count"] = len(archived_files)
    manifest["kept_file_count"] = len(kept_files)
    manifest["archived_samples"] = archived_files[:_MANIFEST_SAMPLE_LIMIT]
    manifest["kept_samples"] = kept_files[:_MANIFEST_SAMPLE_LIMIT]
    if archived_files or kept_files:
        ledger_path = _manifest_ledger_path(manifest_path)
        _write_gzip_json(
            ledger_path,
            {
                "schema_version": 1,
                "quest_root": str(resolved_root),
                "reports_root": str(reports_root),
                "archived_files": archived_files,
                "kept_files": kept_files,
            },
        )
        manifest["ledger_ref"] = _relative_ref(ledger_path, root=resolved_root)
    write_json(manifest_path, manifest)
    return manifest


def _run_meta(root: Path, run_id: str) -> dict[str, Any]:
    payload = read_json(root / ".ds" / "codex_history" / run_id / "meta.json", {})
    return payload if isinstance(payload, dict) else {}


def _run_is_cold(root: Path, run_id: str, *, now: datetime, older_than_seconds: int) -> bool:
    meta = _run_meta(root, run_id)
    timestamp = _parse_timestamp(meta.get("completed_at") or meta.get("finished_at") or meta.get("updated_at"))
    if timestamp is not None:
        return (now - timestamp).total_seconds() >= older_than_seconds
    run_home = root / ".ds" / "codex_homes" / run_id
    return _path_tree_is_cold(run_home, now=now, older_than_seconds=older_than_seconds)


def _maybe_stage_bash_compact_view(
    source_path: Path,
    *,
    mode: str,
    archive_ref: str,
    root: Path,
    head_lines: int,
    tail_lines: int,
) -> Path | None:
    if not source_path.exists():
        return None
    original_bytes = source_path.stat().st_size
    if original_bytes == 0:
        return None
    compact_path = _compact_view_path(source_path)
    archive_stub = root / archive_ref
    if mode == "jsonl":
        _compact_jsonl_file(
            source_path,
            archive_path=archive_stub,
            original_bytes=original_bytes,
            head_lines=head_lines,
            tail_lines=tail_lines,
            root=root,
            destination_path=compact_path,
        )
    else:
        _compact_text_file(
            source_path,
            archive_path=archive_stub,
            original_bytes=original_bytes,
            head_lines=head_lines,
            tail_lines=tail_lines,
            root=root,
            destination_path=compact_path,
        )
    return compact_path if compact_path.exists() else None


def _archive_bash_session_logs(
    root: Path,
    *,
    older_than_seconds: int,
    now: datetime,
    head_lines: int,
    tail_lines: int,
) -> list[dict[str, Any]]:
    moved_entries: list[dict[str, Any]] = []
    bash_root = root / ".ds" / "bash_exec"
    if not bash_root.exists():
        return moved_entries
    for session_dir in sorted(path for path in bash_root.iterdir() if path.is_dir()):
        meta = read_json(session_dir / "meta.json", {})
        if not _session_is_cold_terminal(meta or {}, now=now, older_than_seconds=older_than_seconds):
            continue
        for filename, mode in _BASH_SESSION_LOG_SPECS:
            source_path = session_dir / filename
            if not source_path.exists():
                continue
            index_path = source_path.with_name(f"{source_path.name}.index.json")
            compact_path = _compact_view_path(source_path)
            if index_path.exists() and (compact_path.exists() or source_path.stat().st_size == 0):
                continue
            relative_source = _relative_ref(source_path, root=root)
            source_bytes = source_path.stat().st_size
            cold_archive_ref: str | None = None
            compact_ref: str | None = None
            if source_bytes > 0:
                legacy_archive_path = _archive_path(source_path)
                target = _cold_archive_path(
                    root,
                    kind="bash_exec",
                    relative_path=relative_source,
                    compress=True,
                )
                if legacy_archive_path.exists():
                    shutil.move(str(legacy_archive_path), target)
                    legacy_index = legacy_archive_path.with_name(f"{legacy_archive_path.name}.index.json")
                    legacy_index.unlink(missing_ok=True)
                else:
                    _write_gzip_copy(source_path, target)
                cold_archive_ref = _relative_ref(target, root=root)
                compact_view = _maybe_stage_bash_compact_view(
                    source_path,
                    mode=mode,
                    archive_ref=cold_archive_ref,
                    root=root,
                    head_lines=head_lines,
                    tail_lines=tail_lines,
                )
                if compact_view is not None:
                    compact_ref = _relative_ref(compact_view, root=root)
            source_path.unlink(missing_ok=True)
            _write_json_index(
                index_path,
                {
                    "schema_version": 1,
                    "kind": "bash_exec_session_log",
                    "source_path": relative_source,
                    "compact_view_ref": compact_ref,
                    "cold_archive_ref": cold_archive_ref,
                    "archived_at": utc_now(),
                    "original_bytes": source_bytes,
                    "mode": mode,
                },
            )
            moved_entries.append(
                {
                    "kind": "bash_exec_session_log",
                    "source_path": relative_source,
                    "compact_view_ref": compact_ref,
                    "cold_archive_ref": cold_archive_ref,
                }
            )
    return moved_entries


def _archive_codex_home_payloads(
    root: Path,
    *,
    older_than_seconds: int,
    now: datetime,
) -> list[dict[str, Any]]:
    moved_entries: list[dict[str, Any]] = []
    codex_homes_root = root / ".ds" / "codex_homes"
    if not codex_homes_root.exists():
        return moved_entries
    for run_home in sorted(path for path in codex_homes_root.iterdir() if path.is_dir()):
        run_id = run_home.name
        if not _run_is_cold(root, run_id, now=now, older_than_seconds=older_than_seconds):
            continue
        archived_items: list[dict[str, str]] = []
        retained_items: list[str] = []
        for child in sorted(run_home.iterdir()):
            if child.name in _CODEX_HOME_RETENTION_KEEP_NAMES:
                retained_items.append(child.name)
                continue
            if child.name.startswith("runtime_retention.") or child.name in {".tmp", "tmp"}:
                continue
            relative_child = _relative_ref(child, root=root)
            if child.is_dir():
                target = _cold_archive_path(
                    root,
                    kind="codex_home_runs",
                    relative_path=f"{relative_child}.tar.gz",
                    compress=False,
                )
                _archive_directory_as_tar_gz(child, target)
                shutil.rmtree(child, ignore_errors=True)
            else:
                target = _cold_archive_path(
                    root,
                    kind="codex_home_runs",
                    relative_path=relative_child,
                    compress=True,
                )
                _write_gzip_copy(child, target)
                child.unlink(missing_ok=True)
            archived_entry = {
                "kind": "codex_home_payload",
                "run_id": run_id,
                "source_path": relative_child,
                "cold_archive_ref": _relative_ref(target, root=root),
            }
            archived_items.append(archived_entry)
            moved_entries.append(archived_entry)
        if archived_items:
            write_json(
                run_home / "runtime_retention.index.json",
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "run_home": _relative_ref(run_home, root=root),
                    "retained_items": sorted(set(retained_items + ["runtime_retention.index.json"])),
                    "archived_items": archived_items,
                    "archived_at": utc_now(),
                },
            )
    return moved_entries


def archive_cold_runtime_payloads(
    quest_root: Path,
    *,
    older_than_seconds: int = 6 * 3600,
    head_lines: int = 200,
    tail_lines: int = 200,
) -> dict[str, Any]:
    resolved_root = Path(quest_root).expanduser().resolve()
    manifest_path = resolved_root / ".ds" / "cold_archive" / "manifest.json"
    moved_files: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "quest_root": str(resolved_root),
        "moved_file_count": 0,
        "moved_by_kind": {},
        "moved_samples": [],
    }
    now = datetime.now(UTC)
    moved_files.extend(
        _archive_bash_session_logs(
            resolved_root,
            older_than_seconds=older_than_seconds,
            now=now,
            head_lines=head_lines,
            tail_lines=tail_lines,
        )
    )

    for session_path in _iter_cold_runtime_jsonl_targets(resolved_root):
        relative = _relative_ref(session_path, root=resolved_root)
        if not relative.startswith(".ds/codex_homes/") or "/sessions/" not in relative:
            continue
        if not _path_is_cold(session_path, root=resolved_root, now=now, older_than_seconds=older_than_seconds):
            continue
        compact_path = session_path.with_name(f"{session_path.stem}.compact.ndjson")
        if compact_path.exists():
            continue
        full_archive_path = _archive_path(session_path)
        if full_archive_path.exists():
            target = _cold_archive_path(
                resolved_root,
                kind="codex_sessions",
                relative_path=relative,
                compress=True,
            )
            shutil.move(str(full_archive_path), target)
        else:
            target = _cold_archive_path(
                resolved_root,
                kind="codex_sessions",
                relative_path=relative,
                compress=True,
            )
            _write_gzip_copy(session_path, target)
        session_path.replace(compact_path)
        index_path = session_path.with_name(f"{session_path.name}.index.json")
        _write_json_index(
            index_path,
            {
                "schema_version": 1,
                "kind": "codex_session_jsonl",
                "source_path": relative,
                "compact_view_ref": _relative_ref(compact_path, root=resolved_root),
                "cold_archive_ref": _relative_ref(target, root=resolved_root),
                "archived_at": utc_now(),
                "compact_view_bytes": compact_path.stat().st_size,
            },
        )
        moved_files.append(
            {
                "kind": "codex_session_jsonl",
                "source_path": relative,
                "compact_view_ref": _relative_ref(compact_path, root=resolved_root),
                "cold_archive_ref": _relative_ref(target, root=resolved_root),
            }
        )

    moved_files.extend(
        _archive_codex_home_payloads(
            resolved_root,
            older_than_seconds=older_than_seconds,
            now=now,
        )
    )
    manifest["moved_file_count"] = len(moved_files)
    if moved_files:
        moved_by_kind: dict[str, int] = {}
        for item in moved_files:
            kind = str(item.get("kind") or "unknown")
            moved_by_kind[kind] = moved_by_kind.get(kind, 0) + 1
        manifest["moved_by_kind"] = moved_by_kind
        manifest["moved_samples"] = moved_files[:_MANIFEST_SAMPLE_LIMIT]
        ledger_path = _manifest_ledger_path(manifest_path)
        _write_gzip_json(
            ledger_path,
            {
                "schema_version": 1,
                "quest_root": str(resolved_root),
                "moved_files": moved_files,
            },
        )
        manifest["ledger_ref"] = _relative_ref(ledger_path, root=resolved_root)
        _write_json_index(manifest_path, manifest)
    return manifest


def compact_completed_runtime_logs(
    root: Path,
    *,
    older_than_seconds: int = 6 * 3600,
    jsonl_max_bytes: int = 64 * 1024 * 1024,
    text_max_bytes: int = 16 * 1024 * 1024,
    head_lines: int = 200,
    tail_lines: int = 200,
) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve()
    now = datetime.now(UTC)
    manifest: dict[str, Any] = {
        "root": str(resolved_root),
        "compacted_files": [],
        "session_count": 0,
    }
    bash_root = resolved_root / ".ds" / "bash_exec"
    if bash_root.exists():
        for session_dir in sorted(path for path in bash_root.iterdir() if path.is_dir()):
            meta = read_json(session_dir / "meta.json", {})
            if not _session_is_cold_terminal(meta or {}, now=now, older_than_seconds=older_than_seconds):
                continue
            session_entries: list[dict[str, Any]] = []
            for filename, max_bytes, mode in (
                ("log.jsonl", jsonl_max_bytes, "jsonl"),
                ("terminal.log", text_max_bytes, "text"),
                ("monitor.log", text_max_bytes, "text"),
            ):
                path = session_dir / filename
                if not path.exists():
                    continue
                try:
                    original_bytes = path.stat().st_size
                except OSError:
                    continue
                if original_bytes < max_bytes:
                    continue
                archive_path = _archive_path(path)
                if not archive_path.exists():
                    _write_gzip_copy(path, archive_path)
                if mode == "jsonl":
                    compacted = _compact_jsonl_file(
                        path,
                        archive_path=archive_path,
                        original_bytes=original_bytes,
                        head_lines=head_lines,
                        tail_lines=tail_lines,
                        root=resolved_root,
                    )
                else:
                    compacted = _compact_text_file(
                        path,
                        archive_path=archive_path,
                        original_bytes=original_bytes,
                        head_lines=head_lines,
                        tail_lines=tail_lines,
                        root=resolved_root,
                    )
                if compacted is not None:
                    session_entries.append(compacted)
                    manifest["compacted_files"].append(compacted)
            if session_entries:
                manifest["session_count"] += 1
                _maybe_update_session_meta(session_dir, entries=session_entries)
    for path in _iter_cold_runtime_jsonl_targets(resolved_root):
        if not _path_is_cold(path, root=resolved_root, now=now, older_than_seconds=older_than_seconds):
            continue
        try:
            original_bytes = path.stat().st_size
        except OSError:
            continue
        if original_bytes < jsonl_max_bytes:
            continue
        archive_path = _archive_path(path)
        if not archive_path.exists():
            _write_gzip_copy(path, archive_path)
        compacted = _compact_jsonl_file(
            path,
            archive_path=archive_path,
            original_bytes=original_bytes,
            head_lines=head_lines,
            tail_lines=tail_lines,
            root=resolved_root,
        )
        if compacted is not None:
            manifest["session_count"] += 1
            manifest["compacted_files"].append(compacted)
    return manifest


def prune_stale_atomic_tempfiles(root: Path, *, older_than_seconds: int = 3600) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve()
    now = datetime.now(UTC)
    removed: list[str] = []
    for candidate in resolved_root.rglob("*.tmp"):
        if not candidate.is_file():
            continue
        age = _age_seconds(candidate, now=now)
        if age is None or age < older_than_seconds:
            continue
        match = _ATOMIC_TMP_RE.match(candidate.name)
        if match is None:
            continue
        target = candidate.with_name(match.group("base"))
        if not target.exists():
            continue
        candidate.unlink(missing_ok=True)
        removed.append(str(candidate.relative_to(resolved_root)))
    return {
        "root": str(resolved_root),
        "removed_tempfiles": removed,
        "removed_count": len(removed),
    }


def prune_codex_home_tempdirs(root: Path, *, older_than_seconds: int = 6 * 3600) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve()
    now = datetime.now(UTC)
    removed: list[str] = []
    codex_homes_root = resolved_root / ".ds" / "codex_homes"
    if not codex_homes_root.exists():
        return {"root": str(resolved_root), "removed_tempdirs": removed, "removed_count": 0}
    for run_home in sorted(path for path in codex_homes_root.iterdir() if path.is_dir()):
        for temp_root in (run_home / ".tmp", run_home / "tmp"):
            if not temp_root.exists():
                continue
            if not _path_tree_is_cold(temp_root, now=now, older_than_seconds=older_than_seconds):
                continue
            shutil.rmtree(temp_root, ignore_errors=True)
            removed.append(str(temp_root.relative_to(resolved_root)))
    return {
        "root": str(resolved_root),
        "removed_tempdirs": removed,
        "removed_count": len(removed),
    }


def ensure_runtime_gitignore(root: Path) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve()
    gitignore_path = resolved_root / ".gitignore"
    existing_text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    lines = [line.rstrip("\n") for line in existing_text.splitlines()]
    line_set = {line for line in lines}
    added_entries = [entry for entry in RUNTIME_GITIGNORE_ENTRIES if entry not in line_set]
    if added_entries:
        updated = existing_text.rstrip("\n")
        if updated:
            updated += "\n"
        updated += "\n".join(added_entries) + "\n"
        gitignore_path.write_text(updated, encoding="utf-8")
    return {
        "root": str(resolved_root),
        "path": str(gitignore_path),
        "updated": bool(added_entries),
        "added_entries": added_entries,
    }


def maintain_quest_runtime_storage(
    quest_root: Path,
    *,
    include_worktrees: bool = True,
    older_than_seconds: int = 6 * 3600,
    jsonl_max_mb: int = 64,
    text_max_mb: int = 16,
    event_segment_max_mb: int = 64,
    slim_jsonl_threshold_mb: int | None = 8,
    dedupe_worktree_min_mb: int | None = 16,
    head_lines: int = 200,
    tail_lines: int = 200,
) -> dict[str, Any]:
    resolved_quest_root = Path(quest_root).expanduser().resolve()
    roots = iter_managed_roots(resolved_quest_root) if include_worktrees else [resolved_quest_root]
    manifest: dict[str, Any] = {
        "quest_root": str(resolved_quest_root),
        "include_worktrees": include_worktrees,
        "roots": [],
        "processed_at": utc_now(),
        "worktree_runtime_prune": {
            "quest_root": str(resolved_quest_root),
            "skipped": True,
            "reason": "include_worktrees_disabled",
        },
        "worktree_dedupe": {
            "quest_root": str(resolved_quest_root),
            "skipped": True,
            "reason": "include_worktrees_disabled" if not include_worktrees else "dedupe_disabled",
        },
    }
    if include_worktrees:
        manifest["worktree_runtime_prune"] = prune_cold_worktree_runtime_payloads(
            resolved_quest_root,
            older_than_seconds=older_than_seconds,
        )
    for root in roots:
        gitignore_manifest = ensure_runtime_gitignore(root)
        temp_manifest = prune_stale_atomic_tempfiles(root, older_than_seconds=max(3600, older_than_seconds // 2))
        event_manifest = rotate_quest_events_segments(
            root,
            max_bytes=max(1, event_segment_max_mb) * 1024 * 1024,
        )
        log_manifest = compact_completed_runtime_logs(
            root,
            older_than_seconds=older_than_seconds,
            jsonl_max_bytes=max(1, jsonl_max_mb) * 1024 * 1024,
            text_max_bytes=max(1, text_max_mb) * 1024 * 1024,
            head_lines=head_lines,
            tail_lines=tail_lines,
        )
        oversized_jsonl_manifest = slim_quest_jsonl(
            root,
            older_than_seconds=older_than_seconds,
            threshold_bytes=0 if slim_jsonl_threshold_mb is None else max(1, slim_jsonl_threshold_mb) * 1024 * 1024,
        )
        report_history_retention_manifest = apply_report_history_retention(root)
        codex_home_manifest = prune_codex_home_tempdirs(root, older_than_seconds=older_than_seconds)
        cold_archive_manifest = archive_cold_runtime_payloads(
            root,
            older_than_seconds=older_than_seconds,
            head_lines=head_lines,
            tail_lines=tail_lines,
        )
        manifest["roots"].append(
            {
                "root": str(root),
                "gitignore": gitignore_manifest,
                "tempfiles": temp_manifest,
                "events": event_manifest,
                "runtime_logs": log_manifest,
                "oversized_jsonl": oversized_jsonl_manifest,
                "report_history_retention": report_history_retention_manifest,
                "codex_homes": codex_home_manifest,
                "cold_archive": cold_archive_manifest,
            }
        )
    if include_worktrees and dedupe_worktree_min_mb is not None:
        manifest["worktree_dedupe"] = dedupe_worktree_files(
            resolved_quest_root,
            older_than_seconds=older_than_seconds,
            min_bytes=max(1, dedupe_worktree_min_mb) * 1024 * 1024,
        )
    return manifest
