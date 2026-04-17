from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
import gzip
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .quest.layout import RUNTIME_GITIGNORE_ENTRIES
from .shared import ensure_dir, read_json, utc_now, write_json

TERMINAL_STATUSES = {"completed", "failed", "terminated"}
_ATOMIC_TMP_RE = re.compile(r"^(?P<base>.+)\.[A-Za-z0-9_-]{8,}\.tmp$")
_SEQ_RE = re.compile(r'"seq"\s*:\s*(\d+)')


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


def _archive_path(path: Path) -> Path:
    suffixes = "".join(path.suffixes)
    base = path.name[: -len(suffixes)] if suffixes else path.name
    return path.with_name(f"{base}.full{suffixes}.gz")


def _write_gzip_copy(source: Path, archive_path: Path) -> None:
    ensure_dir(archive_path.parent)
    with source.open("rb") as input_handle, gzip.open(archive_path, "wb", compresslevel=1) as output_handle:
        shutil.copyfileobj(input_handle, output_handle)


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
) -> dict[str, Any] | None:
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
        path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
        return {
            "path": str(path.relative_to(root)),
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
    path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
    return {
        "path": str(path.relative_to(root)),
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
) -> dict[str, Any] | None:
    head, tail, total_lines = _collect_line_windows(path, head_lines=head_lines, tail_lines=tail_lines)
    if total_lines > head_lines + tail_lines:
        omitted_lines = max(0, total_lines - len(head) - len(tail))
        marker = (
            f"[compacted completed runtime log: omitted {omitted_lines} lines; "
            f"full log archived at {archive_path.relative_to(root).as_posix()}]"
        )
        rewritten = [*head, marker, *tail]
        path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
        return {
            "path": str(path.relative_to(root)),
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
        return None
    marker = (
        f"[compacted completed runtime log: omitted {omitted_bytes} bytes; "
        f"full log archived at {archive_path.relative_to(root).as_posix()}]"
    )
    rewritten = [segment for segment in (head_text.rstrip("\n"), marker, tail_text.lstrip("\n")) if segment]
    path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
    return {
        "path": str(path.relative_to(root)),
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
    if not bash_root.exists():
        return manifest

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
        temp_root = run_home / ".tmp"
        if not temp_root.exists():
            continue
        age = _age_seconds(temp_root, now=now)
        if age is None or age < older_than_seconds:
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
    }
    for root in roots:
        gitignore_manifest = ensure_runtime_gitignore(root)
        temp_manifest = prune_stale_atomic_tempfiles(root, older_than_seconds=max(3600, older_than_seconds // 2))
        log_manifest = compact_completed_runtime_logs(
            root,
            older_than_seconds=older_than_seconds,
            jsonl_max_bytes=max(1, jsonl_max_mb) * 1024 * 1024,
            text_max_bytes=max(1, text_max_mb) * 1024 * 1024,
            head_lines=head_lines,
            tail_lines=tail_lines,
        )
        codex_home_manifest = prune_codex_home_tempdirs(root, older_than_seconds=older_than_seconds)
        manifest["roots"].append(
            {
                "root": str(root),
                "gitignore": gitignore_manifest,
                "tempfiles": temp_manifest,
                "runtime_logs": log_manifest,
                "codex_homes": codex_home_manifest,
            }
        )
    return manifest
